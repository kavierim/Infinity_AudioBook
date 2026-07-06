"""Three-tier Gemini client — different models per LLM operation."""

from __future__ import annotations

import logging
from typing import Any, Callable

from infinity_audiobook.gemini_client import GeminiClient
from infinity_audiobook.llm_debug import LLMDebugLogger
from infinity_audiobook.llm_prompts import SegmentResponse
from infinity_audiobook.story_arc import arc_refresh_due

logger = logging.getLogger(__name__)


class TieredGeminiClient:
    """Routes segment, summary, and arc operations to configured Gemini models."""

    def __init__(
        self,
        *,
        model_segment: str,
        model_summary: str,
        model_arc: str,
        arc_refresh_every: int = 20,
        api_key: str | None = None,
        client_factory: Callable[[str], Any] | None = None,
        debug_logger: LLMDebugLogger | None = None,
    ) -> None:
        self._model_segment = model_segment
        self._model_summary = model_summary
        self._model_arc = model_arc
        self._arc_refresh_every = arc_refresh_every
        self._segment_count = 0
        self._client = GeminiClient(
            model=model_segment,
            api_key=api_key,
            client_factory=client_factory,
            debug_logger=debug_logger,
        )

    @property
    def model_segment(self) -> str:
        return self._model_segment

    @property
    def model_summary(self) -> str:
        return self._model_summary

    @property
    def model_arc(self) -> str:
        return self._model_arc

    @property
    def segment_count(self) -> int:
        return self._segment_count

    def tier_summary(self) -> str:
        return (
            f"segment={self._model_segment}, "
            f"summary={self._model_summary}, "
            f"arc={self._model_arc}"
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
    ) -> SegmentResponse:
        self._segment_count += 1
        return self._client.generate_segment(
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
            model=self._model_segment,
            tier="segment",
        )

    def summarize_past(
        self,
        *,
        existing_summary: str,
        events: str,
        language_name: str = "English",
    ) -> str:
        return self._client.summarize_past(
            existing_summary=existing_summary,
            events=events,
            language_name=language_name,
            model=self._model_summary,
            tier="summary",
        )

    def refresh_story_arc(
        self,
        *,
        story_arc: str,
        summary: str,
        current_state: str,
        future_plan: str,
        language_name: str = "English",
    ) -> str:
        """Refresh long-form story arc using tier-3 model."""
        return self._client.refresh_story_arc(
            story_arc=story_arc,
            summary=summary,
            current_state=current_state,
            future_plan=future_plan,
            language_name=language_name,
            model=self._model_arc,
            tier="arc",
        )

    def should_refresh_arc(self, *, has_story_arc_section: bool) -> bool:
        """True when arc refresh is due and story.md has a story_arc section."""
        return arc_refresh_due(
            segment_count=self._segment_count,
            arc_refresh_every=self._arc_refresh_every,
            has_story_arc_section=has_story_arc_section,
        )


__all__ = ["TieredGeminiClient"]
