from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "EggSentry API"
    api_prefix: str = "/api"
    debug: bool = False
    database_url: str = "sqlite:///./egg_sentry.db"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    cors_origins_raw: str = "http://localhost:5173,http://127.0.0.1:5173"
    app_timezone: str = "Asia/Manila"
    auto_create_schema: bool = True

    alert_heartbeat_timeout_minutes: int = 5
    alert_low_production_threshold: float = 0.5
    alert_uncertain_threshold: int = 3
    alert_missing_data_hours: int = 6
    alert_cooldown_minutes: int = 60

    seed_admin_username: str = "admin"
    seed_admin_password: str = "admin123"
    seed_admin_display_name: str = "Administrator"
    seed_viewer_username: str = "viewer"
    seed_viewer_password: str = "viewer123"
    seed_viewer_display_name: str = "Viewer"
    seed_device_id: str = "cam-001"
    seed_device_api_key: str = "dev-cam-001-key"
    seed_device_name: str = "Camera 1"
    seed_device_location: str = "Coop A - Layer Section"
    seed_device_num_cages: int = 4
    seed_device_num_chickens: int = 4

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
