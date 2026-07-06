"""Shared LLM prompt templates and JSON parsing for segment generation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

PROMPT_TEMPLATE = """Next audiobook segment in {language_name}. JSON only, no markdown:
{{"segment_text":"80-150 words","current_state":"brief Situation beat only — do not repeat Last narrated prose","future_plan":"brief"}}

Title: {title} | Genre: {genre} | Tone: {narrator_tone}{story_arc_block}

Story summary:
{summary}

Recent past:
{past}

Last narrated:
{last_narrated}

Now: {situation}
Plan: {future_plan}{references_block}
User: {user_direction}"""

SUMMARY_PROMPT_TEMPLATE = """Compress audiobook history into one paragraph (max 350 words) in {language_name}.
JSON only: {{"summary":"..."}}

Existing summary:
{existing_summary}

Events to fold in:
{events}

Keep character names and major plot beats. Omit repetition and minor detail."""

ARC_PROMPT_TEMPLATE = """Refresh the long-form story arc for an audiobook in {language_name}.
JSON only: {{"story_arc":"..."}}

Current arc:
{story_arc}

Story summary:
{summary}

Current state:
{current_state}

Future plan:
{future_plan}

Preserve major beats and ending direction unless the narrative has clearly shifted."""

STRICT_JSON_SUFFIX = (
    "\n\nRespond with ONLY valid JSON. No markdown fences, no commentary."
)


@dataclass
class SegmentResponse:
    segment_text: str
    past_append: str
    current_state: str
    future_plan: str


FALLBACK_SEGMENT = SegmentResponse(
    segment_text=(
        "The wind shifts against the lighthouse windows. "
        "For a moment, nothing moves — then a footstep echoes on the stair, "
        "too deliberate to be the sea. You hold your breath and listen, "
        "wondering whether the light above you is a warning or an invitation."
    ),
    past_append="A strange footstep echoed on the lighthouse stair.",
    current_state="The protagonist waits in silence, listening for another sound.",
    future_plan="Reveal who — or what — climbed the stairs.",
)


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract a JSON object from accumulated LLM text."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("empty LLM response")
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace:
            cleaned = brace.group(0)
    return json.loads(cleaned)


def build_prompt(
    *,
    title: str,
    genre: str,
    narrator_tone: str,
    story_arc: str = "",
    summary: str,
    past: str,
    last_narrated: str,
    situation: str,
    future_plan: str,
    references: str,
    user_direction: str,
    language: str = "en",
    language_name: str = "English",
) -> str:
    references_block = ""
    if references.strip():
        references_block = f"\nRefs: {references}"
    story_arc_block = ""
    if story_arc.strip():
        story_arc_block = f"\n\nLong-form arc:\n{story_arc}"
    narrated = last_narrated.strip()
    return PROMPT_TEMPLATE.format(
        title=title,
        genre=genre,
        narrator_tone=narrator_tone,
        story_arc_block=story_arc_block,
        summary=summary,
        past=past,
        last_narrated=narrated or "(none)",
        situation=situation.strip() or "(none)",
        future_plan=future_plan,
        references_block=references_block,
        user_direction=user_direction or "(none)",
        language_name=language_name,
    )


def build_summary_prompt(
    *,
    existing_summary: str,
    events: str,
    language_name: str = "English",
) -> str:
    from infinity_audiobook.story_state import EMPTY_SUMMARY_MARKERS

    existing = existing_summary.strip()
    if existing in EMPTY_SUMMARY_MARKERS:
        existing = "(none)"
    return SUMMARY_PROMPT_TEMPLATE.format(
        language_name=language_name,
        existing_summary=existing,
        events=events,
    )


def build_arc_prompt(
    *,
    story_arc: str,
    summary: str,
    current_state: str,
    future_plan: str,
    language_name: str = "English",
) -> str:
    return ARC_PROMPT_TEMPLATE.format(
        language_name=language_name,
        story_arc=story_arc.strip() or "(none)",
        summary=summary.strip() or "(none)",
        current_state=current_state.strip() or "(none)",
        future_plan=future_plan.strip() or "(none)",
    )
