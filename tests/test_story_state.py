"""Tests for story.md parsing and updates."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from infinity_audiobook.story_state import (
    CurrentStateBlocks,
    apply_segment_update,
    current_state_for_tier1_prompt,
    derive_past_append,
    format_current_state,
    last_narrated_for_replay,
    max_past_segment_id,
    next_segment_id,
    parse_current_state,
    parse_story_md,
    past_for_prompt,
    read_story,
    references_for_prompt,
    situation_for_prompt,
    split_past_for_archive,
    story_arc_for_prompt,
    story_arc_section_present,
    summary_for_prompt,
    truncate_segment_text,
    write_story_arc,
    write_story_compact,
    write_story_updates,
)

SAMPLE_STORY = """# Story State

## title

The Lighthouse

## genre

Mystery

## perspective

second-person

## language

en

## narrator_tone

Calm and intimate.

## story_arc

*(no arc yet)*

## summary

*(no summary yet)*

## past

*(no events yet)*

## current_state

The story has not begun.

## future_plan

- Open on a foggy coast

## references

- https://example.com
"""


def test_parse_sections() -> None:
    state = parse_story_md(SAMPLE_STORY)
    assert state.title == "The Lighthouse"
    assert state.genre == "Mystery"
    assert state.language == "en"
    assert "no events yet" in state.past
    assert state.is_cold_start()


def test_parse_normalizes_language_aliases() -> None:
    content = SAMPLE_STORY.replace("## language\n\nen", "## language\n\nFinnish")
    state = parse_story_md(content)
    assert state.language == "fi"


def test_append_past_replaces_empty_marker(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    path.write_text(SAMPLE_STORY, encoding="utf-8")
    state = read_story(path)

    updated = write_story_updates(
        path,
        state,
        past_append="A boat arrived.",
        segment_id=1,
        current_state="On the dock.",
        future_plan="Enter the lighthouse.",
    )

    content = path.read_text(encoding="utf-8")
    assert "*(no events yet)*" not in content
    assert "#1:" in content
    assert "A boat arrived." in content
    assert updated.current_state == "On the dock."


def test_replace_current_state_and_future_plan(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    path.write_text(SAMPLE_STORY, encoding="utf-8")
    state = read_story(path)

    write_story_updates(
        path,
        state,
        current_state="Inside the tower.",
        future_plan="Find the keeper.",
    )

    reread = read_story(path)
    assert reread.current_state == "Inside the tower."
    assert reread.future_plan == "Find the keeper."


def test_derive_past_append_uses_first_sentence() -> None:
    segment = (
        "Kolmisilmäinen tarjoilija nosti kulmakarvaa. "
        "Neon välähti oven yläpuolella."
    )
    assert derive_past_append(segment) == "Kolmisilmäinen tarjoilija nosti kulmakarvaa."


def test_derive_past_append_single_sentence_without_period() -> None:
    assert derive_past_append("Yksi pitkä lause ilman pistettä") == (
        "Yksi pitkä lause ilman pistettä"
    )


def test_next_segment_id_continues_from_past() -> None:
    past = """- [2026-01-01T00:00:00Z] #4: Event four.
- [2026-01-01T00:01:00Z] #7: Event seven."""
    assert max_past_segment_id(past) == 7
    assert next_segment_id(past) == 8
    assert next_segment_id("*(no events yet)*") == 1


def test_truncate_at_sentence_boundary() -> None:
    words = ["word"] * 250
    text = ". ".join([" ".join(words[i : i + 10]) for i in range(0, 250, 10)]) + "."
    truncated = truncate_segment_text(text, max_words=200)
    assert len(truncated.split()) <= 200
    assert truncated.endswith(".") or truncated.endswith("!")


def test_apply_segment_update() -> None:
    state = parse_story_md(SAMPLE_STORY)
    updated = apply_segment_update(
        state,
        segment_id=3,
        past_append="Light flickered.",
        current_state="Darkness.",
        future_plan="Investigate.",
    )
    assert "#3:" in updated.past
    assert "Light flickered." in updated.past
    assert updated.current_state == "Darkness."


def test_past_for_prompt_truncates_old_lines() -> None:
    lines = [f"- [{i}] #{i}: event {i}" for i in range(1, 21)]
    past = "\n".join(lines)
    prompt_past = past_for_prompt(past, max_lines=5)
    assert "15 earlier events omitted" in prompt_past
    assert "event 20" in prompt_past
    assert "#1: event 1" not in prompt_past


def test_references_for_prompt_strips_comments() -> None:
    refs = "<!-- comment -->\n\n- https://example.com"
    assert references_for_prompt(refs) == "- https://example.com"
    assert references_for_prompt("<!-- only comments -->") == ""


