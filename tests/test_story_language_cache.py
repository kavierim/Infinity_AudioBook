"""Tests for StoryLanguageCache mtime-based invalidation."""

from __future__ import annotations

import time
from pathlib import Path

from infinity_audiobook.story_state import StoryLanguageCache, read_story

_MINIMAL_STORY = """# Story

## title
Test

## genre
Fiction

## perspective
first-person

## language
{language}

## narrator_tone
Calm

## summary

*(no summary yet)*

## past
*(no events yet)*

## current_state
Beginning

## future_plan
Continue

## references

"""


def test_language_cache_seeds_without_read(tmp_path: Path) -> None:
    story = tmp_path / "story.md"
    story.write_text(_MINIMAL_STORY.format(language="en"), encoding="utf-8")
    cache = StoryLanguageCache(story, default="en")
    cache.seed("fi")
    assert cache.get() == "fi"


def test_language_cache_reloads_on_mtime_change(tmp_path: Path) -> None:
    story = tmp_path / "story.md"
    story.write_text(_MINIMAL_STORY.format(language="en"), encoding="utf-8")
    cache = StoryLanguageCache(story)
    cache.seed("en")
    assert cache.get() == "en"

    time.sleep(0.05)
    story.write_text(_MINIMAL_STORY.format(language="fi"), encoding="utf-8")
    assert cache.get() == "fi"
    assert read_story(story).language == "fi"
