"""Tests for text producer fallback segments and instruction retention."""

from __future__ import annotations

import threading
import time
from queue import Queue
from unittest.mock import MagicMock

from infinity_audiobook.llm_prompts import FALLBACK_SEGMENT
from infinity_audiobook.context import Context
from infinity_audiobook.gemini_errors import GeminiServiceError
from infinity_audiobook.llm_prompts import SegmentResponse
from infinity_audiobook.story_state import parse_current_state, read_story
from infinity_audiobook.models import TEXT_QUEUE_MAXSIZE, Segment
from infinity_audiobook.text_producer import queue_replay_from_story, text_producer_loop

STORY_TEMPLATE = """# Story

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

"""


def test_text_producer_preserves_instruction_on_gemini_service_error(tmp_path) -> None:
    story = tmp_path / "story.md"
    story.write_text(STORY_TEMPLATE, encoding="utf-8")

    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    shutdown = threading.Event()
    context = Context()
    context.set_instruction("Meet a wolf")

    mock_llm = MagicMock()
    mock_llm.generate_segment.side_effect = [
        GeminiServiceError("500 INTERNAL", retry_after=0.05),
        SegmentResponse(
            segment_text="The wolf appeared on the path.",
            past_append="",
            current_state="After recovery.",
            future_plan="Continue.",
        ),
    ]

    thread = threading.Thread(
        target=text_producer_loop,
        args=(text_queue, context, story, shutdown, mock_llm),
        daemon=True,
    )
    thread.start()

    deadline = time.monotonic() + 5.0
    while text_queue.qsize() < 1 and time.monotonic() < deadline:
        time.sleep(0.05)

    shutdown.set()
    thread.join(timeout=2.0)

    assert mock_llm.generate_segment.call_count >= 2
    second_call = mock_llm.generate_segment.call_args_list[1].kwargs
    assert second_call["user_direction"] == "Meet a wolf"
    assert context.peek_instruction() == ""


def test_text_producer_fallback_uses_negative_segment_ids(tmp_path) -> None:
    story = tmp_path / "story.md"
    story.write_text(STORY_TEMPLATE, encoding="utf-8")

    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    shutdown = threading.Event()
    mock_llm = MagicMock()
    mock_llm.generate_segment.side_effect = [
        RuntimeError("transport failed"),
        RuntimeError("transport failed again"),
        SegmentResponse(
            segment_text="Finally a real segment.",
            past_append="",
            current_state="Recovered.",
            future_plan="Continue.",
        ),
    ]

    thread = threading.Thread(
        target=text_producer_loop,
        args=(text_queue, Context(), story, shutdown, mock_llm),
        daemon=True,
    )
    thread.start()

    segments: list[Segment] = []
    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        while not text_queue.empty():
            segments.append(text_queue.get())
        if any(seg.segment_id > 0 for seg in segments):
            break
        time.sleep(0.05)

    shutdown.set()
    thread.join(timeout=2.0)

    while not text_queue.empty():
        segments.append(text_queue.get())

    fallback_ids = [seg.segment_id for seg in segments if seg.segment_id < 0]
    success_ids = [seg.segment_id for seg in segments if seg.segment_id > 0]

    assert fallback_ids[:2] == [-1, -2]
    assert success_ids == [1]
    assert FALLBACK_SEGMENT.segment_text[:20] in segments[0].text


def test_text_producer_writes_structured_current_state(tmp_path) -> None:
    story = tmp_path / "story.md"
    story.write_text(STORY_TEMPLATE, encoding="utf-8")

    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    shutdown = threading.Event()
    mock_llm = MagicMock()
    mock_llm.generate_segment.return_value = SegmentResponse(
        segment_text="The wolf appeared on the path.",
        past_append="",
        current_state="Wolf on the path ahead.",
        future_plan="Approach carefully.",
    )

    thread = threading.Thread(
        target=text_producer_loop,
        args=(text_queue, Context(), story, shutdown, mock_llm),
        daemon=True,
    )
    thread.start()

    deadline = time.monotonic() + 5.0
    queued: Segment | None = None
    while time.monotonic() < deadline:
        if not text_queue.empty():
            queued = text_queue.get()
            break
        time.sleep(0.05)

    shutdown.set()
    thread.join(timeout=2.0)

    assert queued is not None
    state = read_story(story)
    blocks = parse_current_state(state.current_state)
    assert blocks.last_segment_id is not None
    assert f"#{blocks.last_segment_id}:" in state.past


def test_queue_replay_from_story(tmp_path) -> None:
    story = tmp_path / "story.md"
    story.write_text(
        STORY_TEMPLATE.replace(
            "## current_state\nBeginning",
            """## current_state

Last narrated (#7):

Previously spoken segment text.

Situation:

Current beat.""",
        ),
        encoding="utf-8",
    )
    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    assert queue_replay_from_story(story, text_queue) is True
    segment = text_queue.get_nowait()
    assert segment.segment_id == 7
    assert "Previously spoken" in segment.text

    preloaded = read_story(story)
    assert queue_replay_from_story(story, text_queue, story_state=preloaded) is True
    assert text_queue.qsize() == 1
