from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


# Enums
class AdFormat(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class CampaignObjective(str, Enum):
    LINK_CLICKS = "LINK_CLICKS"
    OUTCOME_AWARENESS = "OUTCOME_AWARENESS"
    OUTCOME_LEADS = "OUTCOME_LEADS"
    OUTCOME_TRAFFIC = "OUTCOME_TRAFFIC"
    LEAD_GENERATION = "LEAD_GENERATION"


class CTAType(str, Enum):
    LEARN_MORE = "LEARN_MORE"
    SHOP_NOW = "SHOP_NOW"
    SIGN_UP = "SIGN_UP"
    GET_QUOTE = "GET_QUOTE"
    DOWNLOAD = "DOWNLOAD"


class JobStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    PREVIEW = "preview"
    DEPLOYING = "deploying"
    LIVE = "live"
    FAILED = "failed"


# Request Models
class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="The ad prompt describing product and audience")
    brand_colors: Optional[List[str]] = Field(None, description="Brand colors as hex codes")
    logo_url: Optional[str] = Field(None, description="URL to brand logo")
    demo_video_url: Optional[str] = Field(None, description="URL to demo video")
    demo_image_url: Optional[str] = Field(None, description="URL to product image")
    destination_url: Optional[str] = Field(None, description="Landing page URL for the ad")


class CreativeRequest(BaseModel):
    job_id: str


class DeployRequest(BaseModel):
    job_id: str
    approved_copy: Dict[str, str] = Field(..., description="Approved ad copy")
    approved_audience: Dict[str, Any] = Field(..., description="Approved audience targeting")
    approved_settings: Dict[str, Any] = Field(..., description="Approved campaign settings")
    privacy_policy_url: Optional[str] = Field(None, description="Privacy policy URL (required for Lead Generation campaigns)")
    sandbox_mode: bool = True


# Response Models
class AdCopy(BaseModel):
    headline: str
    body: str
    cta: CTAType = CTAType.LEARN_MORE


class GeoLocation(BaseModel):
    key: str
    radius: Optional[int] = None
    distance_unit: Optional[str] = "mile"


class GeoLocations(BaseModel):
    countries: List[str] = ["NG"]  # Default to Nigeria
    cities: Optional[List[GeoLocation]] = None


class Interest(BaseModel):
    id: Optional[str] = None
    name: str
    relevance: Optional[str] = None
    reasoning: Optional[str] = None


class Behavior(BaseModel):
    name: str
    reasoning: Optional[str] = None


class CoreAudience(BaseModel):
    age_min: int = 25
    age_max: int = 45
    genders: List[int] = [1, 2]  # 1=male, 2=female
    geo_locations: GeoLocations = Field(default_factory=GeoLocations)
    locales: List[int] = [24]  # 24=English (All)


class Audience(BaseModel):
    core_audience: CoreAudience = Field(default_factory=CoreAudience)
    interests: List[Interest] = []
    behaviors: List[Behavior] = []
    excluded_audiences: List[Dict[str, str]] = []
    audience_rationale: str = ""
    targeting_confidence: str = "medium"
    estimated_audience_size_note: str = ""
    budget_fit_note: str = ""
    suggested_follow_up_audiences: List[str] = []


class UTMParams(BaseModel):
    utm_source: str = "facebook"
    utm_medium: str = "paid_social"
    utm_campaign: str = ""
    utm_content: str = ""
    utm_term: str = ""


class CampaignSettings(BaseModel):
    objective: CampaignObjective = CampaignObjective.OUTCOME_TRAFFIC
    daily_budget: float = 10.0  # In major currency units (e.g., NGN, GBP, USD)
    duration_days: int = 5
    start_paused: bool = True
    destination_url: str = ""
    utm_params: UTMParams = Field(default_factory=UTMParams)


class CreativeUrls(BaseModel):
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    voiceover_url: Optional[str] = None


class MetaIds(BaseModel):
    campaign_id: Optional[str] = None
    adset_id: Optional[str] = None
    creative_id: Optional[str] = None
    ad_id: Optional[str] = None


class GenerateResponse(BaseModel):
    job_id: str
    ad_copy: AdCopy
    audience: Audience
    campaign_settings: CampaignSettings
    creative_brief: str
    voiceover_script: Optional[str] = None
    image_prompt: Optional[str] = None
    format: AdFormat


class CreativeResponse(BaseModel):
    job_id: str
    status: str
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    voiceover_url: Optional[str] = None


class PreviewResponse(BaseModel):
    job_id: str
    status: JobStatus
    prompt: str
    ad_copy: Optional[AdCopy] = None
    audience: Optional[Audience] = None
    campaign_settings: Optional[CampaignSettings] = None
    creative_urls: Optional[CreativeUrls] = None
    creative_brief: Optional[str] = None
    voiceover_script: Optional[str] = None
    format: Optional[AdFormat] = None


class DeployResponse(BaseModel):
    job_id: str
    status: str
    campaign_id: Optional[str] = None
    adset_id: Optional[str] = None
    creative_id: Optional[str] = None
    ad_id: Optional[str] = None
    error: Optional[str] = None


class StatusResponse(BaseModel):
    ad_id: str
    effective_status: Optional[str] = None  # PENDING_REVIEW, DISAPPROVED, PREAPPROVED, ACTIVE, PAUSED, etc.
    configured_status: Optional[str] = None  # ACTIVE, PAUSED, DELETED, ARCHIVED
    ad_review_feedback: Optional[Dict[str, Any]] = None  # Detailed review feedback from Meta
    created_at: Optional[str] = None
    campaign_id: Optional[str] = None
    adset_id: Optional[str] = None

    @property
    def is_pending_review(self) -> bool:
        return self.effective_status == "PENDING_REVIEW"

    @property
    def is_approved(self) -> bool:
        return self.effective_status in ["ACTIVE", "PAUSED", "PREAPPROVED", "CAMPAIGN_PAUSED", "ADSET_PAUSED"]

    @property
    def is_disapproved(self) -> bool:
        return self.effective_status == "DISAPPROVED"

    @property
    def can_activate(self) -> bool:
        """Check if the ad can be activated (approved but paused)."""
        return (
            self.effective_status in ["PAUSED", "CAMPAIGN_PAUSED", "ADSET_PAUSED", "PREAPPROVED"]
            and self.configured_status == "PAUSED"
        )


class ActivateResponse(BaseModel):
    ad_id: str
    success: bool
    effective_status: Optional[str] = None
    configured_status: Optional[str] = None
    campaign_activated: bool = False
    adset_activated: bool = False
    ad_activated: bool = False
    error: Optional[str] = None


# Claude Orchestrator Output Model
class ClaudeAdStrategy(BaseModel):
    ad_copy: AdCopy
    voiceover_script: str
    image_prompt: str
    format: AdFormat
    campaign: CampaignSettings
    audience: Audience
    creative_brief: str
