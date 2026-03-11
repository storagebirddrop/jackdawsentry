from src.api.config import Settings


def _required_settings() -> dict[str, str]:
    return {
        "API_SECRET_KEY": "a" * 32,
        "NEO4J_PASSWORD": "neo4j-password",
        "POSTGRES_PASSWORD": "postgres-password",
        "REDIS_PASSWORD": "redis-password",
        "ENCRYPTION_KEY": "e" * 32,
        "JWT_SECRET_KEY": "jwt-secret-key-for-tests",
    }


def test_settings_accept_release_as_false():
    settings = Settings(**_required_settings(), DEBUG="release")

    assert settings.DEBUG is False


def test_settings_accept_debug_as_true():
    settings = Settings(**_required_settings(), DEBUG="debug")

    assert settings.DEBUG is True
