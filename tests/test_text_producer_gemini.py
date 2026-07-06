"""Tests for text producer Gemini error handling."""

from __future__ import annotations

import threading
import time
from queue import Queue
from unittest.mock import MagicMock

from infinity_audiobook.context import Context
from infinity_audiobook.gemini_errors import GeminiServiceError
from infinity_audiobook.llm_prompts import SegmentResponse
from infinity_audiobook.models import TEXT_QUEUE_MAXSIZE, Segment
from infinity_audiobook.text_producer import text_producer_loop


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


def test_text_producer_waits_and_retries_on_gemini_service_error(tmp_path) -> None:
    story = tmp_path / "story.md"
    story.write_text(STORY_TEMPLATE, encoding="utf-8")

    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    shutdown = threading.Event()
    mock_llm = MagicMock()
    mock_llm.generate_segment.side_effect = [
        GeminiServiceError("500 INTERNAL", retry_after=0.05),
        SegmentResponse(
            segment_text="Recovered segment text.",
            past_append="",
            current_state="After recovery.",
            future_plan="Continue.",
        ),
    ]

    thread = threading.Thread(
        target=text_producer_loop,
        args=(text_queue, Context(), story, shutdown, mock_llm),
        daemon=True,
    )
    thread.start()

    deadline = time.monotonic() + 5.0
    while text_queue.qsize() < 1 and time.monotonic() < deadline:
        time.sleep(0.05)

    shutdown.set()
    thread.join(timeout=2.0)

    assert mock_llm.generate_segment.call_count >= 2
    seg = text_queue.get()
    assert "Recovered segment" in seg.text
