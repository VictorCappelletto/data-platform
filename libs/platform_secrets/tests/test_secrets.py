import pytest

from platform_secrets.resolver import SecretNotFoundError, get_secret


def test_get_secret_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEMO_DB_PASSWORD", "s3cret")
    assert get_secret("DEMO_DB_PASSWORD") == "s3cret"


def test_get_secret_default():
    assert get_secret("MISSING_SECRET_XYZ", default="fallback") == "fallback"


def test_get_secret_missing_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MISSING_SECRET_XYZ", raising=False)
    with pytest.raises(SecretNotFoundError):
        get_secret("MISSING_SECRET_XYZ")
