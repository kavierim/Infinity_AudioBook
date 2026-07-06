"""Periodic refresh of long-form story arc (tier 3)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol, runtime_checkable

from infinity_audiobook.story_state import (
    read_story,
    situation_for_prompt,
    story_arc_section_present,
    summary_for_prompt,
    write_story_arc,
)
from infinity_audiobook.models import SUMMARY_MAX_WORDS

logger = logging.getLogger(__name__)


@runtime_checkable
class StoryArcRefresher(Protocol):
    def refresh_story_arc(
        self,
        *,
        story_arc: str,
        summary: str,
        current_state: str,
        future_plan: str,
        language_name: str = "English",
    ) -> str: ...


def arc_refresh_due(
    *,
    segment_count: int,
    arc_refresh_every: int,
    has_story_arc_section: bool,
) -> bool:
    """True when a tier-3 arc refresh should run after a successful segment."""
    if not has_story_arc_section or arc_refresh_every <= 0:
        return False
    return segment_count > 0 and segment_count % arc_refresh_every == 0


def maybe_refresh_story_arc(
    story_path: Path,
    refresher: StoryArcRefresher,
    *,
    language_name: str,
    segment_count: int,
    arc_refresh_every: int,
) -> bool:
    """Refresh story_arc when due. Returns True if the section was updated."""
    content = story_path.read_text(encoding="utf-8")
    if not story_arc_section_present(content):
        return False
    if not arc_refresh_due(
        segment_count=segment_count,
        arc_refresh_every=arc_refresh_every,
        has_story_arc_section=True,
    ):
        return False

    state = read_story(story_path)
    try:
        new_arc = refresher.refresh_story_arc(
            story_arc=state.story_arc,
            summary=summary_for_prompt(state.summary, max_words=SUMMARY_MAX_WORDS),
            current_state=situation_for_prompt(state.current_state),
            future_plan=state.future_plan,
            language_name=language_name,
        )
    except Exception as exc:
        logger.error("Story arc refresh failed; keeping existing arc: %s", exc)
        return False

    write_story_arc(story_path, new_arc)
    logger.info("Refreshed story_arc after segment %d", segment_count)
    return True
