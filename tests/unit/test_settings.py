from app.infrastructure.config import get_settings


def test_settings_load():
    settings = get_settings()

    assert settings.app_name == "EDITH"
    assert settings.app_version == "0.1.0"
    assert settings.environment == "development"
    assert isinstance(settings.debug, bool)
    assert settings.log_level == "DEBUG"