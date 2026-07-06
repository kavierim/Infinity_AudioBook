"""Unified settings.ini loading — single disk read for all config sections."""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path

from infinity_audiobook.llm_config import LLMConfig, load_llm_config_from_parser
from infinity_audiobook.playback_config import PlaybackConfig, load_playback_config_from_parser
from infinity_audiobook.settings_paths import SETTINGS_FILENAME
from infinity_audiobook.story_config import StoryConfig, load_story_config_from_parser


@dataclass(frozen=True)
class AppSettings:
    """LLM, playback, and story settings loaded from one settings.ini read."""

    llm: LLMConfig
    playback: PlaybackConfig
    story: StoryConfig


def read_settings_parser(path: Path) -> configparser.ConfigParser | None:
    """Read settings.ini into a ConfigParser, or None when the file is missing."""
    if not path.is_file():
        return None
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    return parser


def load_app_settings(
    path: Path,
    *,
    default_language: str = "en",
) -> AppSettings:
    """Load all settings sections from settings.ini with a single disk read."""
    parser = read_settings_parser(path)
    if parser is None:
        return AppSettings(
            llm=load_llm_config_from_parser(None, path_name=path.name),
            playback=load_playback_config_from_parser(None),
            story=load_story_config_from_parser(None, default_language=default_language),
        )
    return AppSettings(
        llm=load_llm_config_from_parser(parser, path_name=path.name),
        playback=load_playback_config_from_parser(parser),
        story=load_story_config_from_parser(parser, default_language=default_language),
    )


__all__ = [
    "AppSettings",
    "SETTINGS_FILENAME",
    "load_app_settings",
    "read_settings_parser",
]
