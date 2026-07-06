"""Split narration text into TTS-sized chunks at sentence boundaries."""

from __future__ import annotations

import re

# Keep each OmniVoice call short enough that duration estimation cannot cut audio.
TTS_CHUNK_MAX_WORDS = 50
TTS_CHUNK_PAUSE_SECONDS = 0.15

_SENTENCE_BREAK_RE = re.compile(
    r"""
    (?<=[.!?…])          # sentence-ending punctuation
    (?:["'»」】])?        # optional closing quote/bracket
    \s+
    """,
    re.VERBOSE,
)


def split_sentences(text: str) -> list[str]:
    """Split prose into sentences, preserving terminal punctuation."""
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return []

    parts = _SENTENCE_BREAK_RE.split(normalized)
    sentences = [part.strip() for part in parts if part.strip()]
    return sentences if sentences else [normalized]


def split_text_for_tts(text: str, *, max_words: int = TTS_CHUNK_MAX_WORDS) -> list[str]:
    """Group sentences into chunks that stay under *max_words* per TTS call."""
    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())
        if sentence_words > max_words:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_words = 0
            chunks.append(sentence)
            continue

        if current_words + sentence_words > max_words and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_words = sentence_words
        else:
            current.append(sentence)
            current_words += sentence_words

    if current:
        chunks.append(" ".join(current))

    return chunks


__all__ = [
    "TTS_CHUNK_MAX_WORDS",
    "TTS_CHUNK_PAUSE_SECONDS",
    "split_sentences",
    "split_text_for_tts",
]
