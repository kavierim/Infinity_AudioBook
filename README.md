# InfinityAudioBook

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

An infinite audiobook player that generates story segments on the fly while audio keeps playing. An LLM writes the next chapter; [OmniVoice](https://pypi.org/project/omnivoice/) narrates it with voice cloning. You steer the story from the terminal without stopping playback.

**Author:** [Kari Vierimaa](https://github.com/kavierim) ([@kavierim](https://github.com/kavierim))

**Platform:** Windows (CUDA 12.8) primary; Python is cross-platform.

## Features

- Seamless four-stage pipeline (LLM → TTS → buffer → speaker)
- Living `story.md` state updated after each segment; **resume on restart** replays the last narrated segment while the LLM writes the next
- Live story direction from the terminal (Textual TUI)
- Voice cloning from a short reference clip
- Gemini LLM with three model tiers (segment, summary, arc)
- English and Finnish story language (`en` / `fi`)

## Requirements

| Component | Notes |
|---|---|
| Python 3.10+ | |
| [uv](https://docs.astral.sh/uv/) | Required package manager |
| NVIDIA GPU | Practical TTS; CUDA 12.8 on Windows |
| LLM auth | `GEMINI_API_KEY` or `GOOGLE_API_KEY` — see [authentication](knowledge/playbooks/authentication.md) |

## Quick start

```bash
git clone https://github.com/kavierim/AudioBook.git
cd AudioBook
uv sync
```

Copy configuration templates (pick your shell):

```bash
# Linux / macOS / Git Bash
cp settings.example.ini settings.ini
cp .env.example .env
```

```powershell
# Windows PowerShell
Copy-Item settings.example.ini settings.ini
Copy-Item .env.example .env
```

1. Edit `story.md` (`title`, `current_state` Situation beat, `future_plan`) before the first run.
2. Add your Gemini API key to `.env` (`GEMINI_API_KEY` or `GOOGLE_API_KEY`).
3. Run the player:

```bash
uv run python -m infinity_audiobook
```

At startup, the TTS model loads, then the full-screen TUI opens.

**Terminal:** use the footer input for story directions; press `q` to quit. Requires a modern terminal (Windows Terminal recommended on Windows).

## Configuration

| File | Purpose |
|---|---|
| [settings.example.ini](settings.example.ini) | LLM tiers, story language, playback limits — copy to `settings.ini` |
| [.env.example](.env.example) | API keys — copy to `.env` (do not commit) |
| [story.md](story.md) | Living narrative state (title, beats, arc) |

See [settings documentation](knowledge/configuration/settings.md) and [story state](knowledge/configuration/story-state.md) for details.

## Documentation

| Document | Purpose |
|---|---|
| [knowledge/](knowledge/index.md) | **OKF knowledge bundle** — architecture, config, modules, [features](knowledge/features/index.md), playbooks |
| [TODO.md](TODO.md) | Backlog index (links to feature specs) |
| [AGENTS.md](AGENTS.md) | Agent coding instructions |

## Development

```bash
uv run pytest
```

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 [Kari Vierimaa](https://github.com/kavierim).
