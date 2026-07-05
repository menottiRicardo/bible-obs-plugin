from pathlib import Path

from app.settings import Settings


def test_defaults():
    s = Settings()
    assert s.port == 8777
    assert s.data_path == Path("data/rvr1960.json")


def test_env_override(monkeypatch):
    monkeypatch.setenv("BIBLE_PORT", "9000")
    assert Settings().port == 9000


def test_token_defaults_empty(monkeypatch):
    monkeypatch.delenv("BIBLE_TOKEN", raising=False)
    assert Settings().token == ""


def test_token_env_override(monkeypatch):
    monkeypatch.setenv("BIBLE_TOKEN", "abc123")
    assert Settings().token == "abc123"
