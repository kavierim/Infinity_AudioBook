---
type: Architecture
title: Error handling
description: Failure modes and recovery behavior across LLM, TTS, story state, and shutdown.
tags: [architecture, errors, resilience]
timestamp: 2026-07-06T09:30:00Z
---

# Failure matrix

| Failure | Behavior |
|---|---|
| Gemini API error (non-quota) | Log; fallback segment |
| JSON parse error | Retry with stricter prompt |
| TTS error | Log, skip segment |
| `story.md` write error | Log, continue playback; retry write next segment |
| Missing or empty reference assets | Exit at startup (see [TTS module](/modules/tts.md)) |
| `q` / Ctrl+C | Shutdown event; close stream |

# Fallback segment

When LLM fails (non-quota), a canned narration is spoken so playback continues. **story.md is not updated** for fallback segments. Fallback chunks use **negative** `segment_id` values (`-1`, `-2`, …) so they do not collide with monotonic `#N` ids in `past`. User directions are **preserved** until a successful LLM segment (not cleared on fallback or Gemini quota wait).

See [LLM clients](/modules/llm-clients.md#fallback-segment).

Gemini quota/rate-limit errors wait and retry instead of using fallback. User directions remain in `Context` across quota/service retries.

# Graceful shutdown

`q`, Ctrl+C, or SIGTERM sets a shared `shutdown_event`. Cleanup order in `main.py`:

1. **Stop scheduling** — producers see the event and exit their loops.
2. **Player** — feeder thread joins (2 s max); playback buffer may drain for up to 2 s while the `OutputStream` callback still runs; then the stream closes.
3. **Worker threads** — `text-producer` and `audio-producer` joined (5 s timeout each). A warning is logged if either thread is still alive.

**Not guaranteed:**

- An in-flight `generate_segment` or `synthesize` call may complete or be cut off at join timeout.
- Queued `Segment` / `AudioChunk` items are discarded, not flushed to the speaker.
- Daemon threads do not block process exit if joins time out.

This is intentional minimal shutdown — enough for normal `q` / Ctrl+C without blocking the audio callback or waiting indefinitely on cloud APIs.

See [pipeline](pipeline.md#shutdown).
