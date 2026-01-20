"""Application configuration using Pydantic Settings."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Server settings
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    debug: bool = False

    # Playwright settings
    playwright_auth_dir: Path = Path("./playwright_auth")
    playwright_headless: bool = False
    playwright_timeout_ms: int = 30000

    # Rate limiting settings
    places_api_delay_ms: int = 100
    removal_action_delay_ms: int = 500

    # Upload settings
    max_upload_size_mb: int = 100
    upload_temp_dir: Path = Path("./uploads")

    # Google Places API (user provides at runtime)
    google_places_api_key: Optional[str] = None

    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024 * 5

    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.playwright_auth_dir.mkdir(parents=True, exist_ok=True)
        self.upload_temp_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
