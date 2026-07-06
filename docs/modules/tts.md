---
type: Module
title: TTS engine
description: OmniVoice voice-cloning wrapper — loads model once, reuses voice prompt per segment.
tags: [module, tts, omnivoice]
timestamp: 2026-07-05T07:30:00Z
---

# File

`infinity_audiobook/tts.py`

# Assets (required at startup)

Both files are **required** at startup. Replace both to change narrator voice.

| File | Purpose |
|---|---|
| `assets/speaker_reference.wav` | Reference audio (`ref_audio`) |
| `assets/speaker_reference.txt` | Transcript (`ref_text`) — must match what is spoken in the WAV |

## speaker_reference.wav properties

| Property | Value |
|---|---|
| Duration | ~4.0 s |
| Sample rate | 24 000 Hz |
| Channels | Mono |
| Format | 16-bit PCM WAV |

Sample rate matches OmniVoice output and playback — no resampling needed.

## speaker_reference.txt content

```
The reason is not that AI is useless. The reason is that the bottleneck moves.
```

English reference; Finnish (`language: fi`) narration works but the clone timbre stays English.

See [OmniVoice reference](/references/omnivoice.md).

# TTSEngine

1. `validate_reference_assets()` — fail fast if missing; warn if duration outside 3–10 s.
2. `load()` — `OmniVoice.from_pretrained("k2-fsa/OmniVoice")`, `create_voice_clone_prompt`.
3. `set_language(code)` — `en` or `fi` for `model.generate(language=...)`.
4. `synthesize(text)` — returns mono float32 at 24 kHz.

# Device selection

`_get_best_device()`: CUDA > XPU > MPS > CPU.

# Usage in code

```python
from omnivoice import OmniVoice

REF_AUDIO = Path("assets/speaker_reference.wav")
REF_TEXT = Path("assets/speaker_reference.txt").read_text(encoding="utf-8").strip()

model = OmniVoice.from_pretrained(
    "k2-fsa/OmniVoice",
    device_map=_get_best_device(),  # cuda > xpu > mps > cpu
    dtype=torch.float16,
)
voice_prompt = model.create_voice_clone_prompt(
    ref_audio=str(REF_AUDIO),
    ref_text=REF_TEXT,
)

# Per segment:
audio = model.generate(
    text=segment.text,
    language="en",
    voice_clone_prompt=voice_prompt,
)[0].astype(np.float32)
```

Voice prompt created once at startup, reused per segment.

# Validation at startup

- Both files must exist; exit with a clear error if either is missing.
- `speaker_reference.txt` must be non-empty.
- Warn if WAV duration is outside 3–10 s (OmniVoice recommendation).

# Constraints

- **Voice cloning only** — no OmniVoice `instruct` parameter.
- Style controlled via LLM prose and `narrator_tone` in story.md.
