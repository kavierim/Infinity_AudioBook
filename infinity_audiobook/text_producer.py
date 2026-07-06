"""Text producer thread — LLM segment generation and story.md updates."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from queue import Queue
from typing import Protocol

from infinity_audiobook.llm_prompts import FALLBACK_SEGMENT, SegmentResponse
from infinity_audiobook.gemini_errors import GeminiQuotaError, GeminiServiceError
from infinity_audiobook.context import Context
from infinity_audiobook.llm_debug import PipelineActivityLogger
from infinity_audiobook.models import (
    PAST_ARCHIVE_THRESHOLD,
    PROMPT_PAST_MAX_LINES,
    SUMMARY_MAX_WORDS,
    TEXT_QUEUE_MAXSIZE,
    Segment,
)
from infinity_audiobook.playback_config import (
    PrefetchAccounting,
    buffer_below_limit,
    estimate_segment_audio_samples,
)
from infinity_audiobook.reference_sources import expand_references_for_prompt
from infinity_audiobook.story_arc import (
    StoryArcRefresher,
    arc_refresh_due,
    maybe_refresh_story_arc,
)
from infinity_audiobook.story_compact import StorySummarizer, maybe_compact_story
from infinity_audiobook.ui.snapshot import UISnapshot
from infinity_audiobook.story_state import (
    StoryState,
    current_state_for_tier1_prompt,
    derive_past_append,
    format_current_state,
    last_narrated_for_replay,
    next_segment_id,
    past_for_prompt,
    past_line_count,
    read_story,
    situation_for_prompt,
    story_arc_for_prompt,
    story_arc_section_present,
    story_language_name,
    summary_for_prompt,
    truncate_segment_text,
    write_story_updates,
)

logger = logging.getLogger(__name__)


class SegmentGenerator(Protocol):
    def generate_segment(
        self,
        *,
        title: str,
        genre: str,
        narrator_tone: str,
        summary: str,
        past: str,
        last_narrated: str,
        situation: str,
        future_plan: str,
        references: str,
        user_direction: str,
        language: str = "en",
        language_name: str = "English",
        story_arc: str = "",
    ) -> SegmentResponse: ...


def queue_replay_from_story(
    story_path: Path,
    text_queue: Queue[Segment],
    *,
    story_state: StoryState | None = None,
    gap_seconds: float = 0.0,
    prefetch: PrefetchAccounting | None = None,
    activity: PipelineActivityLogger | None = None,
) -> bool:
    """Queue the last narrated segment from disk for immediate TTS (startup resume)."""
    current_state = (
        story_state.current_state
        if story_state is not None
        else read_story(story_path).current_state
    )
    replay = last_narrated_for_replay(current_state)
    if replay is None:
        return False
    segment_id, text = replay
    estimated = estimate_segment_audio_samples(text, gap_seconds=gap_seconds)
    text_queue.put(
        Segment(text=text, segment_id=segment_id, estimated_samples=estimated),
    )
    if prefetch is not None:
        prefetch.on_text_queued(estimated)
    act = activity or PipelineActivityLogger(enabled=False)
    act.log("Replay queued: segment %d (%d chars)", segment_id, len(text))
    logger.info(
        "Queued replay of segment #%d from story.md (%d chars)",
        segment_id,
        len(text),
    )
    return True


def text_producer_loop(
    text_queue: Queue[Segment],
    context: Context,
    story_path: Path,
    shutdown_event: threading.Event,
    llm_client: SegmentGenerator,
    *,
    project_root: Path | None = None,
    arc_refresh_every: int = 0,
    buffer_samples_fn: Callable[[], int] | None = None,
    max_buffer_seconds: float = 0.0,
    gap_seconds: float = 0.0,
    prefetch: PrefetchAccounting | None = None,
    activity: PipelineActivityLogger | None = None,
    snapshot: UISnapshot | None = None,
) -> None:
    """Fill text_queue when it has fewer than 2 items."""
    root = project_root or story_path.parent
    segments_ok = 0
    fallback_seq = 0
    act = activity or PipelineActivityLogger(enabled=False)
    wait_reason: str | None = None

    while not shutdown_event.is_set():
        reason: str | None = None
        if text_queue.qsize() >= TEXT_QUEUE_MAXSIZE:
            reason = f"text queue full ({text_queue.qsize()}/{TEXT_QUEUE_MAXSIZE})"
        elif buffer_samples_fn is not None and not buffer_below_limit(
            buffer_samples_fn(), max_buffer_seconds
        ):
            reason = "playback buffer full"

        if reason is not None:
            if reason != wait_reason:
                act.log("Waiting: %s", reason)
                wait_reason = reason
            shutdown_event.wait(timeout=0.2)
            continue
        wait_reason = None

        try:
            state = read_story(story_path)
            user_direction = context.peek_instruction()
            language_name = story_language_name(state.language)
            references_prompt = expand_references_for_prompt(
                state.references,
                root,
            )

            counter_segment_id = next_segment_id(state.past)
            generation_ok = False
            last_narrated, situation = current_state_for_tier1_prompt(state.current_state)
            act.log("Generating segment %d...", counter_segment_id)
            try:
                response = llm_client.generate_segment(
                    title=state.title,
                    genre=state.genre,
                    narrator_tone=state.narrator_tone,
                    summary=summary_for_prompt(state.summary, max_words=SUMMARY_MAX_WORDS),
                    past=past_for_prompt(state.past, max_lines=PROMPT_PAST_MAX_LINES),
                    last_narrated=last_narrated,
                    situation=situation,
                    future_plan=state.future_plan,
                    references=references_prompt,
                    user_direction=user_direction,
                    language=state.language,
                    language_name=language_name,
                    story_arc=story_arc_for_prompt(state.story_arc),
                )
                generation_ok = True
            except GeminiQuotaError as exc:
                kind = "daily quota" if exc.daily else "rate limit"
                logger.warning(
                    "Gemini %s exhausted — waiting %.0fs (no fallback audio)",
                    kind,
                    exc.retry_after,
                )
                shutdown_event.wait(timeout=exc.retry_after)
                continue
            except GeminiServiceError as exc:
                logger.warning(
                    "Gemini service unavailable — waiting %.0fs before retry",
                    exc.retry_after,
                )
                shutdown_event.wait(timeout=exc.retry_after)
                continue
            except Exception as exc:
                logger.error("LLM segment generation failed: %s", exc)
                response = FALLBACK_SEGMENT

            raw_segment_text = response.segment_text
            segment_text = truncate_segment_text(raw_segment_text)
            raw_words = len(raw_segment_text.split())
            spoken_words = len(segment_text.split())
            if spoken_words < raw_words:
                logger.warning(
                    "Segment %d truncated from %d to %d words — "
                    "narration may skip content described in story state",
                    counter_segment_id,
                    raw_words,
                    spoken_words,
                )
            past_append = derive_past_append(segment_text)

            if generation_ok:
                context.get_and_clear_instruction()
                segments_ok += 1
                try:
                    formatted_state = format_current_state(
                        segment_text,
                        counter_segment_id,
                        response.current_state,
                    )
                    write_story_updates(
                        story_path,
                        state,
                        past_append=past_append,
                        segment_id=counter_segment_id,
                        current_state=formatted_state,
                        future_plan=response.future_plan,
                    )
                except Exception as exc:
                    logger.error("Failed to write story.md: %s", exc)

                if isinstance(llm_client, StorySummarizer):
                    if past_line_count(state.past) > PAST_ARCHIVE_THRESHOLD:
                        act.log("Compacting past into summary...")
                    try:
                        maybe_compact_story(
                            story_path,
                            llm_client,
                            language_name=language_name,
                        )
                    except Exception as exc:
                        logger.error("Story compaction error: %s", exc)

                if isinstance(llm_client, StoryArcRefresher) and arc_refresh_every > 0:
                    story_content = story_path.read_text(encoding="utf-8")
                    if arc_refresh_due(
                        segment_count=segments_ok,
                        arc_refresh_every=arc_refresh_every,
                        has_story_arc_section=story_arc_section_present(story_content),
                    ):
                        act.log("Refreshing story arc...")
                    try:
                        maybe_refresh_story_arc(
                            story_path,
                            llm_client,
                            language_name=language_name,
                            segment_count=segments_ok,
                            arc_refresh_every=arc_refresh_every,
                        )
                    except Exception as exc:
                        logger.error("Story arc refresh error: %s", exc)
            else:
                fallback_seq += 1
                counter_segment_id = -fallback_seq
                logger.warning(
                    "Skipping story.md update for fallback segment %d",
                    counter_segment_id,
                )

            estimated = estimate_segment_audio_samples(
                segment_text,
                gap_seconds=gap_seconds,
            )
            text_queue.put(
                Segment(
                    text=segment_text,
                    segment_id=counter_segment_id,
                    estimated_samples=estimated,
                ),
            )
            if prefetch is not None:
                prefetch.on_text_queued(estimated)
            if snapshot is not None:
                snapshot.record_segment_queued(counter_segment_id, segment_text)
            act.log(
                "Segment %d queued (%d chars)",
                counter_segment_id,
                len(segment_text),
            )
        except Exception as exc:
            logger.error("Text producer error: %s", exc)
            shutdown_event.wait(timeout=1.0)


def run_text_producer(
    text_queue: Queue[Segment],
    context: Context,
    story_path: Path,
    shutdown_event: threading.Event,
    llm_client: SegmentGenerator,
    *,
    project_root: Path | None = None,
    arc_refresh_every: int = 0,
    buffer_samples_fn: Callable[[], int] | None = None,
    max_buffer_seconds: float = 0.0,
    gap_seconds: float = 0.0,
    prefetch: PrefetchAccounting | None = None,
    activity: PipelineActivityLogger | None = None,
    snapshot: UISnapshot | None = None,
) -> threading.Thread:
    thread = threading.Thread(
        target=text_producer_loop,
        args=(text_queue, context, story_path, shutdown_event, llm_client),
        kwargs={
            "project_root": project_root,
            "arc_refresh_every": arc_refresh_every,
            "buffer_samples_fn": buffer_samples_fn,
            "max_buffer_seconds": max_buffer_seconds,
            "gap_seconds": gap_seconds,
            "prefetch": prefetch,
            "activity": activity,
            "snapshot": snapshot,
        },
        name="text-producer",
        daemon=True,
    )
    thread.start()
    return thread
