"""Seamless audio playback via feeder thread + OutputStream callback."""

from __future__ import annotations

import logging
import threading
import time
from queue import Empty, Queue
from typing import TYPE_CHECKING

import numpy as np
import sounddevice as sd

from infinity_audiobook.models import BLOCKSIZE, SAMPLE_RATE, AudioChunk

if TYPE_CHECKING:
    from infinity_audiobook.models import AudioChunk as AudioChunkType
    from infinity_audiobook.playback_config import PrefetchAccounting

logger = logging.getLogger(__name__)


class PlaybackBuffer:
    """Thread-safe ring-like buffer of float32 mono samples."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._samples = np.zeros(0, dtype=np.float32)

    def append(self, audio: np.ndarray) -> None:
        with self._lock:
            self._samples = np.concatenate([self._samples, audio.astype(np.float32)])

    def read(self, count: int) -> np.ndarray:
        with self._lock:
            if len(self._samples) >= count:
                out = self._samples[:count].copy()
                self._samples = self._samples[count:]
                return out
            if len(self._samples) == 0:
                return np.zeros(count, dtype=np.float32)
            out = np.zeros(count, dtype=np.float32)
            n = len(self._samples)
            out[:n] = self._samples
            self._samples = np.zeros(0, dtype=np.float32)
            return out

    def pending_samples(self) -> int:
        with self._lock:
            return len(self._samples)

    def clear(self) -> None:
        with self._lock:
            self._samples = np.zeros(0, dtype=np.float32)


class Player:
    """Consumes AudioChunk items and plays them through the default output device."""

    def __init__(
        self,
        audio_queue: Queue[AudioChunk],
        shutdown_event: threading.Event,
        *,
        samplerate: int = SAMPLE_RATE,
        blocksize: int = BLOCKSIZE,
        prefetch: PrefetchAccounting | None = None,
    ) -> None:
        self._audio_queue = audio_queue
        self._shutdown = shutdown_event
        self._samplerate = samplerate
        self._blocksize = blocksize
        self._buffer = PlaybackBuffer()
        self._prefetch = prefetch
        self._stream: sd.OutputStream | None = None
        self._feeder_thread: threading.Thread | None = None
        self._underrun_count = 0

    @property
    def buffer(self) -> PlaybackBuffer:
        return self._buffer

    def bind_prefetch(self, prefetch: PrefetchAccounting) -> None:
        """Attach prefetch accounting after construction (needs buffer ref)."""
        self._prefetch = prefetch

    @property
    def underrun_count(self) -> int:
        return self._underrun_count

    def _callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            logger.debug("OutputStream status: %s", status)
        block = self._buffer.read(frames)
        if np.all(block == 0) and self._buffer.pending_samples() == 0:
            self._underrun_count += 1
        outdata[:, 0] = block

    def _feeder_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                chunk = self._audio_queue.get(timeout=0.1)
            except Empty:
                continue
            if self._prefetch is not None:
                self._prefetch.on_audio_dequeued(len(chunk.audio))
            self._buffer.append(chunk.audio)
            self._audio_queue.task_done()

    def start(self) -> None:
        self._feeder_thread = threading.Thread(
            target=self._feeder_loop, name="player-feeder", daemon=True
        )
        self._feeder_thread.start()
        self._stream = sd.OutputStream(
            samplerate=self._samplerate,
            channels=1,
            dtype="float32",
            blocksize=self._blocksize,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self, *, drain_timeout: float = 2.0) -> None:
        """Stop feeder and output stream; drain playback buffer when possible."""
        self._shutdown.set()
        if self._feeder_thread is not None:
            self._feeder_thread.join(timeout=2.0)
        if self._stream is not None and drain_timeout > 0:
            deadline = time.monotonic() + drain_timeout
            while (
                time.monotonic() < deadline
                and self._buffer.pending_samples() > 0
            ):
                time.sleep(0.05)
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def wait_until_idle(self, timeout: float = 30.0) -> bool:
        """Wait until queues and buffer are drained."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if (
                self._audio_queue.empty()
                and self._buffer.pending_samples() == 0
            ):
                return True
            time.sleep(0.05)
        return False
