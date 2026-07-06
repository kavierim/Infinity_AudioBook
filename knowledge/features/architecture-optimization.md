---
type: Feature
title: Architecture optimization
description: Reduce redundant I/O, unify settings loading, and clarify pipeline startup wiring.
id: architecture-optimization
status: done
category: pipeline
priority: normal
created: 2026-07-06T09:00:00Z
updated: 2026-07-06T12:30:00Z
completed: 2026-07-06
tags: [architecture, pipeline, settings, story-state]
related:
  - /modules/entry-point.md
  - /modules/story-state-module.md
  - /modules/audio-producer.md
  - /architecture/pipeline.md
  - /architecture/project-structure.md
  - /configuration/settings.md
---

# Summary

Focused architecture cleanup after Gemini-only migration: load `settings.ini` once at startup, eliminate redundant `story.md` reads during pipeline boot, and cache story language for the audio producer hot path. No TTS or LLM behavior changes.

# Problem

| Area | Pain |
|---|---|
| **Config loading** | `load_llm_config`, `load_playback_config`, and `load_story_config` each open and parse `settings.ini` independently — three disk reads and three `ConfigParser` instances on every startup. |
| **Startup story reads** | `main.run_pipeline` called `read_story` up to four times before workers start (language, snapshot seed, TTS language, replay queue). |
| **Audio producer** | `audio_producer_loop` called `read_story(story_path)` before every TTS synthesis to pick up language changes — full parse on a hot path even when `story.md` is unchanged. |

# Requirements

## Code

- [x] Add `load_app_settings()` that reads `settings.ini` once and returns LLM, playback, and story config together.
- [x] Refactor existing `load_*_config` functions to share a single `ConfigParser` read helper (backward-compatible public APIs).
- [x] Consolidate startup `story.md` reads in `main.run_pipeline` to a single `read_story` call; pass `StoryState` to replay seed and snapshot.
- [x] Add mtime-based `StoryLanguageCache` in `story_state.py`; wire it into `audio_producer` so language updates are picked up without full parse on every segment when the file is unchanged.
- [x] `queue_replay_from_story` accepts optional pre-loaded `StoryState` to avoid a redundant disk read.

## Configuration

- [x] No `settings.ini` schema changes.

## Documentation

- [x] Update related OKF concepts listed in `related:` frontmatter
- [x] Update `README.md` if user-facing behavior or quick start changes
- [x] Update `AGENTS.md` if agent workflow or constraints change
- [x] Append [log.md](/log.md) on ship

## Tests

- [x] `uv run pytest` passes
- [x] Tests for `load_app_settings` (single-file, missing file, all sections)
- [x] Tests for `StoryLanguageCache` (cache hit, mtime invalidation)
- [x] Test that `queue_replay_from_story` works with pre-loaded state

# Design

## Before

```
main.run_pipeline:
  read_story ×3–4
  load_llm_config(settings.ini)     → ConfigParser #1
  load_playback_config(settings.ini) → ConfigParser #2
  load_story_config(settings.ini)    → ConfigParser #3

audio_producer_loop (per segment):
  read_story(story_path).language   → full parse every time
```

## After

```
main.run_pipeline:
  story_state = read_story(story_path)   # once
  app_settings = load_app_settings(...)  # one ConfigParser read
  StoryLanguageCache(story_path) → audio producer

audio_producer_loop (per segment):
  language_cache.get()  → full parse only when mtime changes
```

### `settings.py`

New module with `AppSettings` dataclass (`llm`, `playback`, `story`) and `read_settings_parser(path)` shared by individual loaders. `main.py` calls `load_app_settings` when any config section is not injected.

### `StoryLanguageCache`

Thread-safe; compares `path.stat().st_mtime` before calling `read_story`. Preserves live language-change behavior without per-segment parse when file is stable.

### Pipeline constraints (unchanged)

- `text_queue` / `audio_queue` maxsize = 2
- OutputStream callback never blocks on queue I/O or TTS
- TTS synthesis path untouched (`tts.py`, `audio_producer` synthesize call)

# Out of scope

- TTS / OmniVoice changes (`tts.py`, synthesis logic)
- Gemini TTS provider
- New features (UI panels, new LLM tiers)
- Full `Pipeline` class / dependency-injection framework refactor
- Caching `story.md` for text producer or TUI (different consistency needs)
- Removing `LEGACY_LLM_PROVIDERS` rejection (still needed for migration)

# Test plan

1. `uv run pytest` — all existing tests plus new settings/cache tests.
2. Manual smoke (optional): start app, verify TUI panels and TTS language still work after editing `## language` in `story.md`.

# Completion

Shipped 2026-07-06. Added `settings.py` (`load_app_settings`, shared `read_settings_parser`); `load_*_config_from_parser` in llm/playback/story config modules; `StoryLanguageCache` in `story_state.py`; consolidated startup reads in `main.py`; `queue_replay_from_story(story_state=...)`; audio producer uses language cache. Tests: `test_settings.py`, `test_story_language_cache.py`. Docs: [pipeline](/architecture/pipeline.md), [project-structure](/architecture/project-structure.md), [entry-point](/modules/entry-point.md), [audio-producer](/modules/audio-producer.md), [story-state](/modules/story-state-module.md), [settings](/configuration/settings.md). Breaking: no.
