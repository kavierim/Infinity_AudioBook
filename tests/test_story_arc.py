"""Tests for story arc refresh (tier 3)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from infinity_audiobook.story_arc import arc_refresh_due, maybe_refresh_story_arc
from infinity_audiobook.story_state import read_story, story_arc_section_present, write_story_arc

STORY_WITH_ARC = """# Story

## title
Test

## genre
Fiction

## perspective
first-person

## language
en

## narrator_tone
Calm

## story_arc

Act I: departure from the harbor.

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


def test_arc_refresh_due_requires_section() -> None:
    assert arc_refresh_due(segment_count=20, arc_refresh_every=20, has_story_arc_section=False) is False
    assert arc_refresh_due(segment_count=20, arc_refresh_every=20, has_story_arc_section=True) is True
    assert arc_refresh_due(segment_count=19, arc_refresh_every=20, has_story_arc_section=True) is False


def test_story_arc_section_present() -> None:
    assert story_arc_section_present(STORY_WITH_ARC) is True
    assert story_arc_section_present("## title\n\nHi") is False


def test_maybe_refresh_story_arc_uses_situation_only(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    structured_state = """Last narrated (#5):

Full narrated prose that should not reach arc refresh.

Situation:

Brief situation beat."""
    content = STORY_WITH_ARC.replace("## current_state\nBeginning", f"## current_state\n\n{structured_state}")
    path.write_text(content, encoding="utf-8")

    refresher = MagicMock()
    refresher.refresh_story_arc.return_value = "Act II: the coast road."

    maybe_refresh_story_arc(
        path,
        refresher,
        language_name="English",
        segment_count=20,
        arc_refresh_every=20,
    )
    call_kwargs = refresher.refresh_story_arc.call_args.kwargs
    assert call_kwargs["current_state"] == "Brief situation beat."
    assert "Full narrated" not in call_kwargs["current_state"]


def test_maybe_refresh_story_arc_updates_section(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    path.write_text(STORY_WITH_ARC, encoding="utf-8")

    refresher = MagicMock()
    refresher.refresh_story_arc.return_value = "Act II: the coast road."

    updated = maybe_refresh_story_arc(
        path,
        refresher,
        language_name="English",
        segment_count=20,
        arc_refresh_every=20,
    )
    assert updated is True
    state = read_story(path)
    assert "Act II" in state.story_arc
    refresher.refresh_story_arc.assert_called_once()


def test_maybe_refresh_skips_without_section(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    path.write_text(STORY_WITH_ARC.replace("## story_arc\n\nAct I: departure from the harbor.\n\n", ""), encoding="utf-8")
    refresher = MagicMock()
    assert maybe_refresh_story_arc(
        path,
        refresher,
        language_name="English",
        segment_count=20,
        arc_refresh_every=20,
    ) is False
    refresher.refresh_story_arc.assert_not_called()


def test_write_story_arc(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    path.write_text(STORY_WITH_ARC, encoding="utf-8")
    write_story_arc(path, "Updated arc beats.")
    assert "Updated arc beats" in path.read_text(encoding="utf-8")
