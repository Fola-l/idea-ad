from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # AI
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Meta Marketing API
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_system_token: str = ""
    meta_ad_account_id_sandbox: str = ""
    meta_ad_account_id_live: str = ""
    meta_page_id: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # Config
    sandbox_mode: bool = True
    currency_symbol: str = "₦"  # NGN (Naira), change to £ for GBP, $ for USD

    # Brand Settings (Send247)
    brand_name: str = "Send247"
    brand_url: str = "https://send247.uk/"
    brand_description: str = "Modern on-demand courier and logistics platform"
    brand_font: str = "Jetbrains Mono"
    brand_primary_color: str = "#00E676"
    brand_dark_bg: str = "#0F0F0F"
    brand_light_bg: str = "#FFFFFF"
    brand_theme: str = "Modern minimalist courier logistics UI"

    # Optional
    elevenlabs_api_key: str = ""

    @property
    def meta_ad_account_id(self) -> str:
        """Return the appropriate ad account ID based on sandbox mode, with act_ prefix."""
        account_id = self.meta_ad_account_id_sandbox if self.sandbox_mode else self.meta_ad_account_id_live
        # Meta API requires act_ prefix
        if account_id and not account_id.startswith("act_"):
            account_id = f"act_{account_id}"
        return account_id

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
