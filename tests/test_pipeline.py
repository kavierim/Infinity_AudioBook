"""Tests for pipeline skeleton and queue backpressure."""

from __future__ import annotations

import threading
import time
from queue import Queue

import numpy as np
import pytest

from infinity_audiobook.llm_prompts import SegmentResponse
from infinity_audiobook.audio_producer import append_segment_gap, audio_producer_loop, make_segment_gap
from infinity_audiobook.context import Context
from infinity_audiobook.models import AUDIO_QUEUE_MAXSIZE, SAMPLE_RATE, TEXT_QUEUE_MAXSIZE, AudioChunk, Segment
from infinity_audiobook.llm_debug import PipelineActivityLogger
from infinity_audiobook.playback_config import (
    PrefetchAccounting,
    estimate_segment_audio_samples,
    max_buffer_samples,
)
from infinity_audiobook.text_producer import text_producer_loop


class MockLLM:
    def __init__(self, responses: list[SegmentResponse] | None = None) -> None:
        self._responses = list(responses or [])
        self._index = 0

    def generate_segment(self, **kwargs: object) -> SegmentResponse:
        if self._index < len(self._responses):
            resp = self._responses[self._index]
            self._index += 1
            return resp
        return SegmentResponse(
            segment_text="Fallback narration continues the story.",
            past_append="Something happened.",
            current_state="The story moves forward.",
            future_plan="More to come.",
        )


class MockTTS:
    def synthesize(self, text: str, *, language: str | None = None) -> np.ndarray:
        duration = min(len(text.split()) * 100, 4800)
        return np.zeros(max(duration, 2400), dtype=np.float32)


class FixedLengthTTS:
    def synthesize(self, text: str, *, language: str | None = None) -> np.ndarray:
        return np.ones(100, dtype=np.float32)


def test_make_segment_gap() -> None:
    gap = make_segment_gap(0.5, sample_rate=SAMPLE_RATE)
    assert gap.dtype == np.float32
    assert len(gap) == 12_000
    assert np.all(gap == 0)
    assert make_segment_gap(0).size == 0


def test_append_segment_gap() -> None:
    audio = np.ones(50, dtype=np.float32)
    combined = append_segment_gap(audio, 0.1)
    assert len(combined) == 50 + int(round(SAMPLE_RATE * 0.1))
    assert np.all(combined[:50] == 1)
    assert np.all(combined[50:] == 0)


def test_queue_maxsize_constants() -> None:
    assert TEXT_QUEUE_MAXSIZE == 2
    assert AUDIO_QUEUE_MAXSIZE == 2


def test_context_instruction_replace() -> None:
    ctx = Context()
    ctx.set_instruction("first")
    ctx.set_instruction("second")
    assert ctx.get_and_clear_instruction() == "second"
    assert ctx.get_and_clear_instruction() == ""


def test_text_producer_fills_queue(tmp_path) -> None:
    story = tmp_path / "story.md"
    story.write_text(
        """# Story

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

## summary

*(no summary yet)*

## past
*(no events yet)*

## current_state
Beginning

## future_plan
Continue

## references

""",
        encoding="utf-8",
    )

    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    shutdown = threading.Event()
    mock_llm = MockLLM(
        [
            SegmentResponse("First segment text here.", "a", "s1", "f1"),
            SegmentResponse("Second segment text here.", "b", "s2", "f2"),
        ]
    )

    thread = threading.Thread(
        target=text_producer_loop,
        args=(text_queue, Context(), story, shutdown, mock_llm),
        daemon=True,
    )
    thread.start()

    deadline = time.monotonic() + 5.0
    while text_queue.qsize() < 2 and time.monotonic() < deadline:
        time.sleep(0.05)

    shutdown.set()
    thread.join(timeout=2.0)

    assert text_queue.qsize() == 2
    seg = text_queue.get()
    assert seg.segment_id == 1
    assert "First segment" in seg.text


def test_text_producer_waits_when_playback_buffer_full(tmp_path) -> None:
    story = tmp_path / "story.md"
    story.write_text(
        """# Story

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

## summary

*(no summary yet)*

## past
*(no events yet)*

## current_state
Beginning

## future_plan
Continue

## references

""",
        encoding="utf-8",
    )

    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    shutdown = threading.Event()
    mock_llm = MockLLM(
        [SegmentResponse("First segment.", "a", "s1", "f1")]
    )
    buffer_samples = [max_buffer_samples(60.0)]

    thread = threading.Thread(
        target=text_producer_loop,
        args=(text_queue, Context(), story, shutdown, mock_llm),
        kwargs={
            "buffer_samples_fn": lambda: buffer_samples[0],
            "max_buffer_seconds": 60.0,
        },
        daemon=True,
    )
    thread.start()

    time.sleep(0.5)
    assert mock_llm._index == 0

    buffer_samples[0] = 0
    deadline = time.monotonic() + 3.0
    while mock_llm._index < 1 and time.monotonic() < deadline:
        time.sleep(0.05)

    shutdown.set()
    thread.join(timeout=2.0)

    assert mock_llm._index == 1


