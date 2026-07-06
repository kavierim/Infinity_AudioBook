"""Tests for TTS text chunking."""

from __future__ import annotations

from infinity_audiobook.tts_chunks import split_sentences, split_text_for_tts


def test_split_sentences_finnish_punctuation() -> None:
    text = "Hän astui sisään. Ovi narahti! Mitä nyt? Hän odotti."
    sentences = split_sentences(text)
    assert len(sentences) == 4
    assert sentences[0].endswith(".")
    assert sentences[1].endswith("!")
    assert sentences[2].endswith("?")


def test_split_text_for_tts_groups_sentences() -> None:
    words = [f"word{i}" for i in range(120)]
    text = ". ".join(" ".join(words[i : i + 10]) + "." for i in range(0, 120, 10))
    chunks = split_text_for_tts(text, max_words=50)
    assert len(chunks) >= 2
    assert all(len(chunk.split()) <= 50 for chunk in chunks)
    assert "word0" in chunks[0]
    assert "word119" in chunks[-1]


def test_split_text_for_tts_keeps_short_text_single_chunk() -> None:
    text = "Short narration stays in one piece."
    assert split_text_for_tts(text) == [text]


def test_split_text_for_tts_handles_long_single_sentence() -> None:
    text = " ".join(["word"] * 80) + "."
    chunks = split_text_for_tts(text, max_words=50)
    assert chunks == [text]
