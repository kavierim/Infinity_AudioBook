---
type: Architecture
title: Tech stack
description: Languages, libraries, CUDA toolchain, and pyproject.toml dependency layout.
tags: [architecture, dependencies, uv, cuda]
timestamp: 2026-07-06T09:30:00Z
---

# Components

| Component | Choice |
|---|---|
| Language | Python 3.10+ |
| Package manager | `uv` |
| LLM & logic | Google AI Studio (Gemini) |
| TTS | `omnivoice` Python library — **voice cloning only** |
| Audio playback | `sounddevice`, `numpy` |
| Concurrency | `threading`, `queue` |
| Terminal UI | `textual` (full-screen dashboard) |
| Testing | `pytest`, `unittest.mock` |

# Reference environment

PyPI `omnivoice` 0.1.5. Voice-cloning pattern originally from `C:\Work\OmniVoice\kari\exampe.py`.

| Package | Version |
|---|---|
| Python | ≥ 3.10 |
| torch | 2.8.0+cu128 |
| torchaudio | 2.8.0+cu128 |
| omnivoice | 0.1.5 |
| CUDA | 12.8 |

# pyproject.toml

Match the OmniVoice project's CUDA index on Windows:

```toml
[project]
name = "infinity-audiobook"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
  "numpy",
  "sounddevice",
  "soundfile",
  "torch>=2.4",
  "torchaudio>=2.4",
  "omnivoice==0.1.5",
  "pytest",
  "google-genai>=2.10.0",
  "python-dotenv>=1.2.2",
  "textual>=8.2.8",
]

[project.scripts]
infinity-audiobook = "infinity_audiobook.main:main"

[tool.uv.sources]
torch = [{ index = "pytorch-cuda", marker = "sys_platform == 'win32'" }]
torchaudio = [{ index = "pytorch-cuda", marker = "sys_platform == 'win32'" }]

[[tool.uv.index]]
name = "pytorch-cuda"
url = "https://download.pytorch.org/whl/cu128"
explicit = true

[tool.uv]
constraint-dependencies = ["torch==2.8.0", "torchaudio==2.8.0"]
```

# Setup

```bash
uv sync
```

From the project root. Requires `GEMINI_API_KEY` or `GOOGLE_API_KEY` for LLM playback.

**Hardware:** NVIDIA GPU with CUDA 12.8. Model weights download from Hugging Face on first run (`k2-fsa/OmniVoice`).

See [quick start](/playbooks/quick-start.md) and [OmniVoice reference](/references/omnivoice.md).
