"""Gemini API error classification and retry hints."""

from __future__ import annotations

import re

MAX_GEMINI_ATTEMPTS = 4
TRANSIENT_BACKOFF_BASE_SECONDS = 2.0
TRANSIENT_RETRY_AFTER_DEFAULT = 30.0

_TRANSIENT_MARKERS = (
    "500",
    "503",
    "INTERNAL",
    "UNAVAILABLE",
    "DEADLINE_EXCEEDED",
    "SERVICE_UNAVAILABLE",
)


class GeminiQuotaError(RuntimeError):
    """Raised when Gemini returns 429 / RESOURCE_EXHAUSTED."""

    def __init__(self, message: str, *, retry_after: float, daily: bool) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.daily = daily


class GeminiServiceError(RuntimeError):
    """Raised when Gemini is still failing after in-call retries (500, 503, …)."""

    def __init__(self, message: str, *, retry_after: float) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def is_transient_gemini_error(exc: Exception) -> bool:
    """Return True for retryable server-side Gemini failures."""
    message = str(exc).upper()
    return any(marker in message for marker in _TRANSIENT_MARKERS)


def transient_backoff_seconds(attempt: int) -> float:
    """Exponential backoff delay before the next generate_content attempt."""
    return TRANSIENT_BACKOFF_BASE_SECONDS * (2**attempt)


_DAILY_QUOTA_MARKERS = (
    "PerDay",
    "free_tier_requests",
    "GenerateRequestsPerDayPerProjectPerModel",
)
_RETRY_SECONDS_RE = re.compile(r"retry in ([\d.]+)s", re.IGNORECASE)
_RETRY_DELAY_RE = re.compile(r"'retryDelay':\s*'(\d+)s'")


def _parse_retry_seconds(message: str) -> float | None:
    match = _RETRY_SECONDS_RE.search(message)
    if match:
        return float(match.group(1))
    match = _RETRY_DELAY_RE.search(message)
    if match:
        return float(match.group(1))
    return None


def classify_gemini_error(exc: Exception) -> GeminiQuotaError | None:
    """Return quota metadata when *exc* looks like a Gemini 429."""
    message = str(exc)
    if "429" not in message and "RESOURCE_EXHAUSTED" not in message:
        return None

    daily = any(marker in message for marker in _DAILY_QUOTA_MARKERS)
    if daily:
        return GeminiQuotaError(message, retry_after=300.0, daily=True)

    retry_after = _parse_retry_seconds(message)
    if retry_after is None:
        retry_after = 30.0
    return GeminiQuotaError(message, retry_after=retry_after + 1.0, daily=False)
