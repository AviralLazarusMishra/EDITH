from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration for the EDITH application.

    Settings are loaded from environment variables and the project's
    .env file. Environment variables take precedence over values
    defined in .env.
    """

    # Application
    app_name: str = "EDITH"
    app_version: str = "0.1.0"

    # Runtime environment
    environment: str = "development"
    debug: bool = False

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return the application's cached Settings instance.

    Caching ensures that configuration is loaded only once
    during the application's lifecycle.
    """
    return Settings()