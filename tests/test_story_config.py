"""Tests for story settings."""

from __future__ import annotations

from pathlib import Path

from infinity_audiobook.story_config import (
    DEFAULT_STORY_LANGUAGE,
    StoryConfig,
    load_story_config,
)


def test_missing_file_uses_default_language() -> None:
    config = load_story_config(Path("missing.ini"), default_language="fi")
    assert config.language == "fi"


def test_missing_story_section_uses_default_language(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[playback]\nsegment_gap_seconds = 1.0\n", encoding="utf-8")
    config = load_story_config(ini, default_language="fi")
    assert config.language == "fi"


def test_load_language_from_ini(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[story]\nlanguage = fi\n", encoding="utf-8")
    config = load_story_config(ini)
    assert config.language == "fi"


def test_load_language_accepts_name(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[story]\nlanguage = Finnish\n", encoding="utf-8")
    config = load_story_config(ini)
    assert config.language == "fi"


def test_invalid_language_falls_back(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[story]\nlanguage = klingon\n", encoding="utf-8")
    config = load_story_config(ini, default_language="en")
    assert config.language == "en"


def test_story_config_default() -> None:
    assert StoryConfig().language == DEFAULT_STORY_LANGUAGE