def test_write_story_compact(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    path.write_text(SAMPLE_STORY, encoding="utf-8")
    updated = write_story_compact(
        path,
        summary="The protagonist arrived at the lighthouse.",
        past="- [t] #1: First event.",
    )
    content = path.read_text(encoding="utf-8")
    assert "protagonist arrived" in content
    assert "#1: First event" in content
    assert updated.summary.startswith("The protagonist")


def test_split_past_for_archive() -> None:
    lines = [f"- line {i}" for i in range(30)]
    past = "\n".join(lines)
    to_archive, to_keep = split_past_for_archive(past, keep_lines=10)
    assert len(to_archive) == 20
    assert len(to_keep) == 10
    assert to_keep[-1] == "- line 29"


def test_summary_for_prompt_truncates() -> None:
    long_summary = "word " * 500
    result = summary_for_prompt(long_summary, max_words=50)
    assert result.endswith("…")
    assert len(result.split()) <= 51


def test_story_arc_for_prompt_omits_placeholder() -> None:
    assert story_arc_for_prompt("*(no arc yet)*") == ""
    assert story_arc_for_prompt("Act I: harbor") == "Act I: harbor"


def test_story_arc_section_present_flag() -> None:
    assert story_arc_section_present(SAMPLE_STORY) is True
    assert story_arc_section_present("## title\n\nx") is False


def test_write_story_arc_section(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    path.write_text(SAMPLE_STORY, encoding="utf-8")
    write_story_arc(path, "Three acts across the coast.")
    assert "Three acts" in read_story(path).story_arc


def test_concurrent_writes_serialized(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    path.write_text(SAMPLE_STORY, encoding="utf-8")

    errors: list[Exception] = []

    def writer(segment_id: int) -> None:
        try:
            state = read_story(path)
            write_story_updates(
                path,
                state,
                past_append=f"Event {segment_id}",
                segment_id=segment_id,
            )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(1, 6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    final = read_story(path)
    assert final.past.count("#") == 5


STRUCTURED_CURRENT_STATE = """Last narrated (#112):

Sieni-virkamies odotti. Marvinin optiset sensorit välähtivät punaisina.

Situation:

Sieni-virkamies odottaa lomakkeen täyttämistä."""


def test_parse_current_state_structured() -> None:
    blocks = parse_current_state(STRUCTURED_CURRENT_STATE)
    assert blocks.last_segment_id == 112
    assert "Marvinin optiset" in blocks.last_narrated
    assert "lomakkeen" in blocks.situation


def test_format_current_state_round_trip() -> None:
    formatted = format_current_state(
        "Full spoken prose here.",
        5,
        "Brief beat.",
    )
    blocks = parse_current_state(formatted)
    assert blocks.last_segment_id == 5
    assert blocks.last_narrated == "Full spoken prose here."
    assert blocks.situation == "Brief beat."


def test_parse_current_state_legacy_plain_text() -> None:
    blocks = parse_current_state("The story has not begun.")
    assert blocks.last_narrated == ""
    assert blocks.last_segment_id is None
    assert blocks.situation == "The story has not begun."


def test_parse_current_state_missing_situation_label() -> None:
    body = """Last narrated (#3):

Spoken text only."""
    blocks = parse_current_state(body)
    assert blocks.last_segment_id == 3
    assert blocks.last_narrated == "Spoken text only."
    assert blocks.situation == ""


def test_format_current_state_omits_last_narrated_when_empty() -> None:
    formatted = format_current_state("", None, "Opening beat.")
    assert "Last narrated" not in formatted
    assert "Situation:" in formatted
    assert formatted.endswith("Opening beat.")


def test_situation_for_prompt() -> None:
    assert situation_for_prompt(STRUCTURED_CURRENT_STATE) == parse_current_state(
        STRUCTURED_CURRENT_STATE
    ).situation


def test_current_state_for_tier1_prompt() -> None:
    last_narrated, situation = current_state_for_tier1_prompt(STRUCTURED_CURRENT_STATE)
    assert "Marvinin" in last_narrated
    assert "lomakkeen" in situation


def test_last_narrated_for_replay() -> None:
    replay = last_narrated_for_replay(STRUCTURED_CURRENT_STATE)
    assert replay is not None
    assert replay[0] == 112
    assert "Marvinin" in replay[1]
    assert last_narrated_for_replay("Plain opening beat.") is None
    assert last_narrated_for_replay("") is None


def test_write_story_compact_preserves_current_state(tmp_path: Path) -> None:
    path = tmp_path / "story.md"
    content = SAMPLE_STORY.replace(
        "## current_state\n\nThe story has not begun.",
        f"## current_state\n\n{STRUCTURED_CURRENT_STATE}",
    )
    path.write_text(content, encoding="utf-8")
    write_story_compact(
        path,
        summary="Compressed summary.",
        past="- [t] #1: First event.",
    )
    state = read_story(path)
    blocks = parse_current_state(state.current_state)
    assert blocks.last_segment_id == 112
    assert "Marvinin" in blocks.last_narrated
