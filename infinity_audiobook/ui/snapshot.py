"""Thread-safe UI snapshot updated from producer threads."""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass

TRANSCRIPT_RING_SIZE = 10


@dataclass(frozen=True)
class TranscriptEntry:
    segment_id: int
    text: str


class UISnapshot:
    """In-memory transcript ring and pipeline event markers for the TUI."""

    def __init__(self, *, transcript_capacity: int = TRANSCRIPT_RING_SIZE) -> None:
        if transcript_capacity < 5:
            raise ValueError("transcript_capacity must be >= 5")
        self._lock = threading.Lock()
        self._transcript: deque[TranscriptEntry] = deque(maxlen=transcript_capacity)

    def record_segment_queued(self, segment_id: int, text: str) -> None:
        with self._lock:
            self._transcript.append(TranscriptEntry(segment_id=segment_id, text=text))

    def seed_transcript(self, segment_id: int, text: str) -> None:
        """Seed transcript ring from disk when empty (cold start after restart)."""
        with self._lock:
            if not self._transcript and text.strip():
                self._transcript.append(TranscriptEntry(segment_id=segment_id, text=text))

    def transcript_snapshot(self) -> list[TranscriptEntry]:
        with self._lock:
            return list(self._transcript)
