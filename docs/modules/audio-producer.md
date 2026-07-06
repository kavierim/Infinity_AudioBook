---
type: Module
title: Audio producer
description: Background thread that synthesizes segments via OmniVoice and pushes audio chunks.
tags: [module, tts, audio-producer]
timestamp: 2026-07-06T12:30:00Z
---

# File

`infinity_audiobook/audio_producer.py`

# Loop

1. Wait if `audio_queue` is full or player buffer exceeds cap.
2. Pop `Segment` from `text_queue`.
3. Resolve `language` via `StoryLanguageCache` (re-reads `story.md` only when mtime changes; picks up mid-session language edits).
4. `synthesizer.synthesize(text, language=language)`.
5. Append [segment gap](/configuration/playback.md) silence.
6. Push `AudioChunk` to `audio_queue`.

On TTS failure: log error, skip segment, continue.

# Synthesizer protocol

```python
def synthesize(self, text: str, *, language: str | None = None) -> np.ndarray: ...
```

Implemented by [TTSEngine](tts.md).
