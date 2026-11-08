from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_stops_with_clear_message_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    at = AppTest.from_file(APP, default_timeout=30).run()

    assert not at.exception
    assert "GEMINI_API_KEY is not set" in at.error[0].value


def test_app_shows_uploader_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    at = AppTest.from_file(APP, default_timeout=30).run()

    assert not at.exception
    assert not at.error
