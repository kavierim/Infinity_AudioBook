"""Tests for three-tier Gemini client — mocked SDK."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from infinity_audiobook.gemini_tiered import TieredGeminiClient
from infinity_audiobook.llm_debug import LLMDebugLogger


def _segment_json(**overrides: str) -> str:
    payload = {
        "segment_text": "The lighthouse beam swept the fog.",
        "past_append": "Fog thickened around the lighthouse.",
        "current_state": "Watching from the gallery.",
        "future_plan": "A knock at the door.",
    }
    payload.update(overrides)
    return json.dumps(payload)


def _mock_client_factory() -> tuple[MagicMock, list[str]]:
    mock_sdk = MagicMock()
    models_used: list[str] = []

    def generate_content(**kwargs: object) -> MagicMock:
        model = str(kwargs["model"])
        models_used.append(model)
        response = MagicMock()
        if "Compress audiobook history" in str(kwargs.get("contents", "")):
            response.text = json.dumps({"summary": "Compressed history."})
        elif "Refresh the long-form story arc" in str(kwargs.get("contents", "")):
            response.text = json.dumps({"story_arc": "Act II begins at the coast."})
        else:
            response.text = _segment_json()
        return response

    mock_sdk.models.generate_content.side_effect = generate_content
    return mock_sdk, models_used


def test_tiered_routes_segment_model() -> None:
    mock_sdk, models_used = _mock_client_factory()
    client = TieredGeminiClient(
        model_segment="gemini-2.5-flash",
        model_summary="gemini-2.5-flash-lite",
        model_arc="gemini-2.5-pro",
        api_key="test-key",
        client_factory=lambda _key: mock_sdk,
    )
    result = client.generate_segment(
        title="T",
        genre="G",
        narrator_tone="Calm",
        summary="Earlier.",
        past="Past line.",
        last_narrated="",
        situation="Now.",
        future_plan="Next.",
        references="",
        user_direction="",
    )
    assert "lighthouse" in result.segment_text
    assert models_used == ["gemini-2.5-flash"]


def test_tiered_routes_summary_model() -> None:
    mock_sdk, models_used = _mock_client_factory()
    client = TieredGeminiClient(
        model_segment="gemini-2.5-flash",
        model_summary="gemini-2.5-flash-lite",
        model_arc="gemini-2.5-pro",
        api_key="test-key",
        client_factory=lambda _key: mock_sdk,
    )
    summary = client.summarize_past(
        existing_summary="*(no summary yet)*",
        events="- Event one\n- Event two",
        language_name="English",
    )
    assert "Compressed" in summary
    assert models_used == ["gemini-2.5-flash-lite"]


def test_tiered_routes_arc_model() -> None:
    mock_sdk, models_used = _mock_client_factory()
    client = TieredGeminiClient(
        model_segment="gemini-2.5-flash",
        model_summary="gemini-2.5-flash-lite",
        model_arc="gemini-2.5-pro",
        api_key="test-key",
        client_factory=lambda _key: mock_sdk,
    )
    arc = client.refresh_story_arc(
        story_arc="Act I: departure.",
        summary="Hero left home.",
        current_state="On the road.",
        future_plan="Reach the coast.",
        language_name="English",
    )
    assert "Act II" in arc
    assert models_used == ["gemini-2.5-pro"]


def test_should_refresh_arc_requires_section(tmp_path) -> None:
    client = TieredGeminiClient(
        model_segment="a",
        model_summary="b",
        model_arc="c",
        arc_refresh_every=2,
        api_key="test-key",
        client_factory=lambda _key: MagicMock(),
    )
    assert client.should_refresh_arc(has_story_arc_section=False) is False
    client._segment_count = 2
    assert client.should_refresh_arc(has_story_arc_section=False) is False
    assert client.should_refresh_arc(has_story_arc_section=True) is True


def test_should_refresh_arc_disabled_when_zero() -> None:
    client = TieredGeminiClient(
        model_segment="a",
        model_summary="b",
        model_arc="c",
        arc_refresh_every=0,
        api_key="test-key",
        client_factory=lambda _key: MagicMock(),
    )
    client._segment_count = 20
    assert client.should_refresh_arc(has_story_arc_section=True) is False


def test_debug_logger_records_tier(tmp_path) -> None:
    mock_sdk, _ = _mock_client_factory()
    log_dir = tmp_path / "debug" / "llm"
    debug_logger = LLMDebugLogger(log_dir, enabled=True)
    client = TieredGeminiClient(
        model_segment="gemini-2.5-flash",
        model_summary="gemini-2.5-flash",
        model_arc="gemini-2.5-pro",
        api_key="test-key",
        client_factory=lambda _key: mock_sdk,
        debug_logger=debug_logger,
    )
    client.generate_segment(
        title="T",
        genre="G",
        narrator_tone="N",
        summary="S",
        past="P",
        last_narrated="",
        situation="C",
        future_plan="F",
        references="",
        user_direction="",
    )
    record = json.loads(debug_logger.log_path.read_text(encoding="utf-8").strip())
    assert record["tier"] == "segment"
    assert record["model"] == "gemini-2.5-flash"
    assert record["operation"] == "segment"
