"""Tests for seamless audio playback."""

from __future__ import annotations

import threading
import time
from queue import Queue

import numpy as np
import pytest

from infinity_audiobook.models import AudioChunk, BLOCKSIZE, SAMPLE_RATE
from infinity_audiobook.player import PlaybackBuffer, Player


def test_playback_buffer_read_exact() -> None:
    buf = PlaybackBuffer()
    samples = np.arange(10, dtype=np.float32)
    buf.append(samples)
    out = buf.read(5)
    np.testing.assert_array_equal(out, samples[:5])
    assert buf.pending_samples() == 5


def test_playback_buffer_underrun_pads_zeros() -> None:
    buf = PlaybackBuffer()
    buf.append(np.ones(3, dtype=np.float32))
    out = buf.read(8)
    assert out.shape == (8,)
    np.testing.assert_array_equal(out[:3], np.ones(3))
    np.testing.assert_array_equal(out[3:], np.zeros(5))


def test_player_feeder_fills_buffer(tone_audio: np.ndarray) -> None:
    audio_queue: Queue[AudioChunk] = Queue(maxsize=2)
    shutdown = threading.Event()
    player = Player(audio_queue, shutdown, samplerate=SAMPLE_RATE, blocksize=BLOCKSIZE)

    # Do not start OutputStream in unit tests — test feeder + buffer only
    feeder = threading.Thread(target=player._feeder_loop, daemon=True)
    feeder.start()

    audio_queue.put(AudioChunk(audio=tone_audio, segment_id=1))

    deadline = time.monotonic() + 3.0
    while player.buffer.pending_samples() == 0 and time.monotonic() < deadline:
        time.sleep(0.05)

    shutdown.set()
    feeder.join(timeout=2.0)

    assert player.buffer.pending_samples() == len(tone_audio)


def test_callback_reads_buffer_only() -> None:
    """Callback must not touch the queue — only the buffer."""
    audio_queue: Queue[AudioChunk] = Queue(maxsize=2)
    shutdown = threading.Event()
    player = Player(audio_queue, shutdown, blocksize=16)

    player.buffer.append(np.full(32, 0.5, dtype=np.float32))
    outdata = np.zeros((16, 1), dtype=np.float32)
    player._callback(outdata, 16, None, 0)
    np.testing.assert_array_almost_equal(outdata[:, 0], np.full(16, 0.5))
    assert audio_queue.empty()
