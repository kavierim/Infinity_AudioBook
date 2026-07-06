"""Audio producer thread — TTS synthesis."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from queue import Empty, Queue
from typing import Protocol

import numpy as np

from infinity_audiobook.models import AUDIO_QUEUE_MAXSIZE, SAMPLE_RATE, AudioChunk, Segment
from infinity_audiobook.llm_debug import PipelineActivityLogger
from infinity_audiobook.playback_config import PrefetchAccounting, buffer_below_limit
from infinity_audiobook.story_state import StoryLanguageCache, read_story

logger = logging.getLogger(__name__)


def make_segment_gap(
    gap_seconds: float,
    *,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """Return trailing silence between segments (empty when gap_seconds <= 0)."""
    if gap_seconds <= 0:
        return np.zeros(0, dtype=np.float32)
    return np.zeros(int(round(sample_rate * gap_seconds)), dtype=np.float32)


def append_segment_gap(audio: np.ndarray, gap_seconds: float) -> np.ndarray:
    gap = make_segment_gap(gap_seconds)
    if gap.size == 0:
        return audio
    return np.concatenate([audio.astype(np.float32), gap])


class Synthesizer(Protocol):
    def synthesize(self, text: str, *, language: str | None = None) -> np.ndarray: ...


def audio_producer_loop(
    text_queue: Queue[Segment],
    audio_queue: Queue[AudioChunk],
    shutdown_event: threading.Event,
    synthesizer: Synthesizer,
    *,
    story_path: Path | None = None,
    language: str = "en",
    language_cache: StoryLanguageCache | None = None,
    gap_seconds: float = 0.0,
    buffer_samples_fn: Callable[[], int] | None = None,
    max_buffer_seconds: float = 0.0,
    prefetch: PrefetchAccounting | None = None,
    activity: PipelineActivityLogger | None = None,
) -> None:
    """Synthesize segments from text_queue into audio_queue."""
    act = activity or PipelineActivityLogger(enabled=False)
    wait_reason: str | None = None

    while not shutdown_event.is_set():
        reason: str | None = None
        if audio_queue.qsize() >= AUDIO_QUEUE_MAXSIZE:
            reason = f"audio queue full ({audio_queue.qsize()}/{AUDIO_QUEUE_MAXSIZE})"
        elif buffer_samples_fn is not None and not buffer_below_limit(
            buffer_samples_fn(), max_buffer_seconds
        ):
            reason = "playback buffer full"

        if reason is not None:
            if reason != wait_reason:
                act.log("Waiting: %s", reason)
                wait_reason = reason
            shutdown_event.wait(timeout=0.1)
            continue
        wait_reason = None

        try:
            segment = text_queue.get(timeout=0.2)
        except Empty:
            continue

        if prefetch is not None:
            prefetch.on_text_dequeued(segment.estimated_samples)

        try:
            lang = language
            if language_cache is not None:
                lang = language_cache.get()
            elif story_path is not None:
                lang = read_story(story_path).language
            act.log("Synthesizing segment %d...", segment.segment_id)
            audio = synthesizer.synthesize(segment.text, language=lang)
            audio = append_segment_gap(audio, gap_seconds)
            audio_queue.put(
                AudioChunk(audio=audio, segment_id=segment.segment_id),
            )
            if prefetch is not None:
                prefetch.on_audio_queued(len(audio))
            duration_s = len(audio) / SAMPLE_RATE
            act.log(
                "Segment %d audio queued (%.1fs)",
                segment.segment_id,
                duration_s,
            )
        except Exception as exc:
            logger.error(
                "TTS failed for segment %d: %s", segment.segment_id, exc
            )
        finally:
            text_queue.task_done()


def run_audio_producer(
    text_queue: Queue[Segment],
    audio_queue: Queue[AudioChunk],
    shutdown_event: threading.Event,
    synthesizer: Synthesizer,
    *,
    story_path: Path | None = None,
    language: str = "en",
    language_cache: StoryLanguageCache | None = None,
    gap_seconds: float = 0.0,
    buffer_samples_fn: Callable[[], int] | None = None,
    max_buffer_seconds: float = 0.0,
    prefetch: PrefetchAccounting | None = None,
    activity: PipelineActivityLogger | None = None,
) -> threading.Thread:
    thread = threading.Thread(
        target=audio_producer_loop,
        args=(text_queue, audio_queue, shutdown_event, synthesizer),
        kwargs={
            "story_path": story_path,
            "language": language,
            "language_cache": language_cache,
            "gap_seconds": gap_seconds,
            "buffer_samples_fn": buffer_samples_fn,
            "max_buffer_seconds": max_buffer_seconds,
            "prefetch": prefetch,
            "activity": activity,
        },
        name="audio-producer",
        daemon=True,
    )
    thread.start()
    return thread
