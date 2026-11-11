"""Tests must behave the same on every machine, whatever is in the developer's .env."""
import pytest


@pytest.fixture(autouse=True)
def _gemini_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
