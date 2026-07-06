"""Shared data models for the audiobook pipeline."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Segment:
    """Text segment waiting for TTS synthesis."""

    text: str
    segment_id: int
    estimated_samples: int = 0


@dataclass
class AudioChunk:
    """Synthesized audio ready for playback."""

    audio: np.ndarray
    segment_id: int


SAMPLE_RATE = 24_000
BLOCKSIZE = 2048
TEXT_QUEUE_MAXSIZE = 2
AUDIO_QUEUE_MAXSIZE = 2
MAX_SEGMENT_WORDS = 200
PROMPT_PAST_MAX_LINES = 12
PAST_ARCHIVE_THRESHOLD = 25
PAST_KEEP_AFTER_ARCHIVE = 10
SUMMARY_MAX_WORDS = 350
