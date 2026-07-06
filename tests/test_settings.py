"""Tests for unified settings.ini loading."""

from __future__ import annotations

from pathlib import Path

from infinity_audiobook.llm_config import DEFAULT_GEMINI_MODEL
from infinity_audiobook.playback_config import DEFAULT_MAX_BUFFER_SECONDS, DEFAULT_SEGMENT_GAP_SECONDS
from infinity_audiobook.settings import load_app_settings, read_settings_parser
from infinity_audiobook.story_config import DEFAULT_STORY_LANGUAGE


def test_read_settings_parser_missing_file(tmp_path: Path) -> None:
    assert read_settings_parser(tmp_path / "missing.ini") is None


def test_load_app_settings_missing_file_uses_defaults(tmp_path: Path) -> None:
    settings = load_app_settings(tmp_path / "missing.ini", default_language="fi")
    assert settings.llm.provider == "gemini"
    assert settings.llm.effective_model_segment() == DEFAULT_GEMINI_MODEL
    assert settings.playback.segment_gap_seconds == DEFAULT_SEGMENT_GAP_SECONDS
    assert settings.playback.max_buffer_seconds == DEFAULT_MAX_BUFFER_SECONDS
    assert settings.story.language == "fi"


def test_load_app_settings_all_sections(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text(
        "[llm]\n"
        "provider = gemini\n"
        "model_segment = gemini-2.5-flash\n"
        "model_summary = gemini-2.5-flash-lite\n"
        "model_arc = gemini-2.5-pro\n"
        "arc_refresh_every = 15\n"
        "[playback]\n"
        "segment_gap_seconds = 0.5\n"
        "max_buffer_seconds = 120\n"
        "[story]\n"
        "language = fi\n",
        encoding="utf-8",
    )
    settings = load_app_settings(ini, default_language=DEFAULT_STORY_LANGUAGE)
    assert settings.llm.model_segment == "gemini-2.5-flash"
    assert settings.llm.model_summary == "gemini-2.5-flash-lite"
    assert settings.llm.model_arc == "gemini-2.5-pro"
    assert settings.llm.arc_refresh_every == 15
    assert settings.playback.segment_gap_seconds == 0.5
    assert settings.playback.max_buffer_seconds == 120.0
    assert settings.story.language == "fi"
