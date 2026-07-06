---
type: Module
title: Text producer
description: Background thread that generates story segments via LLM and updates story.md.
tags: [module, llm, text-producer]
timestamp: 2026-07-06T11:30:00Z
---

# File

`infinity_audiobook/text_producer.py`

# Key functions

| Function | Purpose |
|---|---|
| `queue_replay_from_story(...)` | Enqueue `Last narrated` at startup; optional `story_state` avoids redundant disk read |
| `text_producer_loop(...)` | Background LLM loop |
| `run_text_producer(...)` | Start the text-producer thread |

# Loop

Runs while shutdown event is not set:

1. Wait if `text_queue` is full (max 2) or player buffer exceeds [max_buffer_seconds](/configuration/playback.md).
2. `read_story(story_path)` — fresh from disk.
3. `current_state_for_tier1_prompt(state.current_state)` — split `Last narrated` prose and `Situation` beat for the LLM.
4. `context.peek_instruction()` — user direction (cleared only after success).
5. `expand_references_for_prompt()` — inline `sources/` files.
6. `llm_client.generate_segment(...)` with `last_narrated`, `situation`, truncated `past`, and `summary`.
7. On [Gemini quota](/playbooks/debugging-llm.md): wait and retry (no fallback).
8. On other errors: use [fallback segment](llm-clients.md#fallback-segment).
9. On success: `format_current_state(spoken_text, segment_id, response.current_state)` → `write_story_updates`, `maybe_compact_story`, `maybe_refresh_story_arc`.
10. `text_queue.put(Segment(...))`.

# LLM client

| Provider | Client | Compaction | Arc refresh |
|---|---|---|---|
| `gemini` | `TieredGeminiClient` | tier 2 model | tier 3 model |

See [LLM clients](llm-clients.md).

# Prompt limits

Applied before LLM call (from `models.py`):

- `past`: last 12 lines
- `summary`: max 350 words
- `story_arc`: included when non-empty
- `current_state`: parsed into `last_narrated` (full spoken prose from disk) + `situation` (brief beat) — see [story.md](/configuration/story-state.md#current_state-format)

On write, `current_state` is replaced with a structured body: `Last narrated (#N):` + `Situation:` (LLM JSON `current_state` field maps to `Situation` only).

`queue_replay_from_story(story_state=...)` enqueues the `Last narrated` segment at startup so TTS begins before the first LLM call. `main.py` passes the already-loaded `StoryState`.
