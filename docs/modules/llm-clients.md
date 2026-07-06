---
type: Module
title: LLM clients
description: Gemini tiered client for segment, summary, and arc operations.
tags: [module, llm, gemini]
timestamp: 2026-07-06T09:30:00Z
---

# Factory

`infinity_audiobook/llm_config.py` — `load_llm_config()` + `create_llm_client()`.

| `provider` | Client class |
|---|---|
| `gemini` | `TieredGeminiClient` |

# TieredGeminiClient

`infinity_audiobook/gemini_tiered.py` routes operations:

| Tier | Method | Model key | When |
|---|---|---|---|
| 1 | `generate_segment()` | `model_segment` | Every segment |
| 2 | `summarize_past()` | `model_summary` | `past` > 25 lines |
| 3 | `refresh_story_arc()` | `model_arc` | Every `arc_refresh_every` segments |

Low-level SDK: `gemini_client.py`. Quota handling: `gemini_errors.py`. Prompts: `llm_prompts.py`.

# Fallback segment

When LLM fails (non-quota), a canned lighthouse narration is spoken so playback continues. **story.md is not updated** for fallback segments. Queued fallbacks use negative `segment_id` values (`-1`, `-2`, …) so they do not reuse the next `past` id.

```python
# infinity_audiobook/llm_prompts.py — FALLBACK_SEGMENT
```

Gemini quota/rate-limit errors wait and retry instead of using fallback.

# Tier-1 prompt context

`build_prompt()` in `llm_prompts.py` passes narrative state as:

| Placeholder | Source |
|---|---|
| `{last_narrated}` | Parsed `Last narrated` block from `## current_state` (or `(none)`) |
| `{situation}` | Parsed `Situation` beat (or `(none)`) |
| `{past}` | Last 12 `past` lines |
| `{summary}` | Truncated rolling summary |

JSON response schema is unchanged: `{ segment_text, current_state, future_plan }` where `current_state` is the **Situation** beat only — the `Last narrated` block is written by the text producer, not the LLM.

Tier-3 `build_arc_prompt()` receives `situation_for_prompt()` only (no `Last narrated` prose).

# Debug logging

`llm_debug.py` — when enabled, appends JSON lines to `debug/llm/traffic.jsonl` with `tier` and `model`.

See [debugging playbook](/playbooks/debugging-llm.md).