def test_text_producer_waits_when_prefetch_in_queues(tmp_path) -> None:
    """Backpressure includes estimated samples in text_queue, not only the buffer."""
    story = tmp_path / "story.md"
    story.write_text(
        """# Story

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

## summary

*(no summary yet)*

## past
*(no events yet)*

## current_state
Beginning

## future_plan
Continue

## references

""",
        encoding="utf-8",
    )

    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    shutdown = threading.Event()
    mock_llm = MockLLM(
        [SegmentResponse("First segment.", "a", "s1", "f1")]
    )
    buffer_samples = [0]
    accounting = PrefetchAccounting(lambda: buffer_samples[0])
    queued_est = estimate_segment_audio_samples(" ".join(["word"] * 30))
    accounting.on_text_queued(queued_est)
    buffer_samples[0] = max_buffer_samples(1.0) - 1

    thread = threading.Thread(
        target=text_producer_loop,
        args=(text_queue, Context(), story, shutdown, mock_llm),
        kwargs={
            "buffer_samples_fn": accounting.total_samples,
            "max_buffer_seconds": 1.0,
            "prefetch": accounting,
        },
        daemon=True,
    )
    thread.start()

    time.sleep(0.5)
    assert mock_llm._index == 0

    accounting.on_text_dequeued(queued_est)
    buffer_samples[0] = 0

    deadline = time.monotonic() + 3.0
    while mock_llm._index < 1 and time.monotonic() < deadline:
        time.sleep(0.05)

    shutdown.set()
    thread.join(timeout=2.0)

    assert mock_llm._index == 1


def test_audio_producer_pipeline(tmp_path) -> None:
    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    audio_queue: Queue[AudioChunk] = Queue(maxsize=AUDIO_QUEUE_MAXSIZE)
    shutdown = threading.Event()

    text_queue.put(Segment(text="Hello world test.", segment_id=1))

    thread = threading.Thread(
        target=audio_producer_loop,
        args=(text_queue, audio_queue, shutdown, MockTTS()),
        daemon=True,
    )
    thread.start()

    deadline = time.monotonic() + 3.0
    while audio_queue.empty() and time.monotonic() < deadline:
        time.sleep(0.05)

    shutdown.set()
    thread.join(timeout=2.0)

    chunk = audio_queue.get(timeout=1.0)
    assert chunk.segment_id == 1
    assert chunk.audio.dtype == np.float32
    assert len(chunk.audio) > 0


def test_audio_producer_appends_segment_gap() -> None:
    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    audio_queue: Queue[AudioChunk] = Queue(maxsize=AUDIO_QUEUE_MAXSIZE)
    shutdown = threading.Event()

    text_queue.put(Segment(text="Short.", segment_id=1))

    thread = threading.Thread(
        target=audio_producer_loop,
        args=(text_queue, audio_queue, shutdown, FixedLengthTTS()),
        kwargs={"gap_seconds": 0.5},
        daemon=True,
    )
    thread.start()

    deadline = time.monotonic() + 3.0
    while audio_queue.empty() and time.monotonic() < deadline:
        time.sleep(0.05)

    shutdown.set()
    thread.join(timeout=2.0)

    chunk = audio_queue.get(timeout=1.0)
    assert len(chunk.audio) == 100 + 12_000
    assert np.all(chunk.audio[:100] == 1)
    assert np.all(chunk.audio[100:] == 0)


def test_audio_producer_skips_gap_when_zero() -> None:
    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    audio_queue: Queue[AudioChunk] = Queue(maxsize=AUDIO_QUEUE_MAXSIZE)
    shutdown = threading.Event()

    text_queue.put(Segment(text="Short.", segment_id=1))

    thread = threading.Thread(
        target=audio_producer_loop,
        args=(text_queue, audio_queue, shutdown, FixedLengthTTS()),
        kwargs={"gap_seconds": 0.0},
        daemon=True,
    )
    thread.start()

    deadline = time.monotonic() + 3.0
    while audio_queue.empty() and time.monotonic() < deadline:
        time.sleep(0.05)

    shutdown.set()
    thread.join(timeout=2.0)

    chunk = audio_queue.get(timeout=1.0)
    assert len(chunk.audio) == 100


def test_text_producer_logs_activity_when_debug_enabled(tmp_path, caplog) -> None:
    import logging

    caplog.set_level(logging.INFO, logger="infinity_audiobook.llm_debug")

    story = tmp_path / "story.md"
    story.write_text(
        """# Story

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

## summary

*(no summary yet)*

## past
*(no events yet)*

## current_state
Beginning

## future_plan
Continue

## references

""",
        encoding="utf-8",
    )

    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    shutdown = threading.Event()
    mock_llm = MockLLM(
        [SegmentResponse("First segment text here.", "a", "s1", "f1")]
    )
    activity = PipelineActivityLogger(enabled=True)

    thread = threading.Thread(
        target=text_producer_loop,
        args=(text_queue, Context(), story, shutdown, mock_llm),
        kwargs={"activity": activity},
        daemon=True,
    )
    thread.start()

    deadline = time.monotonic() + 5.0
    while text_queue.qsize() < 1 and time.monotonic() < deadline:
        time.sleep(0.05)

    shutdown.set()
    thread.join(timeout=2.0)

    assert "[activity] Generating segment 1..." in caplog.text
    assert "[activity] Segment 1 queued" in caplog.text


def test_audio_producer_logs_activity_when_debug_enabled(caplog) -> None:
    import logging

    caplog.set_level(logging.INFO, logger="infinity_audiobook.llm_debug")

    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    audio_queue: Queue[AudioChunk] = Queue(maxsize=AUDIO_QUEUE_MAXSIZE)
    shutdown = threading.Event()
    activity = PipelineActivityLogger(enabled=True)

    text_queue.put(Segment(text="Hello world test.", segment_id=1))

    thread = threading.Thread(
        target=audio_producer_loop,
        args=(text_queue, audio_queue, shutdown, FixedLengthTTS()),
        kwargs={"activity": activity},
        daemon=True,
    )
    thread.start()

    deadline = time.monotonic() + 3.0
    while audio_queue.empty() and time.monotonic() < deadline:
        time.sleep(0.05)

    shutdown.set()
    thread.join(timeout=2.0)

    assert "[activity] Synthesizing segment 1..." in caplog.text
    assert "[activity] Segment 1 audio queued" in caplog.text
