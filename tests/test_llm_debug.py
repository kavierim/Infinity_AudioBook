"""Tests for LLM debug traffic logging."""

from __future__ import annotations

import json
from pathlib import Path

from infinity_audiobook.llm_debug import (
    LLMDebugLogger,
    PipelineActivityLogger,
    debug_enabled_from_env,
    parse_debug_flag,
)


def test_parse_debug_flag() -> None:
    assert parse_debug_flag("true") is True
    assert parse_debug_flag("0") is False


def test_debug_logger_writes_jsonl(tmp_path: Path) -> None:
    log_dir = tmp_path / "debug" / "llm"
    logger = LLMDebugLogger(log_dir, enabled=True)
    logger.log_exchange(
        provider="gemini",
        model="gemini-2.5-flash",
        operation="segment",
        prompt="prompt text",
        response='{"segment_text":"Hi"}',
    )

    lines = logger.log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["provider"] == "gemini"
    assert record["operation"] == "segment"
    assert record["prompt"] == "prompt text"
    assert record["seq"] == 1


def test_debug_logger_noop_when_disabled(tmp_path: Path) -> None:
    log_dir = tmp_path / "debug" / "llm"
    logger = LLMDebugLogger(log_dir, enabled=False)
    logger.log_exchange(
        provider="gemini",
        model=None,
        operation="segment",
        prompt="ignored",
    )
    assert not logger.log_path.exists()


def test_debug_enabled_from_env(monkeypatch) -> None:
    monkeypatch.setenv("AUDIOBOOK_DEBUG_LLM", "1")
    assert debug_enabled_from_env() is True


def test_pipeline_activity_logger_logs_when_enabled(caplog) -> None:
    import logging

    caplog.set_level(logging.INFO, logger="infinity_audiobook.llm_debug")
    activity = PipelineActivityLogger(enabled=True)
    activity.log("Generating segment %d...", 3)

    assert "[activity] Generating segment 3..." in caplog.text


def test_pipeline_activity_logger_noop_when_disabled(caplog) -> None:
    import logging

    caplog.set_level(logging.INFO, logger="infinity_audiobook.llm_debug")
    activity = PipelineActivityLogger(enabled=False)
    activity.log("Generating segment %d...", 3)

    assert "[activity]" not in caplog.text
