"""Basic tests for Phase 1. Run with:  python -m pytest
These never call any API."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
import prompts


def test_all_languages_kept():
    assert set(config.LANGS) == {"English", "Hinglish", "Kannada"}


def test_categories_and_difficulties():
    assert len(config.CATEGORIES) == 5
    assert config.DIFFICULTIES == ["Beginner", "Intermediate", "Advanced"]
    for c in config.CATEGORIES:
        assert c in prompts.CATEGORY_GUIDE
    for d in config.DIFFICULTIES:
        assert d in prompts.DIFFICULTY_GUIDE


def test_system_prompt_contains_choices():
    p = prompts.build_system_prompt("Data Analyst", "HR Interview", "Advanced", "Kannada", 6)
    assert "Data Analyst" in p and "HR Interview" in p
    assert "Advanced" in p and "Kannada" in p and "6" in p


def test_turn_note_middle_and_last():
    assert "question 3 of 5" in prompts.turn_note(2, 5)
    assert "Do NOT ask another question" in prompts.turn_note(5, 5)


def test_placeholders_detected(monkeypatch):
    monkeypatch.setattr(config, "GNANI_API_KEY", "paste_your_gnani_key_here")
    assert "GNANI_API_KEY" in config.missing_settings()
    monkeypatch.setattr(config, "GNANI_API_KEY", "real-key")
    assert "GNANI_API_KEY" not in config.missing_settings()
