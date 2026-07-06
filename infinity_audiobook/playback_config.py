"""Playback settings loaded from settings.ini."""

from __future__ import annotations

import configparser
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from infinity_audiobook.settings_paths import SETTINGS_FILENAME

from infinity_audiobook.models import SAMPLE_RATE

logger = logging.getLogger(__name__)

DEFAULT_SEGMENT_GAP_SECONDS = 1.0
DEFAULT_MAX_BUFFER_SECONDS = 300.0

# ~150 words/minute — conservative upper bound for prefetch accounting.
_SAMPLES_PER_WORD = int(SAMPLE_RATE * 60 / 150)


@dataclass(frozen=True)
class PlaybackConfig:
    segment_gap_seconds: float = DEFAULT_SEGMENT_GAP_SECONDS
    max_buffer_seconds: float = DEFAULT_MAX_BUFFER_SECONDS


def max_buffer_samples(
    max_buffer_seconds: float,
    *,
    sample_rate: int = SAMPLE_RATE,
) -> int:
    """Convert a buffer cap in seconds to a sample count."""
    return int(max_buffer_seconds * sample_rate)


def estimate_segment_audio_samples(
    text: str,
    *,
    gap_seconds: float = 0.0,
    sample_rate: int = SAMPLE_RATE,
) -> int:
    """Conservative sample estimate for a segment before TTS runs."""
    words = max(len(text.split()), 1)
    speech = words * _SAMPLES_PER_WORD
    gap = int(round(gap_seconds * sample_rate)) if gap_seconds > 0 else 0
    return speech + gap


def buffer_below_limit(
    pending_samples: int,
    max_buffer_seconds: float,
    *,
    sample_rate: int = SAMPLE_RATE,
) -> bool:
    """Return True when more audio may be synthesized into the playback buffer."""
    if max_buffer_seconds <= 0:
        return True
    return pending_samples < max_buffer_samples(
        max_buffer_seconds, sample_rate=sample_rate
    )


class PrefetchAccounting:
    """Track prefetched audio across playback buffer and pipeline queues."""

    def __init__(
        self,
        buffer_samples_fn: Callable[[], int],
    ) -> None:
        self._buffer_samples_fn = buffer_samples_fn
        self._lock = threading.Lock()
        self._text_queue_samples = 0
        self._audio_queue_samples = 0

    def total_samples(self) -> int:
        with self._lock:
            return (
                self._buffer_samples_fn()
                + self._text_queue_samples
                + self._audio_queue_samples
            )

    def on_text_queued(self, samples: int) -> None:
        with self._lock:
            self._text_queue_samples += samples

    def on_text_dequeued(self, samples: int) -> None:
        with self._lock:
            self._text_queue_samples = max(0, self._text_queue_samples - samples)

    def on_audio_queued(self, samples: int) -> None:
        with self._lock:
            self._audio_queue_samples += samples

    def on_audio_dequeued(self, samples: int) -> None:
        with self._lock:
            self._audio_queue_samples = max(0, self._audio_queue_samples - samples)


def _parse_gap_seconds(raw: str) -> float:
    try:
        value = float(raw.strip())
    except ValueError:
        logger.warning(
            "Invalid segment_gap_seconds %r — using default %.1f",
            raw,
            DEFAULT_SEGMENT_GAP_SECONDS,
        )
        return DEFAULT_SEGMENT_GAP_SECONDS
    if value < 0:
        logger.warning("segment_gap_seconds must be >= 0, got %s — using 0", value)
        return 0.0
    return value


def _parse_max_buffer_seconds(raw: str) -> float:
    try:
        value = float(raw.strip())
    except ValueError:
        logger.warning(
            "Invalid max_buffer_seconds %r — using default %.0f",
            raw,
            DEFAULT_MAX_BUFFER_SECONDS,
        )
        return DEFAULT_MAX_BUFFER_SECONDS
    if value < 0:
        logger.warning("max_buffer_seconds must be >= 0, got %s — using 0", value)
        return 0.0
    return value


def load_playback_config_from_parser(
    parser: configparser.ConfigParser | None,
) -> PlaybackConfig:
    """Parse playback settings from an already-loaded ConfigParser."""
    if parser is None or "playback" not in parser:
        return PlaybackConfig()

    section = parser["playback"]
    gap_raw = section.get(
        "segment_gap_seconds",
        str(DEFAULT_SEGMENT_GAP_SECONDS),
    )
    buffer_raw = section.get(
        "max_buffer_seconds",
        str(DEFAULT_MAX_BUFFER_SECONDS),
    )
    return PlaybackConfig(
        segment_gap_seconds=_parse_gap_seconds(gap_raw),
        max_buffer_seconds=_parse_max_buffer_seconds(buffer_raw),
    )


def load_playback_config(path: Path) -> PlaybackConfig:
    """Load playback settings from settings.ini. Missing section returns defaults."""
    from infinity_audiobook.settings import read_settings_parser

    return load_playback_config_from_parser(read_settings_parser(path))


__all__ = [
    "DEFAULT_MAX_BUFFER_SECONDS",
    "DEFAULT_SEGMENT_GAP_SECONDS",
    "PlaybackConfig",
    "PrefetchAccounting",
    "SETTINGS_FILENAME",
    "buffer_below_limit",
    "estimate_segment_audio_samples",
    "load_playback_config",
    "load_playback_config_from_parser",
    "max_buffer_samples",
]
