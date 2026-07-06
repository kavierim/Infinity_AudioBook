"""Google AI Studio (Gemini) client for segment generation."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Callable

from google import genai
from google.genai import types

from infinity_audiobook.gemini_errors import (
    MAX_GEMINI_ATTEMPTS,
    GeminiQuotaError,
    GeminiServiceError,
    TRANSIENT_RETRY_AFTER_DEFAULT,
    classify_gemini_error,
    is_transient_gemini_error,
    transient_backoff_seconds,
)
from infinity_audiobook.llm_debug import LLMDebugLogger
from infinity_audiobook.llm_prompts import (
    STRICT_JSON_SUFFIX,
    SegmentResponse,
    build_arc_prompt,
    build_prompt,
    build_summary_prompt,
    extract_json_object,
)

logger = logging.getLogger(__name__)


def resolve_gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY or GOOGLE_API_KEY must be set for provider=gemini "
            "(environment variable or .env file)"
        )
    return key


class GeminiClient:
    """Stateless Gemini generateContent client for audiobook segments."""

    def __init__(
        self,
        *,
        model: str = "gemini-2.5-flash",
        api_key: str | None = None,
        client_factory: Callable[[str], Any] | None = None,
        debug_logger: LLMDebugLogger | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key if api_key is not None else resolve_gemini_api_key()
        self._client_factory = client_factory or (lambda key: genai.Client(api_key=key))
        self._client: Any | None = None
        self._debug_logger = debug_logger

    @property
    def model(self) -> str:
        return self._model

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = self._client_factory(self._api_key)
        return self._client

    def generate_json(
        self,
        prompt_text: str,
        *,
        operation: str,
        model: str | None = None,
        tier: str | None = None,
    ) -> str:
        """Run generateContent and return raw JSON text."""
        return self._generate(
            prompt_text,
            operation=operation,
            model=model,
            tier=tier,
        )

    def _generate(
        self,
        prompt_text: str,
        *,
        operation: str,
        model: str | None = None,
        tier: str | None = None,
    ) -> str:
        use_model = model or self._model
        last_error: Exception | None = None
        for attempt in range(MAX_GEMINI_ATTEMPTS):
            try:
                response = self._get_client().models.generate_content(
                    model=use_model,
                    contents=prompt_text,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
                text = response.text
                if not text or not text.strip():
                    raise ValueError("empty LLM response")
                if self._debug_logger is not None:
                    self._debug_logger.log_exchange(
                        provider="gemini",
                        model=use_model,
                        operation=operation,
                        tier=tier,
                        prompt=prompt_text,
                        response=text,
                    )
                return text
            except Exception as exc:
                quota = classify_gemini_error(exc)
                if quota is not None and quota.daily:
                    if self._debug_logger is not None:
                        self._debug_logger.log_exchange(
                            provider="gemini",
                            model=use_model,
                            operation=operation,
                            tier=tier,
                            prompt=prompt_text,
                            response="",
                            error=str(exc),
                        )
                    raise GeminiQuotaError(
                        str(exc), retry_after=quota.retry_after, daily=True
                    ) from exc
                last_error = exc
                if (
                    quota is not None
                    and not quota.daily
                    and attempt < MAX_GEMINI_ATTEMPTS - 1
                ):
                    logger.info(
                        "Gemini rate limited — retrying in %.0fs",
                        quota.retry_after,
                    )
                    time.sleep(quota.retry_after)
                    continue
                if (
                    is_transient_gemini_error(exc)
                    and attempt < MAX_GEMINI_ATTEMPTS - 1
                ):
                    delay = transient_backoff_seconds(attempt)
                    logger.info(
                        "Gemini transient error — retrying in %.0fs",
                        delay,
                    )
                    time.sleep(delay)
                    continue
                logger.warning(
                    "Gemini generate_content attempt %d failed: %s",
                    attempt + 1,
                    exc,
                )
        if self._debug_logger is not None:
            self._debug_logger.log_exchange(
                provider="gemini",
                model=use_model,
                operation=operation,
                tier=tier,
                prompt=prompt_text,
                response="",
                error=str(last_error),
            )
        raise GeminiServiceError(
            f"Gemini generate_content failed after retries: {last_error}",
            retry_after=TRANSIENT_RETRY_AFTER_DEFAULT,
        )

    def generate_segment(
        self,
        *,
        title: str,
        genre: str,
        narrator_tone: str,
        summary: str,
        past: str,
        last_narrated: str,
        situation: str,
        future_plan: str,
        references: str,
        user_direction: str,
        language: str = "en",
        language_name: str = "English",
        story_arc: str = "",
        model: str | None = None,
        tier: str | None = "segment",
    ) -> SegmentResponse:
        prompt_text = build_prompt(
            title=title,
            genre=genre,
            narrator_tone=narrator_tone,
            story_arc=story_arc,
            summary=summary,
            past=past,
            last_narrated=last_narrated,
            situation=situation,
            future_plan=future_plan,
            references=references,
            user_direction=user_direction,
            language=language,
            language_name=language_name,
        )
        prompts = [prompt_text, prompt_text + STRICT_JSON_SUFFIX]
        last_error: Exception | None = None
        for attempt, current_prompt in enumerate(prompts):
            try:
                raw = self._generate(
                    current_prompt,
                    operation="segment",
                    model=model,
                    tier=tier,
                )
                data = extract_json_object(raw)
                return SegmentResponse(
                    segment_text=data["segment_text"],
                    past_append=data.get("past_append", ""),
                    current_state=data["current_state"],
                    future_plan=data["future_plan"],
                )
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt == 0:
                    logger.warning(
                        "JSON parse failed — retrying with stricter prompt: %s", exc
                    )
                    continue
                raise
        raise ValueError(f"segment JSON parse failed: {last_error}")

    def summarize_past(
        self,
        *,
        existing_summary: str,
        events: str,
        language_name: str = "English",
        model: str | None = None,
        tier: str | None = "summary",
    ) -> str:
        """Fold archived past lines into a rolling story summary."""
        prompt_text = build_summary_prompt(
            existing_summary=existing_summary,
            events=events,
            language_name=language_name,
        )
        raw = self._generate(
            prompt_text, operation="summary", model=model, tier=tier
        )
        data = extract_json_object(raw)
        summary = data.get("summary", "").strip()
        if not summary:
            raise ValueError("summary field missing or empty")
        return summary

    def refresh_story_arc(
        self,
        *,
        story_arc: str,
        summary: str,
        current_state: str,
        future_plan: str,
        language_name: str = "English",
        model: str | None = None,
        tier: str | None = "arc",
    ) -> str:
        """Refresh long-form story arc (tier 3)."""
        prompt_text = build_arc_prompt(
            story_arc=story_arc,
            summary=summary,
            current_state=current_state,
            future_plan=future_plan,
            language_name=language_name,
        )
        raw = self.generate_json(
            prompt_text, operation="arc", model=model, tier=tier
        )
        data = extract_json_object(raw)
        arc = data.get("story_arc", "").strip()
        if not arc:
            raise ValueError("story_arc field missing or empty")
        return arc
