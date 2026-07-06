"""Tests for UISnapshot and activity ring buffers."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from queue import Queue

from infinity_audiobook.context import Context
from infinity_audiobook.llm_config import LLMConfig
from infinity_audiobook.story_state import situation_for_prompt
from infinity_audiobook.ui.activity import (
    ActivityLogHandler,
    ActivityRing,
    UIActivityLogger,
)
from infinity_audiobook.ui.app import InfinityAudioBookApp
from infinity_audiobook.ui.snapshot import TRANSCRIPT_RING_SIZE, UISnapshot


def _make_tui_app() -> InfinityAudioBookApp:
    return InfinityAudioBookApp(
        snapshot=UISnapshot(),
        context=Context(),
        shutdown_event=threading.Event(),
        story_path=Path("story.md"),
        text_queue=Queue(),
        audio_queue=Queue(),
        buffer_samples_fn=lambda: 0,
        llm_config=LLMConfig(
            provider="gemini",
            model_segment="m",
            model_summary="m",
            model_arc="m",
            arc_refresh_every=5,
            debug_traffic=False,
        ),
        activity_ring=ActivityRing(),
    )


def test_app_preserves_textual_context_manager() -> None:
    """Regression: story Context must not overwrite Textual App._context."""
    app = _make_tui_app()
    assert isinstance(app._instruction_context, Context)
    assert callable(app._context)


def test_transcript_seed_from_disk() -> None:
    snapshot = UISnapshot()
    snapshot.seed_transcript(42, "Persisted narration from disk.")
    entries = snapshot.transcript_snapshot()
    assert len(entries) == 1
    assert entries[0].segment_id == 42
    assert entries[0].text == "Persisted narration from disk."


def test_transcript_seed_skipped_when_ring_has_entries() -> None:
    snapshot = UISnapshot(transcript_capacity=5)
    snapshot.record_segment_queued(1, "live segment")
    snapshot.seed_transcript(99, "should not appear")
    entries = snapshot.transcript_snapshot()
    assert len(entries) == 1
    assert entries[0].segment_id == 1


def test_transcript_ring_buffer_keeps_last_n() -> None:
    snapshot = UISnapshot(transcript_capacity=5)
    for i in range(8):
        snapshot.record_segment_queued(i + 1, f"segment {i + 1}")
    entries = snapshot.transcript_snapshot()
    assert len(entries) == 5
    assert entries[0].segment_id == 4
    assert entries[-1].segment_id == 8


def test_transcript_ring_requires_minimum_capacity() -> None:
    try:
        UISnapshot(transcript_capacity=4)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_transcript_ring_thread_safe() -> None:
    snapshot = UISnapshot(transcript_capacity=TRANSCRIPT_RING_SIZE)
    errors: list[str] = []

    def writer(start: int) -> None:
        try:
            for i in range(20):
                snapshot.record_segment_queued(start + i, f"text-{start}-{i}")
        except Exception as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=writer, args=(n * 100,)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert len(snapshot.transcript_snapshot()) <= TRANSCRIPT_RING_SIZE


def test_activity_ring_drops_oldest() -> None:
    ring = ActivityRing(capacity=3)
    ring.append("a")
    ring.append("b")
    ring.append("c")
    ring.append("d")
    assert ring.snapshot() == ["b", "c", "d"]


def test_ui_activity_logger_always_fills_ring() -> None:
    ring = ActivityRing()
    activity = UIActivityLogger(ring, debug_to_logger=False)
    activity.log("Generating segment %d...", 1)
    assert ring.snapshot() == ["Generating segment 1..."]


def test_ui_activity_logger_optional_debug_logger(caplog) -> None:
    import logging

    caplog.set_level(logging.INFO, logger="infinity_audiobook.ui.activity")
    ring = ActivityRing()
    activity = UIActivityLogger(ring, debug_to_logger=True)
    activity.log("Queued %s", "ok")
    assert ring.snapshot() == ["Queued ok"]
    assert "[activity] Queued ok" in caplog.text


def test_activity_log_handler_routes_warnings() -> None:
    ring = ActivityRing()
    handler = ActivityLogHandler(ring)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="buffer low",
        args=(),
        exc_info=None,
    )
    handler.emit(record)
    assert ring.snapshot() == ["WARNING: buffer low"]


def test_situation_for_prompt_extracts_beat_only() -> None:
    body = """Last narrated (#5):

Full narrated prose here.

Situation:

Brief situation beat."""
    assert situation_for_prompt(body) == "Brief situation beat."
    assert situation_for_prompt("Plain opening beat.") == "Plain opening beat."
    ctx = Context()
    ctx.set_instruction("go north")
    ctx.set_instruction("go south")
    assert ctx.peek_instruction() == "go south"
    consumed = ctx.get_and_clear_instruction()
    assert consumed == "go south"
    assert ctx.peek_instruction() == ""
