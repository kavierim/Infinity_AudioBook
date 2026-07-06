"""Tests for Gemini LLM client — mocked SDK."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from infinity_audiobook.gemini_client import (
    GeminiClient,
    GeminiQuotaError,
    GeminiServiceError,
    resolve_gemini_api_key,
)


def _segment_json(**overrides: str) -> str:
    payload = {
        "segment_text": "The lighthouse beam swept the fog.",
        "past_append": "Fog thickened around the lighthouse.",
        "current_state": "Watching from the gallery.",
        "future_plan": "A knock at the door.",
    }
    payload.update(overrides)
    return json.dumps(payload)


def _mock_client_factory(responses: list[str | Exception]) -> tuple[MagicMock, MagicMock]:
    mock_sdk = MagicMock()
    call_count = {"n": 0}

    def generate_content(**kwargs: object) -> MagicMock:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx >= len(responses):
            raise RuntimeError("unexpected call")
        outcome = responses[idx]
        if isinstance(outcome, Exception):
            raise outcome
        response = MagicMock()
        response.text = outcome
        return response

    mock_sdk.models.generate_content.side_effect = generate_content
    return mock_sdk, call_count


def test_generate_segment_parses_json() -> None:
    mock_sdk, _ = _mock_client_factory([_segment_json()])
    client = GeminiClient(
        model="gemini-2.5-flash",
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
    assert result.past_append.startswith("Fog")
    mock_sdk.models.generate_content.assert_called_once()
    call_kwargs = mock_sdk.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-flash"
    assert call_kwargs["config"].response_mime_type == "application/json"


def test_summarize_past_returns_summary_field() -> None:
    mock_sdk, _ = _mock_client_factory(
        [json.dumps({"summary": "Hero reached the coast after many trials."})]
    )
    client = GeminiClient(
        api_key="test-key",
        client_factory=lambda _key: mock_sdk,
    )
    summary = client.summarize_past(
        existing_summary="*(no summary yet)*",
        events="- Event one\n- Event two",
        language_name="English",
    )
    assert "coast" in summary


def test_generate_segment_retries_once_on_transient_failure() -> None:
    mock_sdk, call_count = _mock_client_factory(
        [RuntimeError("503 unavailable"), _segment_json()]
    )
    client = GeminiClient(
        api_key="test-key",
        client_factory=lambda _key: mock_sdk,
    )
    result = client.generate_segment(
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
    assert result.segment_text
    assert call_count["n"] == 2


def test_generate_segment_retries_transient_errors_with_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(
        "infinity_audiobook.gemini_client.time.sleep",
        lambda seconds: sleeps.append(seconds),
    )
    internal_error = RuntimeError(
        "500 INTERNAL. {'error': {'code': 500, 'message': 'Internal error encountered.'}}"
    )
    mock_sdk, call_count = _mock_client_factory(
        [internal_error, internal_error, _segment_json()]
    )
    client = GeminiClient(
        api_key="test-key",
        client_factory=lambda _key: mock_sdk,
    )
    result = client.generate_segment(
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
    assert result.segment_text
    assert call_count["n"] == 3
    assert sleeps == [2.0, 4.0]


def test_generate_segment_raises_after_retries_exhausted() -> None:
    internal_error = RuntimeError("500 INTERNAL")
    mock_sdk, _ = _mock_client_factory(
        [internal_error, internal_error, internal_error, internal_error]
    )
    client = GeminiClient(
        api_key="test-key",
        client_factory=lambda _key: mock_sdk,
    )
    with pytest.raises(GeminiServiceError, match="failed after retries"):
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


def test_generate_segment_raises_daily_quota_without_retry() -> None:
    daily_error = RuntimeError(
        "429 RESOURCE_EXHAUSTED. GenerateRequestsPerDayPerProjectPerModel-FreeTier"
    )
    mock_sdk, call_count = _mock_client_factory([daily_error, _segment_json()])
    client = GeminiClient(
        api_key="test-key",
        client_factory=lambda _key: mock_sdk,
    )
    with pytest.raises(GeminiQuotaError) as exc_info:
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
    assert exc_info.value.daily is True
    assert call_count["n"] == 1


def test_resolve_gemini_api_key_prefers_gemini_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    assert resolve_gemini_api_key() == "gem-key"


def test_resolve_gemini_api_key_falls_back_to_google(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    assert resolve_gemini_api_key() == "google-key"


def test_resolve_gemini_api_key_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        resolve_gemini_api_key()
