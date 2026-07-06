"""Periodic compaction of story past into rolling summary."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol, runtime_checkable

from infinity_audiobook.models import PAST_ARCHIVE_THRESHOLD, PAST_KEEP_AFTER_ARCHIVE
from infinity_audiobook.story_state import (
    join_past_lines,
    past_line_count,
    read_story,
    split_past_for_archive,
    write_story_compact,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class StorySummarizer(Protocol):
    def summarize_past(
        self,
        *,
        existing_summary: str,
        events: str,
        language_name: str = "English",
    ) -> str: ...


def maybe_compact_story(
    story_path: Path,
    summarizer: StorySummarizer,
    *,
    language_name: str,
) -> bool:
    """Fold older past lines into summary when past exceeds threshold. Returns True if compacted."""
    state = read_story(story_path)
    if past_line_count(state.past) <= PAST_ARCHIVE_THRESHOLD:
        return False

    to_archive, to_keep = split_past_for_archive(state.past, PAST_KEEP_AFTER_ARCHIVE)
    if not to_archive:
        return False

    events = "\n".join(to_archive)
    try:
        new_summary = summarizer.summarize_past(
            existing_summary=state.summary,
            events=events,
            language_name=language_name,
        )
    except Exception as exc:
        logger.error("Story compaction failed; keeping full past: %s", exc)
        return False

    write_story_compact(
        story_path,
        summary=new_summary,
        past=join_past_lines(to_keep),
    )
    logger.info(
        "Compacted %d past lines into summary (%d lines kept)",
        len(to_archive),
        len(to_keep),
    )
    return True
