---
type: Architecture
title: Async pipeline
description: Four-stage pipeline — text generation, TTS, audio buffer, and speaker output.
tags: [architecture, threading, pipeline]
timestamp: 2026-07-06T11:30:00Z
---

# Overview

InfinityAudioBook runs four concurrent stages. Playback never blocks on LLM or TTS work.

```
TUI (main thread)      →  Context (user instructions)
Text Producer (thread) →  text_queue (max 2)
Audio Producer (thread) → audio_queue (max 2)
Player (feeder + callback) → sounddevice OutputStream
```

See also [data models](data-models.md), [text producer](/modules/text-producer.md), [audio producer](/modules/audio-producer.md), [player](/modules/player.md).

# Stages

## Terminal UI (TUI)

Main thread. [Textual](https://textual.textualize.io/) full-screen dashboard — the only user-facing interface.

| Action | Behavior |
|---|---|
| Footer input + Enter | Replace pending story direction (applied on next LLM call) |
| `q` | Graceful shutdown |
| Ctrl+C | Shutdown |

Panels show `story.md` summary, past, and storyline tabs (Arc, **Now** = `Situation` beat only, Plan), plus an in-memory **Transcript** ring with full narrated prose (`Last narrated` on cold start). Pipeline activity and status bar (LLM provider, queue depths, playback buffer, pending direction). `story.md` is re-read on the main thread at most once per second.

Implementation: `infinity_audiobook/ui/`, `infinity_audiobook/context.py`.

## Text Producer

Background thread. Fills [text_queue](data-models.md) when it has fewer than two items.

1. Reload [story.md](/configuration/story-state.md) from disk.
2. Read and clear user instruction from `Context`.
3. Call LLM ([Gemini](/references/gemini-api.md)).
4. On success: append `past`, write structured `current_state` (`Last narrated` + `Situation`) and `future_plan`, run compaction and arc refresh when due.
5. Push `Segment` to `text_queue`.

On startup, when `## current_state` contains a `Last narrated` block, `queue_replay_from_story()` enqueues that segment **before** the first LLM call so TTS can begin immediately.

Pauses when the player buffer exceeds [max_buffer_seconds](/configuration/playback.md).

## Audio Producer

Background thread. Pops `Segment` from `text_queue`, synthesizes via [OmniVoice](/references/omnivoice.md), appends optional segment gap, pushes `AudioChunk` to `audio_queue`.

On TTS failure: log, skip segment, continue.

Language is read via `StoryLanguageCache` (mtime-based invalidation) before each synthesis — picks up language changes without restart, without full `story.md` parse when the file is unchanged.

## Player

Two parts — the **OutputStream callback must never block** on queue I/O or TTS:

1. **Feeder thread** — drains `audio_queue` into a thread-safe playback buffer.
2. **Callback** (audio device thread) — copies `blocksize` samples; pads with silence on underrun.

# Backpressure

| Mechanism | Limit | Purpose |
|---|---|---|
| `text_queue` maxsize | 2 | Cap in-flight segments awaiting TTS |
| `audio_queue` maxsize | 2 | Cap synthesized audio awaiting playback |
| `max_buffer_seconds` | default 300 | Pause LLM/TTS when total prefetch (buffer + queues) reaches cap |

Prefetch accounting (`PrefetchAccounting` in `playback_config.py`) includes the playback buffer, `audio_queue` sample counts, and conservative estimates for `text_queue` segments.

Without buffer cap, API failures can prefetch many minutes of [fallback audio](/modules/llm-clients.md#fallback-segment).

# Shutdown

`q`, Ctrl+C, or SIGTERM sets a shared `shutdown_event`. No new LLM or TTS work starts after that.

| Step | Behavior |
|---|---|
| Shutdown event | Producers stop scheduling new segments |
| Player `stop()` | Feeder thread exits; playback buffer drains up to 2 s while the stream stays open |
| Worker join | `text-producer` and `audio-producer` joined with 5 s timeout each |

**Best-effort:** in-flight LLM or TTS on a worker may finish or be abandoned if join times out. Segments left in `text_queue` / `audio_queue` are not played. Worker threads are daemons; the process can exit without waiting indefinitely.

See [error handling](error-handling.md#graceful-shutdown).

# Startup sequence

1. Load `.env` ([authentication](/playbooks/authentication.md)).
2. Validate `assets/speaker_reference.*`.
3. Read `story.md` once; load [settings.ini](/configuration/settings.md) via `load_app_settings()` (single parse); apply `[story] language` to `story.md` when it differs.
4. Load OmniVoice model (downloads weights on first run).
5. Start player; `queue_replay_from_story()` when `Last narrated` exists (reuses startup `StoryState`); start **audio producer** then **text producer**.
6. Launch Textual TUI on the main thread.
