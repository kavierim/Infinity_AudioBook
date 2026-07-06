"""Story settings loaded from settings.ini."""

from __future__ import annotations

import configparser
import logging
from dataclasses import dataclass
from pathlib import Path

from infinity_audiobook.settings_paths import SETTINGS_FILENAME
from infinity_audiobook.story_state import normalize_story_language

logger = logging.getLogger(__name__)

DEFAULT_STORY_LANGUAGE = "en"


@dataclass(frozen=True)
class StoryConfig:
    language: str = DEFAULT_STORY_LANGUAGE


def load_story_config_from_parser(
    parser: configparser.ConfigParser | None,
    *,
    default_language: str = DEFAULT_STORY_LANGUAGE,
) -> StoryConfig:
    """Parse story settings from an already-loaded ConfigParser."""
    if parser is None or "story" not in parser:
        return StoryConfig(language=default_language)

    raw = parser["story"].get("language", "").strip()
    if not raw:
        return StoryConfig(language=default_language)

    normalized = normalize_story_language(raw)
    if normalized is None:
        logger.warning(
            "Invalid story language %r — using %s",
            raw,
            default_language,
        )
        return StoryConfig(language=default_language)

    return StoryConfig(language=normalized)


def load_story_config(
    path: Path,
    *,
    default_language: str = DEFAULT_STORY_LANGUAGE,
) -> StoryConfig:
    """Load story settings from settings.ini.

    When ``[story]`` or ``language`` is missing, *default_language* is used
    (typically the current value from ``story.md``).
    """
    from infinity_audiobook.settings import read_settings_parser

    return load_story_config_from_parser(
        read_settings_parser(path),
        default_language=default_language,
    )


__all__ = [
    "DEFAULT_STORY_LANGUAGE",
    "SETTINGS_FILENAME",
    "StoryConfig",
    "load_story_config",
    "load_story_config_from_parser",
]
