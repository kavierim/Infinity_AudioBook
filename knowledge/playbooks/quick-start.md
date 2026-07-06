---
type: Playbook
title: Quick start
description: Install dependencies, prepare story.md, authenticate, and run the audiobook player.
tags: [playbook, quick-start]
timestamp: 2026-07-06T08:45:00Z
---

# Prerequisites

| Component | Notes |
|---|---|
| Python 3.10+ | |
| [uv](https://docs.astral.sh/uv/) | Package manager |
| NVIDIA GPU | Practical TTS use; CUDA 12.8 on Windows |
| LLM credentials | See [authentication](authentication.md) |

# Steps

## 1. Install dependencies

```bash
cd InfinityAudioBook
uv sync
```

First run downloads OmniVoice weights from Hugging Face (`k2-fsa/OmniVoice`). Model load can take several minutes.

## 2. Prepare story.md

Edit `story.md` before the first run. Set at least:

- `## title`
- `## current_state` — set the opening **Situation** beat (plain text is fine before the first segment; after segment #1 the app writes the structured `Last narrated` + `Situation` layout automatically)
- `## future_plan`

When `past` is empty, the opening segment is generated from the `Situation` beat in `current_state` + `future_plan`.

On **restart** with an existing `Last narrated` block, TTS replays that segment immediately while the LLM prepares the next one in the background.

## 3. Authenticate

See [authentication](authentication.md). Set `GEMINI_API_KEY` or `GOOGLE_API_KEY` in `.env` (copy from `.env.example`).

## 4. Configure (optional)

```bash
cp settings.example.ini settings.ini   # Linux/macOS
copy settings.example.ini settings.ini # Windows
```

Defaults without `settings.ini`: `provider = gemini`, tier models fall back to `gemini-2.5-flash`.

## 5. Run

```bash
uv run python -m infinity_audiobook
```

Story language comes from `[story] language` in `settings.ini` (or `## language` in `story.md` when the section is absent). Edit `settings.ini` before run to switch `en` / `fi`.

After the TTS model loads, the full-screen **Textual TUI** opens. Use **Windows Terminal** (or another modern terminal) on Windows for best rendering.

## 6. Steer the story

Use the **footer input** to type directions for the next segment (Enter to submit). Press **`q`** to quit gracefully, or **Ctrl+C** to shut down.

# Manual test with Gemini

```ini
# settings.ini
[llm]
provider = gemini
model_segment = gemini-2.5-flash
```

```bash
# .env
GEMINI_API_KEY=your-key-here
```

```bash
uv run python -m infinity_audiobook
```

# Tests

```bash
uv run pytest
```

Integration tests use mocked Gemini. Set `GEMINI_API_KEY` for manual playback.
