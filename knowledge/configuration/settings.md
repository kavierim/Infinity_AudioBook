---
type: Configuration
title: settings.ini
description: Gemini LLM model tiers, story language, playback limits, and debug flags.
tags: [configuration, llm, gemini]
timestamp: 2026-07-06T09:00:00Z
---

# Location

Project root: `settings.ini`. Copy from `settings.example.ini` if missing.

When `settings.ini` is absent, defaults apply: `provider = gemini`, playback defaults.

Load all sections in one call via `infinity_audiobook.settings.load_app_settings()`. Individual `load_llm_config`, `load_playback_config`, and `load_story_config` share a single `ConfigParser` read internally.

Legacy `provider = cursor`, `copilot`, or `custom` (including an `[acp]`-only file) fails at startup with a migration error.

# Sections

## `[llm]`

| Key | Default | Description |
|---|---|---|
| `provider` | `gemini` | Must be `gemini` |
| `model` | `gemini-2.5-flash` when empty | Applies to all tiers when tier keys are omitted |
| `model_segment` | falls back to `model` | Tier 1 — every segment |
| `model_summary` | falls back to `model` | Tier 2 — past compaction when `past` > 25 lines |
| `model_arc` | falls back to `model` | Tier 3 — `story_arc` refresh |
| `arc_refresh_every` | `20` | Segments between arc refreshes; `0` = off |
| `debug_traffic` | `false` | Log prompts/responses to `debug/llm/traffic.jsonl` |

When only `model=` is set (no tier keys), that model applies to all three Gemini tiers.

Tier 3 runs when `## story_arc` exists in [story.md](story-state.md) and `arc_refresh_every > 0`.

### Example

```ini
[llm]
provider = gemini
model_segment = gemini-2.5-flash
model_summary = gemini-2.5-flash-lite
model_arc = gemini-2.5-pro
arc_refresh_every = 20
debug_traffic = true
```

Auth: `GEMINI_API_KEY` or `GOOGLE_API_KEY` — see [authentication](/playbooks/authentication.md).

## `[story]`

| Key | Default | Description |
|---|---|---|
| `language` | value from `story.md` | Narration language: `en` or `fi` |

Loaded by `infinity_audiobook/story_config.py`. On startup, if this differs from `## language` in [story.md](story-state.md), the file is updated to match.

There is no interactive language prompt at startup; set `language` here or edit `story.md` directly.

Example:

```ini
[story]
language = fi
```

## `[playback]`

Documented in [playback](playback.md).

# Environment overrides

| Variable | Effect |
|---|---|
| `AUDIOBOOK_DEBUG_LLM=1` | Enable LLM traffic logging regardless of `debug_traffic` |

# Examples

Full examples: `settings.example.ini` in the repo root.
