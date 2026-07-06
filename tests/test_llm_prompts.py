"""Tests for shared LLM prompt helpers."""

from __future__ import annotations

from infinity_audiobook.llm_prompts import (
    build_arc_prompt,
    build_prompt,
    build_summary_prompt,
    extract_json_object,
)


def test_extract_json_from_markdown_fence() -> None:
    text = 'Here is the result:\n```json\n{"segment_text":"Hi","past_append":"a","current_state":"b","future_plan":"c"}\n```'
    data = extract_json_object(text)
    assert data["segment_text"] == "Hi"


def test_extract_json_embedded() -> None:
    text = 'Some preamble {"segment_text":"Hi","past_append":"a","current_state":"b","future_plan":"c"} trailing'
    data = extract_json_object(text)
    assert data["past_append"] == "a"


def test_build_prompt_includes_sections() -> None:
    prompt = build_prompt(
        title="T",
        genre="G",
        narrator_tone="N",
        summary="Earlier events.",
        past="P",
        last_narrated="spoken prose",
        situation="C",
        future_plan="F",
        references="R",
        user_direction="Go left",
        language="fi",
        language_name="Finnish",
    )
    assert "Title: T" in prompt
    assert "User: Go left" in prompt
    assert "Story summary:" in prompt
    assert "Earlier events." in prompt
    assert "Next audiobook segment in Finnish" in prompt
    assert "segment_text" in prompt
    assert "Last narrated:" in prompt
    assert "spoken prose" in prompt
    assert "do not repeat Last narrated" in prompt


def test_build_prompt_includes_story_arc() -> None:
    prompt = build_prompt(
        title="T",
        genre="G",
        narrator_tone="N",
        story_arc="Act I: leave home. Act III: return changed.",
        summary="Earlier events.",
        past="P",
        last_narrated="spoken prose",
        situation="C",
        future_plan="F",
        references="",
        user_direction="",
        language_name="English",
    )
    assert "Long-form arc:" in prompt
    assert "Act I: leave home" in prompt


def test_build_arc_prompt_includes_sections() -> None:
    prompt = build_arc_prompt(
        story_arc="Act I",
        summary="So far",
        current_state="Now",
        future_plan="Next",
        language_name="Finnish",
    )
    assert "Refresh the long-form story arc" in prompt
    assert "Finnish" in prompt
    assert "Act I" in prompt
    assert '"story_arc"' in prompt


def test_build_prompt_omits_last_narrated_when_empty() -> None:
    prompt = build_prompt(
        title="T",
        genre="G",
        narrator_tone="N",
        summary="S",
        past="P",
        last_narrated="",
        situation="Opening.",
        future_plan="F",
        references="",
        user_direction="",
        language_name="English",
    )
    assert "Last narrated:\n(none)" in prompt
    assert "Now: Opening." in prompt


def test_build_summary_prompt_replaces_empty_marker() -> None:
    prompt = build_summary_prompt(
        existing_summary="*(no summary yet)*",
        events="Event one\nEvent two",
        language_name="English",
    )
    assert "(none)" in prompt
    assert "Event one" in prompt
    assert "Compress audiobook history" in prompt
