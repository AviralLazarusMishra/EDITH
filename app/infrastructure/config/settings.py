from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings:
    """
    Central configuration for the EDITH application.
    """

    app_name: str = "EDITH"
    app_version: str = "0.1.0"

    environment: str = "development"
    debug: bool = False

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()