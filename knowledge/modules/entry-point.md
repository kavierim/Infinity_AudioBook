---
type: Module
title: Entry point
description: main.py — wires pipeline threads, validates assets, and handles graceful shutdown.
tags: [module, main, entry-point]
timestamp: 2026-07-06T12:30:00Z
---

# File

`infinity_audiobook/main.py`

# Responsibilities

1. Parse CLI (`--help`, `--version` only).
2. Load `.env` via `env.load_project_env`.
3. Validate `assets/speaker_reference.wav` and `.txt`.
4. Load [story.md](/configuration/story-state.md) once; load [settings](/configuration/settings.md) via `load_app_settings()` and [playback](/configuration/playback.md) config; load OmniVoice model.
5. Create queues, `Context`, `UISnapshot` (seed transcript from `Last narrated` when present), `StoryLanguageCache`, `TTSEngine`, LLM client, and activity logger.
6. Start [player](player.md); `queue_replay_from_story(story_state=...)` when `Last narrated` exists.
7. Start [audio producer](audio-producer.md) then [text producer](text-producer.md).
8. Run [Textual TUI](/architecture/pipeline.md) on main thread (default).
9. On exit: stop player, join threads.

# Run

```bash
uv run python -m infinity_audiobook
# or: uv run infinity-audiobook
```

Use **Windows Terminal** (or another true-color terminal) for best Textual rendering.

# Test hooks

`run_pipeline()` accepts `skip_tts_load`, `skip_ui`, injectable `ui_runner`, `language`, `llm_config`, `playback_config`, and `story_config` for unit tests.

- `skip_ui=True` — block on `shutdown_event` without launching Textual.
- `ui_runner=...` — inject a mock UI loop (receives `shutdown_event`, `snapshot`, queues, etc.).
