"""Tests for TTS engine — mocked OmniVoice."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from infinity_audiobook.tts import TTSEngine, validate_reference_assets


def test_validate_reference_assets_missing_audio(tmp_path: Path) -> None:
    txt = tmp_path / "speaker_reference.txt"
    txt.write_text("Hello world.", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_reference_assets(tmp_path / "missing.wav", txt)


def test_validate_reference_assets_empty_text(tmp_path: Path) -> None:
    wav = tmp_path / "speaker_reference.wav"
    txt = tmp_path / "speaker_reference.txt"
    # Copy real wav if available, else skip audio check
    real_wav = Path("assets/speaker_reference.wav")
    if real_wav.is_file():
        wav.write_bytes(real_wav.read_bytes())
    else:
        pytest.skip("No reference wav available")
    txt.write_text("   ", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_reference_assets(wav, txt)


def test_synthesize_uses_voice_clone_prompt(tmp_path: Path) -> None:
    wav = Path("assets/speaker_reference.wav")
    txt = Path("assets/speaker_reference.txt")
    if not wav.is_file():
        pytest.skip("Reference assets not present")

    mock_model = MagicMock()
    mock_model.sampling_rate = 24_000
    fake_audio = np.zeros(4800, dtype=np.float32)
    mock_model.generate.return_value = [fake_audio]
    voice_prompt = object()

    engine = TTSEngine(
        ref_audio=wav,
        ref_text_file=txt,
        model=mock_model,
        voice_prompt=voice_prompt,
    )

    result = engine.synthesize("Test narration.", language="en")

    mock_model.generate.assert_called_once()
    call_kwargs = mock_model.generate.call_args.kwargs
    assert call_kwargs["voice_clone_prompt"] is voice_prompt
    assert "instruct" not in call_kwargs
    np.testing.assert_array_equal(result, fake_audio)


def test_synthesize_splits_long_text_into_chunks(tmp_path: Path) -> None:
    wav = Path("assets/speaker_reference.wav")
    txt = Path("assets/speaker_reference.txt")
    if not wav.is_file():
        pytest.skip("Reference assets not present")

    mock_model = MagicMock()
    mock_model.sampling_rate = 24_000
    fake_audio = np.ones(2400, dtype=np.float32)
    mock_model.generate.return_value = [fake_audio]
    voice_prompt = object()

    engine = TTSEngine(
        ref_audio=wav,
        ref_text_file=txt,
        model=mock_model,
        voice_prompt=voice_prompt,
    )

    sentences = [f"This is sentence number {i}." for i in range(12)]
    long_text = " ".join(sentences)
    result = engine.synthesize(long_text, language="fi")

    assert mock_model.generate.call_count >= 2
    assert len(result) > len(fake_audio)
    for call in mock_model.generate.call_args_list:
        assert call.kwargs["audio_chunk_threshold"] == 15.0
        assert "instruct" not in call.kwargs

    wav = Path("assets/speaker_reference.wav")
    txt = Path("assets/speaker_reference.txt")
    if not wav.is_file():
        pytest.skip("Reference assets not present")

    mock_model = MagicMock()
    mock_model.sampling_rate = 24_000
    mock_prompt = object()
    mock_model.create_voice_clone_prompt.return_value = mock_prompt

    with patch("omnivoice.OmniVoice") as mock_cls:
        mock_cls.from_pretrained.return_value = mock_model
        with patch("infinity_audiobook.tts._get_best_device", return_value="cpu"):
            engine = TTSEngine(ref_audio=wav, ref_text_file=txt)
            engine.load()

    mock_model.create_voice_clone_prompt.assert_called_once()
    assert engine._voice_prompt is mock_prompt
