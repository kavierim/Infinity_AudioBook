"""LLM provider settings and client factory."""

from __future__ import annotations

import configparser
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from infinity_audiobook.llm_debug import LLMDebugLogger, debug_enabled_from_env, parse_debug_flag
from infinity_audiobook.settings_paths import SETTINGS_FILENAME

if TYPE_CHECKING:
    from infinity_audiobook.text_producer import SegmentGenerator

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_ARC_REFRESH_EVERY = 20
VALID_LLM_PROVIDERS = frozenset({"gemini"})
LEGACY_LLM_PROVIDERS = frozenset({"cursor", "copilot", "custom"})

_LEGACY_PROVIDER_ERROR = (
    "LLM provider '{provider}' is no longer supported. "
    "Set provider = gemini in [llm] and configure GEMINI_API_KEY or GOOGLE_API_KEY."
)


@dataclass
class LLMConfig:
    provider: str = "gemini"
    model: str | None = None
    model_segment: str | None = None
    model_summary: str | None = None
    model_arc: str | None = None
    arc_refresh_every: int = DEFAULT_ARC_REFRESH_EVERY
    debug_traffic: bool = False

    def effective_model_segment(self) -> str:
        return self.model_segment or self.model or DEFAULT_GEMINI_MODEL

    def effective_model_summary(self) -> str:
        return self.model_summary or self.model or DEFAULT_GEMINI_MODEL

    def effective_model_arc(self) -> str:
        return self.model_arc or self.model or DEFAULT_GEMINI_MODEL

    def summary(self) -> str:
        parts = [
            f"segment={self.effective_model_segment()}",
            f"summary={self.effective_model_summary()}",
            f"arc={self.effective_model_arc()}",
        ]
        line = f"gemini tiers: {', '.join(parts)}"
        if self.arc_refresh_every:
            line += f" (arc refresh every {self.arc_refresh_every} segments)"
        return line


def _resolve_model(provider: str, model_raw: str) -> str | None:
    model = model_raw.strip() or None
    if provider == "gemini" and not model:
        return DEFAULT_GEMINI_MODEL
    return model


def _resolve_tier_models(
    provider: str,
    section: configparser.SectionProxy,
) -> tuple[str | None, str | None, str | None]:
    """Resolve per-tier Gemini models with backward-compat from single model=."""
    model = _resolve_model(provider, section.get("model", ""))
    segment = section.get("model_segment", "").strip() or None
    summary = section.get("model_summary", "").strip() or None
    arc = section.get("model_arc", "").strip() or None

    if not any((segment, summary, arc)):
        return model, model, model

    fallback = model or (DEFAULT_GEMINI_MODEL if provider == "gemini" else None)
    return (
        segment or fallback,
        summary or fallback,
        arc or fallback,
    )


def _load_arc_refresh_every(section: configparser.SectionProxy) -> int:
    raw = section.get("arc_refresh_every", str(DEFAULT_ARC_REFRESH_EVERY)).strip()
    try:
        return int(raw)
    except ValueError:
        logger.warning(
            "Invalid arc_refresh_every=%r — using %d",
            raw,
            DEFAULT_ARC_REFRESH_EVERY,
        )
        return DEFAULT_ARC_REFRESH_EVERY


def _reject_legacy_provider(provider: str) -> None:
    if provider in LEGACY_LLM_PROVIDERS:
        raise ValueError(_LEGACY_PROVIDER_ERROR.format(provider=provider))


def _validate_provider(provider: str) -> None:
    if provider not in VALID_LLM_PROVIDERS:
        raise ValueError(
            f"Unknown LLM provider '{provider}'. "
            f"Use one of: {', '.join(sorted(VALID_LLM_PROVIDERS))}"
        )


def _load_debug_traffic(section: configparser.SectionProxy) -> bool:
    enabled = parse_debug_flag(section.get("debug_traffic", "false"))
    if debug_enabled_from_env():
        return True
    return enabled


def load_llm_config_from_parser(
    parser: configparser.ConfigParser | None,
    *,
    path_name: str = SETTINGS_FILENAME,
) -> LLMConfig:
    """Parse LLM settings from an already-loaded ConfigParser."""
    if parser is None:
        logger.info("No %s found — using default LLM provider (gemini)", path_name)
        return LLMConfig(debug_traffic=debug_enabled_from_env())

    if "llm" in parser:
        section = parser["llm"]
        provider = section.get("provider", "gemini").strip().lower()
        _reject_legacy_provider(provider)
        _validate_provider(provider)
        model_segment, model_summary, model_arc = _resolve_tier_models(provider, section)
        return LLMConfig(
            provider=provider,
            model=_resolve_model(provider, section.get("model", "")),
            model_segment=model_segment,
            model_summary=model_summary,
            model_arc=model_arc,
            arc_refresh_every=_load_arc_refresh_every(section),
            debug_traffic=_load_debug_traffic(section),
        )

    if "acp" in parser:
        section = parser["acp"]
        provider = section.get("provider", "cursor").strip().lower()
        _reject_legacy_provider(provider)

    logger.warning("%s has no [llm] section — using defaults", path_name)
    return LLMConfig(debug_traffic=debug_enabled_from_env())


def load_llm_config(path: Path) -> LLMConfig:
    """Load LLM settings from settings.ini."""
    from infinity_audiobook.settings import read_settings_parser

    return load_llm_config_from_parser(read_settings_parser(path), path_name=path.name)


def create_llm_client(config: LLMConfig, settings_path: Path, cwd: Path) -> SegmentGenerator:
    """Create the segment generator for the configured LLM provider."""
    debug_logger = LLMDebugLogger(
        cwd / "debug" / "llm",
        enabled=config.debug_traffic,
    )
    from infinity_audiobook.gemini_tiered import TieredGeminiClient

    return TieredGeminiClient(
        model_segment=config.effective_model_segment(),
        model_summary=config.effective_model_summary(),
        model_arc=config.effective_model_arc(),
        arc_refresh_every=config.arc_refresh_every,
        debug_logger=debug_logger,
    )


__all__ = [
    "DEFAULT_ARC_REFRESH_EVERY",
    "DEFAULT_GEMINI_MODEL",
    "LLMConfig",
    "SETTINGS_FILENAME",
    "create_llm_client",
    "load_llm_config",
    "load_llm_config_from_parser",
]
