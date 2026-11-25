"""NoticeSetu runtime configuration loaded via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with zero-config local fallbacks for optional services."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    TTS_PROVIDER: Literal["sarvam", "bhashini", "none"] = "sarvam"
    SARVAM_API_KEY: str = ""
    SARVAM_TTS_MODEL: str = "bulbul:v3"
    SARVAM_TTS_SPEAKER: str = "shubh"
    BHASHINI_API_KEY: str = ""
    BHASHINI_USER_ID: str = ""

    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""

    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_AUDIO_BUCKET: str = "notice-audio"

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    FRONTEND_BASE_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    RATE_LIMIT_MAX_REQUESTS: int = 30
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    @property
    def allowed_origins_list(self) -> list[str]:
        origins = [
            item.strip()
            for item in self.ALLOWED_ORIGINS.split(",")
            if item.strip() and item.strip() != "*"
        ]
        return origins or ["http://localhost:3000"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
