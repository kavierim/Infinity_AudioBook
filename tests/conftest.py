"""Shared pytest fixtures."""

from __future__ import annotations

import numpy as np
import pytest

from infinity_audiobook.llm_prompts import SegmentResponse


@pytest.fixture
def sample_segment_response() -> SegmentResponse:
    return SegmentResponse(
        segment_text="The fog rolls in across the rocky shore.",
        past_append="Fog arrived at the lighthouse.",
        current_state="Visibility drops to a few meters.",
        future_plan="A boat approaches through the mist.",
    )


@pytest.fixture
def tone_audio() -> np.ndarray:
    """1 second 440 Hz sine at 24 kHz."""
    sr = 24_000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
