import pytest

from app.infrastructure.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_load_environment(monkeypatch):
    monkeypatch.setenv("APP_NAME", "EDITH test")
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = get_settings()

    assert settings.app_name == "EDITH test"
    assert settings.app_version == "1.2.3"
    assert settings.environment == "test"
    assert settings.debug is True
    assert settings.log_level == "DEBUG"
