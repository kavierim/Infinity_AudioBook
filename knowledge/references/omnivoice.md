---
type: Reference
title: OmniVoice
description: PyPI omnivoice 0.1.5 — zero-shot voice cloning TTS used by infinity_audiobook/tts.py.
resource: https://pypi.org/project/omnivoice/
tags: [reference, tts, omnivoice]
timestamp: 2026-07-05T07:30:00Z
---

# Integration

| Property | Value |
|---|---|
| Package | `omnivoice==0.1.5` |
| Model | `k2-fsa/OmniVoice` (Hugging Face) |
| Mode | Voice cloning only — **no `instruct`** |
| Sample rate | 24000 Hz mono float32 |
| Device | CUDA preferred (`torch 2.8.0+cu128` on Windows) |

# Usage pattern

```python
model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cuda", dtype=torch.float16)
voice_prompt = model.create_voice_clone_prompt(ref_audio=path, ref_text=transcript)
audio = model.generate(text=segment, language="en", voice_clone_prompt=voice_prompt)[0]
```

Voice prompt created once at startup, reused per segment.

# Reference assets

Bundled in `assets/` — see [TTS module](/modules/tts.md).

# Citations

[1] [omnivoice on PyPI](https://pypi.org/project/omnivoice/)
[2] [k2-fsa/OmniVoice on Hugging Face](https://huggingface.co/k2-fsa/OmniVoice)
