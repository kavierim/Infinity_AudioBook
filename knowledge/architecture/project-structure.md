---
type: Architecture
title: Project structure
description: Repository layout — Python package, assets, configuration, and documentation.
tags: [architecture, structure]
timestamp: 2026-07-06T09:30:00Z
---

# Layout

```
infinity_audiobook/
  __init__.py
  main.py
  models.py
  context.py           # in-memory instruction state
  story_state.py       # read/write story.md
  story_compact.py     # past → summary compaction
  story_arc.py         # tier-3 arc refresh
  reference_sources.py # inline sources/ files into prompts
  ui/
    snapshot.py        # thread-safe transcript ring
    activity.py        # activity ring + logging handler
    app.py             # Textual dashboard
  text_producer.py
  audio_producer.py
  player.py
  gemini_client.py
  gemini_tiered.py
  gemini_errors.py
  llm_config.py
  llm_prompts.py
  llm_debug.py
  settings_paths.py
  settings.py          # unified settings.ini loader
  playback_config.py
  story_config.py
  env.py
  tts.py
tests/
assets/
  speaker_reference.wav   # narrator voice clone (see TTS module)
  speaker_reference.txt   # transcript of speaker_reference.wav (required)
story.md                  # living story state
settings.ini              # Gemini LLM and playback settings
settings.example.ini      # configuration examples
sources/                  # optional; referenced from story.md (non-fiction)
knowledge/                # OKF documentation bundle
  features/               # implementation specs (type: Feature)
LICENSE                   # MIT
```

# Run

```bash
uv run python -m infinity_audiobook
```

# Module map

See [modules index](/modules/index.md) for per-file responsibilities.

# Feature specs

See [features index](/features/index.md) for implementation specs and delivery history.
