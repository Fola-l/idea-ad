import json
import base64
import httpx
from typing import Optional, Dict, Any
from anthropic import Anthropic

from app.config import get_settings
from app.models import (
    ClaudeAdStrategy, AdCopy, Audience, CoreAudience,
    CampaignSettings, Interest, Behavior, GeoLocations,
    GeoLocation, UTMParams, AdFormat, CampaignObjective, CTAType
)

SYSTEM_PROMPT = """You are an expert digital marketing strategist specializing in Facebook/Instagram ads. Your job is to create complete ad campaigns from a single prompt.

## Context
- Primary market: United Kingdom (UK)
- Platform: Facebook/Instagram Ads
- Goal: Create ads that convert, not just get impressions

## Your Task
Given a product description and any visual assets, generate a complete ad strategy including:
1. Ad copy (headline, body, CTA)
2. Voiceover script (for video ads)
3. Image generation prompt (for DALL-E)
4. Audience targeting (detailed UK-focused)
5. Campaign settings

## Audience Intelligence Guidelines

### Signal Analysis
Extract targeting signals from:
- Explicit mentions ("developers", "startup founders", etc.)
- Pain points implied by the product
- Buyer psychology (technical vs non-technical, B2B vs B2C)
- User constraints in the prompt

### Product Category Intelligence
- API/Developer tools → job titles, coding interests, specific SaaS tools
- No-code/AI tools → Zapier, Notion, Make.com users
- Mac productivity → macOS users, productivity apps, indie hackers
- Logistics/Delivery → e-commerce, supply chain, business owners

### UK Market Specificity
- Tech products: London, Manchester, Bristol, Edinburgh (main hubs)
- B2B SaaS: London + commuter belt
- Consumer productivity: broader UK coverage
- Always include English language targeting

## Format Decision
- Product demo/feature showcase → VIDEO
- Announcement/offer/awareness → IMAGE
- If user uploads demo video → VIDEO
- If user uploads image only → IMAGE (unless prompt asks for video)

## Output Format
Return ONLY valid JSON matching this structure:
{
  "ad_copy": {
    "headline": "max 40 chars, punchy, scroll-stopping",
    "body": "max 125 chars, benefit-focused",
    "cta": "LEARN_MORE | SHOP_NOW | SIGN_UP | GET_QUOTE | DOWNLOAD"
  },
  "voiceover_script": "15-30 second script, conversational, ends with CTA",
  "image_prompt": "DALL-E prompt for ad image, professional, clean, no text",
  "format": "image | video",
  "campaign": {
    "objective": "OUTCOME_TRAFFIC | OUTCOME_AWARENESS | OUTCOME_LEADS | LINK_CLICKS",
    "daily_budget": 10,
    "duration_days": 5,
    "start_paused": true
  },
  "audience": {
    "core_audience": {
      "age_min": 25,
      "age_max": 45,
      "genders": [1, 2],
      "geo_locations": {
        "countries": ["NG"],
        "cities": []
      },
      "locales": [24]
    },
    "interests": [
      {"name": "Interest Name", "relevance": "high|medium|low", "reasoning": "why this interest"}
    ],
    "behaviors": [
      {"name": "Behavior Name", "reasoning": "why this behavior"}
    ],
    "excluded_audiences": [
      {"name": "Excluded Segment", "reasoning": "why exclude"}
    ],
    "audience_rationale": "Full paragraph explaining targeting logic",
    "targeting_confidence": "high | medium | low",
    "estimated_audience_size_note": "Commentary on expected reach",
    "budget_fit_note": "How budget fits audience size",
    "suggested_follow_up_audiences": ["Lookalike audience suggestions"]
  },
  "creative_brief": "1-2 sentence summary of the creative direction"
}

## Important Rules
- Ad copy must be punchy, not corporate
- Lead with outcome/benefit, not features
- All campaigns start PAUSED (start_paused: true)
- Budget should match prompt if specified, otherwise default 10/day in local currency
- Return ONLY the JSON, no markdown code blocks or explanations
"""


