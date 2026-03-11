import httpx
import asyncio
import base64
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from app.config import get_settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from app.models import (
    Audience, CampaignSettings, AdCopy, MetaIds,
    CampaignObjective, CTAType
)
from app.utils.sanitizer import sanitize_for_meta
from app.utils.utm_builder import build_utm_url
from app.utils.interest_resolver import InterestResolver


class MetaAPIError(Exception):
    """Custom exception for Meta API errors."""

    def __init__(self, message: str, code: int = None, subcode: int = None, error_data: dict = None):
        self.message = message
        self.code = code
        self.subcode = subcode
        self.error_data = error_data or {}
        super().__init__(self.message)


class MetaClient:
    """Client for Meta Marketing API v25.0."""

    BASE_URL = "https://graph.facebook.com/v25.0"

    # Error codes that should trigger retry with backoff
    RATE_LIMIT_CODES = {17, 613}
    RATE_LIMIT_SUBCODES = {2446079, 1487742}

    # Minimum lifetime budget in kobo (NGN 108,300 = 10,830,000 kobo)
    MIN_LIFETIME_BUDGET_KOBO = 10_830_000

    # Error subcode for deprecated interests
    DEPRECATED_INTEREST_SUBCODE = 1870247

    # Error subcode for unsupported city targeting
    CITY_TARGETING_NOT_SUPPORTED_SUBCODE = 1487479

    def __init__(self):
        settings = get_settings()
        self.access_token = settings.meta_system_token
        self.ad_account_id = settings.meta_ad_account_id
        self.page_id = settings.meta_page_id
        self.sandbox_mode = settings.sandbox_mode
        self.interest_resolver = InterestResolver()

    async def deploy_ad(
        self,
        job_id: str,
        ad_copy: AdCopy,
        audience: Audience,
        campaign_settings: CampaignSettings,
        image_url: Optional[str] = None,
        video_url: Optional[str] = None
    ) -> MetaIds:
        """
        Deploy a complete ad campaign to Meta.

        Execution order:
        1. Create Campaign (PAUSED)
        2. Create Ad Set with targeting
        3. Upload Creative asset
        4. Create Ad Creative
        5. Create Ad (PAUSED)

        Args:
            job_id: Unique job identifier
            ad_copy: Approved ad copy
            audience: Approved audience targeting
            campaign_settings: Approved campaign settings
            image_url: URL to image creative
            video_url: URL to video creative

        Returns:
            MetaIds with all created object IDs
        """
        logger.info(f"[DEPLOY] Starting deployment for job {job_id[:8]}")

        # Step 1: Create Campaign
        logger.info("[DEPLOY] Step 1: Creating Campaign...")
        campaign_id = await self._create_campaign(
            job_id, campaign_settings, ad_copy.headline
        )

        # Step 2: Resolve interest IDs
        logger.info("[DEPLOY] Step 2: Resolving interests...")
        interest_names = [i.name for i in audience.interests]
        resolved_interests = await self.interest_resolver.resolve_interests_parallel(
            interest_names
        )

        # Step 2b: Resolve city keys to numeric IDs
        logger.info("[DEPLOY] Step 2b: Resolving city keys...")
        if audience.core_audience.geo_locations.cities:
            country_code = audience.core_audience.geo_locations.countries[0] if audience.core_audience.geo_locations.countries else "NG"
            for city in audience.core_audience.geo_locations.cities:
                if not city.key.isdigit():
                    # City key is a name, need to resolve to numeric ID
                    resolved_key = await self.resolve_city_key(city.key, country_code)
                    if resolved_key:
                        logger.info(f"Resolved city '{city.key}' to key '{resolved_key}'")
                        city.key = resolved_key
                    else:
                        logger.warning(f"Could not resolve city '{city.key}', will skip")

        # Step 3: Create Ad Set
        logger.info("[DEPLOY] Step 3: Creating Ad Set...")
        adset_id = await self._create_adset(
            campaign_id, audience, campaign_settings, resolved_interests
        )

        # Step 4: Upload Creative
        logger.info("[DEPLOY] Step 4: Uploading Creative...")
        if video_url:
            asset_id = await self._upload_video(video_url)
            is_video = True
        elif image_url:
            asset_id = await self._upload_image(image_url)
            is_video = False
        else:
            raise MetaAPIError("No creative asset provided")

        # Step 5: Create Ad Creative
        logger.info("[DEPLOY] Step 5: Creating Ad Creative...")
        creative_id = await self._create_creative(
            ad_copy, campaign_settings, asset_id, is_video
        )

        # Step 6: Create Ad
        logger.info("[DEPLOY] Step 6: Creating Ad...")
        ad_id = await self._create_ad(adset_id, creative_id, ad_copy.headline)

        logger.info(f"[DEPLOY] Complete! Campaign={campaign_id}, Ad={ad_id}")

        return MetaIds(
            campaign_id=campaign_id,
            adset_id=adset_id,
            creative_id=creative_id,
            ad_id=ad_id
        )

    def _extract_campaign_name(
        self,
        headline: str,
        destination_url: str
    ) -> str:
        """Extract a meaningful campaign name from headline or URL."""
        from urllib.parse import urlparse

        # Try to use headline first (truncate to 30 chars)
        if headline and len(headline.strip()) > 3:
            name = headline.strip()[:30]
            return name

        # Fall back to domain name from URL
        if destination_url:
            try:
                parsed = urlparse(destination_url)
                domain = parsed.netloc.replace("www.", "")
                # Get just the main domain name without TLD
                domain_parts = domain.split(".")
                if len(domain_parts) >= 2:
                    name = domain_parts[0].title()
                    if len(name) > 2:
                        return name
            except Exception:
                pass

        # Last resort: generic name
        return "Campaign"

    async def _create_campaign(
        self,
        job_id: str,
        settings: CampaignSettings,
        headline: str = ""
    ) -> str:
        """Create a campaign (always PAUSED)."""
        url = f"{self.BASE_URL}/{self.ad_account_id}/campaigns"

        # Generate campaign name from headline or destination URL
        base_name = self._extract_campaign_name(headline, settings.destination_url)
        campaign_name = sanitize_for_meta(
            f"{base_name} - {datetime.now().strftime('%b %d')}"
        )

        data = {
            "name": campaign_name,
            "objective": settings.objective.value,
            "status": "PAUSED",
            "special_ad_categories": "[]",
            "is_adset_budget_sharing_enabled": "false",
            "access_token": self.access_token
        }

        response = await self._make_request("POST", url, data)
        return response["id"]

    async def _create_adset(
        self,
        campaign_id: str,
        audience: Audience,
        settings: CampaignSettings,
        resolved_interests: List[Dict[str, str]]
    ) -> str:
        """Create an ad set with targeting."""
        url = f"{self.BASE_URL}/{self.ad_account_id}/adsets"

        # Convert budget to minor currency units (kobo for NGN, pence for GBP, cents for USD)
        # Use lifetime_budget = daily_budget * duration_days * 100
        lifetime_budget = int(settings.daily_budget * settings.duration_days * 100)

        # Validate minimum budget for NGN
        if lifetime_budget < self.MIN_LIFETIME_BUDGET_KOBO:
            min_naira = self.MIN_LIFETIME_BUDGET_KOBO / 100
            current_naira = lifetime_budget / 100
            raise MetaAPIError(
                f"Lifetime budget too low. Minimum is ₦{min_naira:,.0f} but got ₦{current_naira:,.0f}. "
                f"Increase daily budget or duration."
            )

        # Build targeting spec (may be modified on retry if interests are deprecated or city targeting fails)
        current_interests = resolved_interests.copy()
        skip_city_targeting = False
        targeting = self._build_targeting_spec(audience, current_interests, skip_city_targeting)

        # Calculate start/end times
        start_time = datetime.utcnow() + timedelta(days=1)
        end_time = start_time + timedelta(days=settings.duration_days)

        adset_name = sanitize_for_meta(
            f"AdSet - {audience.targeting_confidence} confidence"
        )

        # Map objective to optimization goal
        optimization_goal = self._get_optimization_goal(settings.objective)

        data = {
            "name": adset_name,
            "campaign_id": campaign_id,
            "lifetime_budget": lifetime_budget,
            "billing_event": "IMPRESSIONS",
            "optimization_goal": optimization_goal,
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "targeting": targeting,
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S-0000"),
            "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%S-0000"),
            "status": "PAUSED",
            "access_token": self.access_token
        }

        # Try creating adset, handling deprecated interests and city targeting errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self._make_request("POST", url, data)
                return response["id"]
            except MetaAPIError as e:
                if e.subcode == self.DEPRECATED_INTEREST_SUBCODE:
                    # Parse deprecated interests from error and remove them
                    deprecated_ids = self._parse_deprecated_interests_from_error(e)
                    if deprecated_ids and attempt < max_retries - 1:
                        logger.warning(f"Removing deprecated interests: {deprecated_ids}")
                        current_interests = [
                            i for i in current_interests
                            if i.get("id") not in deprecated_ids
                        ]
                        targeting = self._build_targeting_spec(
                            audience, current_interests, skip_city_targeting=skip_city_targeting
                        )
                        data["targeting"] = targeting
                        continue
                elif e.subcode == self.CITY_TARGETING_NOT_SUPPORTED_SUBCODE:
                    # City targeting not supported, retry without cities
                    if not skip_city_targeting and attempt < max_retries - 1:
                        logger.warning("City targeting not supported, retrying without cities")
                        skip_city_targeting = True
                        targeting = self._build_targeting_spec(
                            audience, current_interests, skip_city_targeting=True
                        )
                        data["targeting"] = targeting
                        continue
                raise

        raise MetaAPIError("Failed to create ad set after retries")

    def _parse_deprecated_interests_from_error(self, error: MetaAPIError) -> List[str]:
        """Parse deprecated interest IDs from Meta API error."""
        import re
        # Check error_user_msg first (contains the detailed info)
        error_user_msg = error.error_data.get("error_user_msg", "")
        # Also check the main message
        full_text = f"{error.message} {error_user_msg}"

        # Look for deprecated_interest_id in the error
        # Pattern: "deprecated_interest_id":"6011208690029"
        pattern = r'"deprecated_interest_id"\s*:\s*"(\d+)"'
        matches = re.findall(pattern, full_text)
        return matches

    async def _check_country_supports_city(self, country_code: str) -> bool:
        """Check if a country supports city targeting via Meta API."""
        url = f"{self.BASE_URL}/search"
        params = {
            "type": "adgeolocation",
            "location_types": '["country"]',
            "q": country_code,
            "match_country_code": "true",
            "access_token": self.access_token
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("data", [])
                    for result in results:
                        if result.get("key") == country_code:
                            return result.get("supports_city", False)
        except Exception as e:
            logger.warning(f"Failed to check city support for {country_code}: {e}")

        # Default to False if we can't determine
        return False

    async def resolve_city_key(self, city_name: str, country_code: str) -> Optional[str]:
        """
        Resolve a city name to its Meta geolocation key (numeric ID).

        Args:
            city_name: Name of the city (e.g., "Lagos")
            country_code: ISO country code (e.g., "NG")

        Returns:
            Numeric key string (e.g., "2332459") or None if not found
        """
        url = f"{self.BASE_URL}/search"
        params = {
            "type": "adgeolocation",
            "q": city_name,
            "location_types": '["city"]',
            "country_code": country_code,
            "access_token": self.access_token
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("data", [])
                    if results:
                        # Return the first (most relevant) match
                        return results[0].get("key")
        except Exception as e:
            logger.warning(f"Failed to resolve city '{city_name}' in {country_code}: {e}")

        return None

    def _build_targeting_spec(
        self,
        audience: Audience,
        resolved_interests: List[Dict[str, str]],
        skip_city_targeting: bool = False
    ) -> Dict[str, Any]:
        """Build Meta targeting specification."""
        core = audience.core_audience

        # Build geo_locations - cities and countries are mutually exclusive
        # If we have resolved cities, use cities only (country is implied)
        # Otherwise fall back to country-level targeting
        geo_locations = {}

        if core.geo_locations.cities and not skip_city_targeting:
            valid_cities = [
                {
                    "key": city.key,
                    "radius": city.radius or 25,
                    "distance_unit": "kilometer"  # Always kilometer, never mile
                }
                for city in core.geo_locations.cities
                if city.key and city.key.isdigit()
            ]
            if valid_cities:
                # Cities only - country is implied by the city
                geo_locations["cities"] = valid_cities
            else:
                # No valid cities resolved - fall back to country
                geo_locations["countries"] = core.geo_locations.countries
        else:
            # No cities or city targeting skipped - use country only
            geo_locations["countries"] = core.geo_locations.countries

        targeting = {
            "geo_locations": geo_locations,
            "publisher_platforms": ["facebook", "audience_network"],
            "facebook_positions": ["feed"],
            # Required since API v23.0 - set to 0 to use specific targeting
            "targeting_automation": {
                "advantage_audience": 0
            }
        }

        # Add age if specified (not always required)
        if core.age_min:
            targeting["age_min"] = core.age_min
        if core.age_max:
            targeting["age_max"] = core.age_max

        # Add genders if specified
        if core.genders and core.genders != [1, 2]:
            targeting["genders"] = core.genders

        # Add interests (using resolved IDs)
        if resolved_interests:
            targeting["interests"] = [
                {"id": i["id"], "name": i["name"]}
                for i in resolved_interests
            ]

        return targeting

    def _get_optimization_goal(self, objective: CampaignObjective) -> str:
        """Map campaign objective to optimization goal."""
        mapping = {
            CampaignObjective.LINK_CLICKS: "LINK_CLICKS",
            CampaignObjective.OUTCOME_TRAFFIC: "LINK_CLICKS",
            CampaignObjective.OUTCOME_AWARENESS: "REACH",
            CampaignObjective.OUTCOME_LEADS: "LEAD_GENERATION"
        }
        return mapping.get(objective, "LINK_CLICKS")

    async def _upload_image(self, image_url: str) -> str:
        """Upload an image and return the image hash."""
        url = f"{self.BASE_URL}/{self.ad_account_id}/adimages"

        # Download the image
        async with httpx.AsyncClient() as client:
            img_response = await client.get(image_url)
            img_response.raise_for_status()
            image_bytes = img_response.content

        # Upload as base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        data = {
            "bytes": image_b64,
            "access_token": self.access_token
        }

        response = await self._make_request("POST", url, data)

        # Response contains {images: {hash: {hash: "xxx"}}}
        images = response.get("images", {})
        for key, value in images.items():
            return value.get("hash")

        raise MetaAPIError("Failed to get image hash from upload response")

    async def _upload_video(self, video_url: str) -> str:
        """Upload a video and return the video ID (async with polling)."""
        url = f"{self.BASE_URL}/{self.ad_account_id}/advideos"

        # Download the video
        async with httpx.AsyncClient(timeout=120.0) as client:
            video_response = await client.get(video_url)
            video_response.raise_for_status()
            video_bytes = video_response.content

        # Upload video
        files = {"source": ("video.mp4", video_bytes, "video/mp4")}
        data = {
            "access_token": self.access_token,
            "name": f"adforge_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, data=data, files=files)
            response.raise_for_status()
            result = response.json()

        video_id = result.get("id")
        if not video_id:
            raise MetaAPIError("Failed to get video ID from upload response")

        # Poll for video encoding completion
        await self._wait_for_video_ready(video_id)

        return video_id

    async def _wait_for_video_ready(
        self,
        video_id: str,
        timeout: int = 120,
        poll_interval: int = 5
    ) -> None:
        """Poll until video is ready for use."""
        url = f"{self.BASE_URL}/{video_id}"
        params = {
            "fields": "status",
            "access_token": self.access_token
        }

        start_time = datetime.utcnow()
        while (datetime.utcnow() - start_time).seconds < timeout:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            status = data.get("status", {})
            video_status = status.get("video_status")

            if video_status == "ready":
                return
            elif video_status in ("error", "expired"):
                raise MetaAPIError(f"Video processing failed: {video_status}")

            await asyncio.sleep(poll_interval)

        raise MetaAPIError("Video processing timed out")

    async def _create_creative(
        self,
        ad_copy: AdCopy,
        settings: CampaignSettings,
        asset_id: str,
        is_video: bool
    ) -> str:
        """Create an ad creative."""
        url = f"{self.BASE_URL}/{self.ad_account_id}/adcreatives"

        # Build destination URL with UTMs
        destination_url = build_utm_url(
            settings.destination_url,
            {
                "utm_source": settings.utm_params.utm_source,
                "utm_medium": settings.utm_params.utm_medium,
                "utm_campaign": settings.utm_params.utm_campaign,
                "utm_content": settings.utm_params.utm_content
            }
        )

        # Map CTA type
        cta_type = ad_copy.cta.value

        if is_video:
            object_story_spec = {
                "page_id": self.page_id,
                "video_data": {
                    "video_id": asset_id,
                    "title": sanitize_for_meta(ad_copy.headline),
                    "message": sanitize_for_meta(ad_copy.body),
                    "call_to_action": {
                        "type": cta_type,
                        "value": {"link": destination_url}
                    }
                }
            }
        else:
            object_story_spec = {
                "page_id": self.page_id,
                "link_data": {
                    "message": sanitize_for_meta(ad_copy.body),
                    "link": destination_url,
                    "name": sanitize_for_meta(ad_copy.headline),
                    "image_hash": asset_id,
                    "call_to_action": {
                        "type": cta_type,
                        "value": {"link": destination_url}
                    }
                }
            }

        data = {
            "name": f"Creative - {ad_copy.headline[:20]}",
            "object_story_spec": object_story_spec,
            "access_token": self.access_token
        }

        response = await self._make_request("POST", url, data)
        return response["id"]

    async def _create_ad(
        self,
        adset_id: str,
        creative_id: str,
        headline: str
    ) -> str:
        """Create the final ad object (PAUSED)."""
        url = f"{self.BASE_URL}/{self.ad_account_id}/ads"

        ad_name = sanitize_for_meta(
            f"Ad - {headline[:20]} - {datetime.now().strftime('%Y%m%d')}"
        )

        data = {
            "name": ad_name,
            "adset_id": adset_id,
            "creative": {"creative_id": creative_id},
            "status": "PAUSED",
            "access_token": self.access_token
        }

        response = await self._make_request("POST", url, data)
        return response["id"]

    async def get_ad_status(self, ad_id: str) -> Dict[str, Any]:
        """Get the status of an ad including review feedback."""
        url = f"{self.BASE_URL}/{ad_id}"

        # Request ad_review_feedback for review status
        # effective_status includes: PENDING_REVIEW, DISAPPROVED, PREAPPROVED, ACTIVE, etc.
        params = {
            "fields": "status,effective_status,configured_status,ad_review_feedback,created_time,adset_id,campaign_id",
            "access_token": self.access_token
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)

            if response.status_code != 200:
                error_data = response.json().get("error", {})
                logger.warning(f"Ad status query failed: {error_data.get('message', 'Unknown error')}")
                # Return a default status if query fails
                return {
                    "id": ad_id,
                    "status": "UNKNOWN",
                    "effective_status": "UNKNOWN",
                    "configured_status": "UNKNOWN",
                    "ad_review_feedback": None,
                    "created_time": None
                }

            return response.json()

    async def activate_ad(self, ad_id: str) -> Dict[str, Any]:
        """
        Activate an ad by setting it and its parent objects to ACTIVE.

        This method:
        1. Gets the ad's parent IDs (adset_id, campaign_id)
        2. Sets Campaign status to ACTIVE
        3. Sets AdSet status to ACTIVE
        4. Sets Ad status to ACTIVE

        Returns:
            Dict with activation results including the new effective_status
        """
        logger.info(f"[ACTIVATE] Starting activation for ad {ad_id}")

        # Step 1: Get parent IDs
        ad_info = await self.get_ad_status(ad_id)
        adset_id = ad_info.get("adset_id")
        campaign_id = ad_info.get("campaign_id")

        if not adset_id or not campaign_id:
            # Fetch adset to get campaign_id if not in ad response
            adset_url = f"{self.BASE_URL}/{ad_id}"
            params = {
                "fields": "adset{id,campaign_id}",
                "access_token": self.access_token
            }
            async with httpx.AsyncClient() as client:
                resp = await client.get(adset_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    adset_data = data.get("adset", {})
                    adset_id = adset_data.get("id")
                    campaign_id = adset_data.get("campaign_id")

        results = {
            "ad_id": ad_id,
            "adset_id": adset_id,
            "campaign_id": campaign_id,
            "campaign_activated": False,
            "adset_activated": False,
            "ad_activated": False
        }

        # Step 2: Activate Campaign
        if campaign_id:
            try:
                await self._update_status(campaign_id, "ACTIVE")
                results["campaign_activated"] = True
                logger.info(f"[ACTIVATE] Campaign {campaign_id} activated")
            except MetaAPIError as e:
                logger.error(f"[ACTIVATE] Failed to activate campaign: {e.message}")
                raise

        # Step 3: Activate AdSet
        if adset_id:
            try:
                await self._update_status(adset_id, "ACTIVE")
                results["adset_activated"] = True
                logger.info(f"[ACTIVATE] AdSet {adset_id} activated")
            except MetaAPIError as e:
                logger.error(f"[ACTIVATE] Failed to activate adset: {e.message}")
                raise

        # Step 4: Activate Ad
        try:
            await self._update_status(ad_id, "ACTIVE")
            results["ad_activated"] = True
            logger.info(f"[ACTIVATE] Ad {ad_id} activated")
        except MetaAPIError as e:
            logger.error(f"[ACTIVATE] Failed to activate ad: {e.message}")
            raise

        # Step 5: Get final status
        final_status = await self.get_ad_status(ad_id)
        results["effective_status"] = final_status.get("effective_status")
        results["configured_status"] = final_status.get("configured_status")

        logger.info(f"[ACTIVATE] Complete! effective_status={results['effective_status']}")

        return results

    async def _update_status(self, object_id: str, status: str) -> None:
        """Update the status of a Meta Ads object (campaign, adset, or ad)."""
        url = f"{self.BASE_URL}/{object_id}"

        data = {
            "status": status,
            "access_token": self.access_token
        }

        await self._make_request("POST", url, data)

    async def _make_request(
        self,
        method: str,
        url: str,
        data: Dict[str, Any],
        retries: int = 3
    ) -> Dict[str, Any]:
        """Make a request to the Meta API with retry logic."""
        import json as json_module

        # Check if this request has complex nested data (like targeting)
        # If so, send as JSON instead of form-encoded
        has_complex_data = any(
            key in data for key in ["targeting", "object_story_spec", "creative"]
        )

        if has_complex_data:
            # Send as JSON - httpx will handle serialization
            payload = data
        else:
            # Convert nested dicts to JSON strings for form data
            payload = {}
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    payload[key] = json_module.dumps(value)
                else:
                    payload[key] = value

        for attempt in range(retries):
            async with httpx.AsyncClient(timeout=60.0) as client:
                if method == "POST":
                    if has_complex_data:
                        response = await client.post(url, json=payload)
                    else:
                        response = await client.post(url, data=payload)
                else:
                    response = await client.get(url, params=payload)

                if response.status_code == 200:
                    return response.json()

                error_data = response.json().get("error", {})
                error_code = error_data.get("code")
                error_subcode = error_data.get("error_subcode")
                error_message = error_data.get("message", "Unknown error")

                # Log the error with request details
                log_data = {k: v for k, v in payload.items() if k != "access_token"}
                logger.error(f"[META API ERROR] {url}")
                logger.error(f"  Message: {error_message}")
                logger.error(f"  Code: {error_code}, Subcode: {error_subcode}")
                logger.error(f"  Request data: {json_module.dumps(log_data, indent=2)}")

                # Check for rate limiting
                if (error_code in self.RATE_LIMIT_CODES or
                        error_subcode in self.RATE_LIMIT_SUBCODES):
                    if attempt < retries - 1:
                        wait_time = (attempt + 1) * 60  # Exponential backoff
                        await asyncio.sleep(wait_time)
                        continue

                raise MetaAPIError(
                    message=error_message,
                    code=error_code,
                    subcode=error_subcode,
                    error_data=error_data
                )

        raise MetaAPIError("Max retries exceeded")
