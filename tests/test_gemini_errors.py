"""Tests for Gemini quota error handling."""

from __future__ import annotations

import pytest

from infinity_audiobook.gemini_errors import (
    GeminiQuotaError,
    GeminiServiceError,
    classify_gemini_error,
    is_transient_gemini_error,
    transient_backoff_seconds,
)

_DAILY_429 = (
    "429 RESOURCE_EXHAUSTED. {'error': {'quotaId': "
    "'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}}"
)
_RATE_429 = (
    "429 RESOURCE_EXHAUSTED. Please retry in 12.5s. "
    "'retryDelay': '12s'"
)


def test_classify_daily_quota() -> None:
    quota = classify_gemini_error(RuntimeError(_DAILY_429))
    assert quota is not None
    assert quota.daily is True
    assert quota.retry_after == 300.0


def test_classify_rate_limit_retry_delay() -> None:
    quota = classify_gemini_error(RuntimeError(_RATE_429))
    assert quota is not None
    assert quota.daily is False
    assert quota.retry_after == pytest.approx(13.5)


def test_non_quota_returns_none() -> None:
    assert classify_gemini_error(RuntimeError("503 unavailable")) is None


def test_classify_internal_server_error_as_transient() -> None:
    error = RuntimeError(
        "500 INTERNAL. {'error': {'code': 500, 'message': 'Internal error encountered.'}}"
    )
    assert is_transient_gemini_error(error) is True
    assert classify_gemini_error(error) is None


def test_transient_backoff_grows_exponentially() -> None:
    assert transient_backoff_seconds(0) == 2.0
    assert transient_backoff_seconds(2) == 8.0


def test_gemini_service_error_fields() -> None:
    err = GeminiServiceError("down", retry_after=30.0)
    assert err.retry_after == 30.0


def test_gemini_quota_error_fields() -> None:
    err = GeminiQuotaError("quota", retry_after=60.0, daily=True)
    assert err.retry_after == 60.0
    assert err.daily is True
