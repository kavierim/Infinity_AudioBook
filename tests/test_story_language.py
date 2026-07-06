"""Tests for story language normalization and story.md updates."""

from __future__ import annotations

from pathlib import Path

import pytest

from infinity_audiobook.story_state import (
    normalize_story_language,
    read_story,
    write_story_language,
)

SAMPLE_STORY = """# Story State

## title

Test

## genre

Test

## perspective

first-person

## language

en

## narrator_tone

Calm.

## past

*(no events yet)*

## current_state

Start.

## future_plan

Begin.

## references

"""


def test_normalize_story_language() -> None:
    assert normalize_story_language("en") == "en"
    assert normalize_story_language("Finnish") == "fi"
    assert normalize_story_language("suomi") == "fi"
    assert normalize_story_language("2") == "fi"
    assert normalize_story_language("de") is None


def test_write_story_language(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    path.write_text(SAMPLE_STORY, encoding="utf-8")

    code = write_story_language(path, "Finnish")
    assert code == "fi"
    assert read_story(path).language == "fi"


def test_write_story_language_rejects_unknown(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    path.write_text(SAMPLE_STORY, encoding="utf-8")
    with pytest.raises(ValueError):
        write_story_language(path, "swedish")
