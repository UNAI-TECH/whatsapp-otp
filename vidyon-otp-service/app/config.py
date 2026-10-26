from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    provider: Literal["mock", "whatsapp_cloud"] = "mock"
    mock_mode: Literal["success", "reject", "timeout", "unavailable"] = "success"

    send_sms_hook_secret: str = "v1,whsec_placeholder"
    provider_timeout_seconds: float = 4.0
    allowed_country_prefix: str = "+91"
    per_phone_limit_enabled: bool = True

    # WhatsApp Cloud API
    whatsapp_access_token: str = "PLACEHOLDER"
    whatsapp_phone_number_id: str = "PLACEHOLDER"
    whatsapp_graph_api_version: str = "v19.0"
    whatsapp_template_name_en: str = "otp_en"
    whatsapp_template_name_ta: str = "otp_ta"
    whatsapp_template_language_en: str = "en"
    whatsapp_template_language_ta: str = "ta"

    # OTP Platform (Project C)
    otp_platform_url: str = ""
    otp_platform_api_key: str = "PLACEHOLDER"


settings = Settings()
