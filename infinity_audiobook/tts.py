"""OmniVoice TTS wrapper — voice cloning only."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from infinity_audiobook.models import SAMPLE_RATE
from infinity_audiobook.tts_chunks import (
    TTS_CHUNK_PAUSE_SECONDS,
    split_text_for_tts,
)

logger = logging.getLogger(__name__)

REF_AUDIO = Path("assets/speaker_reference.wav")
REF_TEXT_FILE = Path("assets/speaker_reference.txt")
MODEL_ID = "k2-fsa/OmniVoice"


def _get_best_device() -> str:
    """Auto-detect the best available device: CUDA > XPU > MPS > CPU."""
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch, "xpu") and torch.xpu.is_available():
        return "xpu"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def validate_reference_assets(
    ref_audio: Path = REF_AUDIO,
    ref_text_file: Path = REF_TEXT_FILE,
) -> str:
    """Validate bundled narrator reference files. Returns ref_text."""
    if not ref_audio.is_file():
        raise FileNotFoundError(f"Missing reference audio: {ref_audio}")
    if not ref_text_file.is_file():
        raise FileNotFoundError(f"Missing reference transcript: {ref_text_file}")

    ref_text = ref_text_file.read_text(encoding="utf-8").strip()
    if not ref_text:
        raise ValueError(f"Reference transcript is empty: {ref_text_file}")

    try:
        info = sf.info(str(ref_audio))
        duration = info.duration
        if duration < 3.0 or duration > 10.0:
            logger.warning(
                "Reference WAV duration %.1fs is outside recommended 3–10s range",
                duration,
            )
        if info.samplerate != SAMPLE_RATE:
            logger.warning(
                "Reference WAV sample rate %d differs from expected %d",
                info.samplerate,
                SAMPLE_RATE,
            )
    except Exception as exc:
        logger.warning("Could not inspect reference WAV: %s", exc)

    return ref_text


class TTSEngine:
    """OmniVoice voice-cloning synthesizer."""

    def __init__(
        self,
        *,
        ref_audio: Path = REF_AUDIO,
        ref_text_file: Path = REF_TEXT_FILE,
        model: object | None = None,
        voice_prompt: object | None = None,
    ) -> None:
        self._ref_audio = ref_audio
        self._ref_text = validate_reference_assets(ref_audio, ref_text_file)
        self._model = model
        self._voice_prompt = voice_prompt
        self._language = "en"

    @property
    def sampling_rate(self) -> int:
        if self._model is not None:
            return int(getattr(self._model, "sampling_rate", SAMPLE_RATE))
        return SAMPLE_RATE

    def load(self) -> None:
        if self._model is not None:
            return
        from omnivoice import OmniVoice

        self._model = OmniVoice.from_pretrained(
            MODEL_ID,
            device_map=_get_best_device(),
            dtype=torch.float16,
        )
        self._voice_prompt = self._model.create_voice_clone_prompt(
            ref_audio=str(self._ref_audio),
            ref_text=self._ref_text,
        )
        logger.info("OmniVoice model loaded with voice clone prompt")

    def _synthesize_chunk(self, text: str, *, language: str) -> np.ndarray:
        """Synthesize one TTS-sized text chunk via OmniVoice."""
        return self._model.generate(
            text=text,
            language=language,
            voice_clone_prompt=self._voice_prompt,
            # Force internal chunking for unusually long single sentences.
            audio_chunk_threshold=15.0,
            audio_chunk_duration=12.0,
        )[0].astype(np.float32)

    def synthesize(self, text: str, *, language: str | None = None) -> np.ndarray:
        if self._model is None or self._voice_prompt is None:
            raise RuntimeError("TTS model not loaded; call load() first")

        lang = language or self._language
        chunks = split_text_for_tts(text)
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        if len(chunks) == 1:
            return self._synthesize_chunk(chunks[0], language=lang)

        pause = np.zeros(
            int(round(self.sampling_rate * TTS_CHUNK_PAUSE_SECONDS)),
            dtype=np.float32,
        )
        parts: list[np.ndarray] = []
        for index, chunk in enumerate(chunks):
            parts.append(self._synthesize_chunk(chunk, language=lang))
            if index < len(chunks) - 1 and pause.size > 0:
                parts.append(pause)
        return np.concatenate(parts)

    def set_language(self, language: str) -> None:
        self._language = language