class ClaudeOrchestrator:
    def __init__(self):
        settings = get_settings()
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-20250514"

    async def generate_ad_strategy(
        self,
        prompt: str,
        demo_image_base64: Optional[str] = None,
        demo_video_frames: Optional[list] = None,
        destination_url: Optional[str] = None
    ) -> ClaudeAdStrategy:
        """
        Generate a complete ad strategy from a prompt.

        Args:
            prompt: User's ad request
            demo_image_base64: Base64 encoded image for vision analysis
            demo_video_frames: List of base64 encoded video frames for analysis
            destination_url: Landing page URL

        Returns:
            ClaudeAdStrategy with all ad components
        """
        messages = []

        # Build the user message content
        content = []

        # Add image if provided (for vision analysis)
        if demo_image_base64:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": demo_image_base64
                }
            })

        # Add video frames if provided
        if demo_video_frames:
            for i, frame in enumerate(demo_video_frames[:3]):  # Max 3 frames
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": frame
                    }
                })

        # Add the text prompt
        user_text = f"""Create a Facebook ad campaign for the following:

{prompt}

{"Destination URL: " + destination_url if destination_url else ""}

{"I've attached product visuals for you to analyze for targeting insights." if demo_image_base64 or demo_video_frames else ""}

Return ONLY the JSON response with no additional text."""

        content.append({"type": "text", "text": user_text})

        messages.append({"role": "user", "content": content})

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=messages
        )

        # Parse response
        response_text = response.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        # Parse JSON
        strategy_data = json.loads(response_text)

        # Convert to Pydantic model
        return self._parse_strategy(strategy_data, destination_url)

    def _parse_strategy(
        self,
        data: Dict[str, Any],
        destination_url: Optional[str] = None
    ) -> ClaudeAdStrategy:
        """Parse Claude's JSON response into a ClaudeAdStrategy model."""

        # Parse ad copy
        ad_copy_data = data.get("ad_copy", {})
        cta_str = ad_copy_data.get("cta", "LEARN_MORE")
        try:
            cta = CTAType(cta_str)
        except ValueError:
            cta = CTAType.LEARN_MORE

        ad_copy = AdCopy(
            headline=ad_copy_data.get("headline", ""),
            body=ad_copy_data.get("body", ""),
            cta=cta
        )

        # Parse campaign settings
        campaign_data = data.get("campaign", {})
        objective_str = campaign_data.get("objective", "OUTCOME_TRAFFIC")
        try:
            objective = CampaignObjective(objective_str)
        except ValueError:
            objective = CampaignObjective.OUTCOME_TRAFFIC

        campaign = CampaignSettings(
            objective=objective,
            daily_budget=float(campaign_data.get("daily_budget", 10)),
            duration_days=int(campaign_data.get("duration_days", 5)),
            start_paused=campaign_data.get("start_paused", True),
            destination_url=destination_url or "",
            utm_params=UTMParams(
                utm_source="facebook",
                utm_medium="paid_social",
                utm_campaign=ad_copy.headline[:30].lower().replace(" ", "_"),
                utm_content="adforge"
            )
        )

        # Parse audience
        audience_data = data.get("audience", {})
        core_data = audience_data.get("core_audience", {})
        geo_data = core_data.get("geo_locations", {})

        cities = []
        for city in geo_data.get("cities", []):
            if isinstance(city, str):
                # Claude returned city as string instead of dict
                cities.append(GeoLocation(key=city))
            elif isinstance(city, dict):
                cities.append(GeoLocation(
                    key=city.get("key", ""),
                    radius=city.get("radius"),
                    distance_unit=city.get("distance_unit", "mile")
                ))

        geo_locations = GeoLocations(
            countries=geo_data.get("countries", ["GB"]),
            cities=cities if cities else None
        )

        core_audience = CoreAudience(
            age_min=core_data.get("age_min", 25),
            age_max=core_data.get("age_max", 45),
            genders=core_data.get("genders", [1, 2]),
            geo_locations=geo_locations,
            locales=core_data.get("locales", [6])
        )

        interests = []
        for i in audience_data.get("interests", []):
            if isinstance(i, str):
                # Claude returned a simple string instead of dict
                interests.append(Interest(name=i))
            elif isinstance(i, dict):
                interests.append(Interest(
                    name=i.get("name", ""),
                    relevance=i.get("relevance"),
                    reasoning=i.get("reasoning")
                ))

        behaviors = []
        for b in audience_data.get("behaviors", []):
            if isinstance(b, str):
                # Claude returned a simple string instead of dict
                behaviors.append(Behavior(name=b))
            elif isinstance(b, dict):
                behaviors.append(Behavior(
                    name=b.get("name", ""),
                    reasoning=b.get("reasoning")
                ))

        # Handle excluded_audiences - could be strings or dicts
        excluded_raw = audience_data.get("excluded_audiences", [])
        excluded_audiences = []
        for e in excluded_raw:
            if isinstance(e, str):
                excluded_audiences.append({"name": e, "reasoning": ""})
            elif isinstance(e, dict):
                excluded_audiences.append(e)

        audience = Audience(
            core_audience=core_audience,
            interests=interests,
            behaviors=behaviors,
            excluded_audiences=excluded_audiences,
            audience_rationale=audience_data.get("audience_rationale", ""),
            targeting_confidence=audience_data.get("targeting_confidence", "medium"),
            estimated_audience_size_note=audience_data.get("estimated_audience_size_note", ""),
            budget_fit_note=audience_data.get("budget_fit_note", ""),
            suggested_follow_up_audiences=audience_data.get("suggested_follow_up_audiences", [])
        )

        # Parse format
        format_str = data.get("format", "image")
        try:
            ad_format = AdFormat(format_str)
        except ValueError:
            ad_format = AdFormat.IMAGE

        return ClaudeAdStrategy(
            ad_copy=ad_copy,
            voiceover_script=data.get("voiceover_script", ""),
            image_prompt=data.get("image_prompt", ""),
            format=ad_format,
            campaign=campaign,
            audience=audience,
            creative_brief=data.get("creative_brief", "")
        )


async def fetch_image_as_base64(url: str) -> Optional[str]:
    """Fetch an image URL and return as base64."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                return base64.b64encode(response.content).decode("utf-8")
    except Exception:
        pass
    return None
