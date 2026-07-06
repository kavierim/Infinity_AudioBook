"""Tests for periodic story compaction."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from infinity_audiobook.story_compact import maybe_compact_story
from infinity_audiobook.story_state import past_line_count, read_story


def _story_with_past_lines(n: int) -> str:
    lines = "\n".join(f"- [t] #{i}: event {i}" for i in range(1, n + 1))
    return f"""# Story

## title
T

## genre
G

## perspective
second-person

## language
en

## narrator_tone
Calm

## summary

*(no summary yet)*

## past

{lines}

## current_state
Now

## future_plan
Next

## references

"""


def test_maybe_compact_story_trims_past(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    path.write_text(_story_with_past_lines(30), encoding="utf-8")

    summarizer = MagicMock()
    summarizer.summarize_past.return_value = "Compressed history of 20 events."

    assert maybe_compact_story(path, summarizer, language_name="English") is True

    state = read_story(path)
    assert state.summary == "Compressed history of 20 events."
    assert past_line_count(state.past) == 10
    summarizer.summarize_past.assert_called_once()


def test_maybe_compact_story_skips_below_threshold(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    path.write_text(_story_with_past_lines(10), encoding="utf-8")

    summarizer = MagicMock()
    assert maybe_compact_story(path, summarizer, language_name="English") is False
    summarizer.summarize_past.assert_not_called()
