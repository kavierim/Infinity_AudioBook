---
type: Feature
title: Terminal UI (TUI)
description: Textual full-screen dashboard — the only user-facing interface.
id: tui
status: done
category: polish
priority: normal
created: 2026-07-06T05:30:00Z
updated: 2026-07-06T11:05:00Z
tags: [ui, terminal, textual]
related:
  - /architecture/pipeline.md
  - /configuration/story-state.md
  - /modules/entry-point.md
  - /features/current-state-transcript.md
---

# Summary

Replace the line-oriented `input()` command center with a **Textual** full-screen TUI as the only user-facing interface. The old `status` / `stop` / `> ` prompt is removed. Non-TUI entry points are limited to `--help` / `--version` (argparse) and test-only `skip_ui` / injectable `ui_runner` hooks on `run_pipeline()`.

# Problem

The former command center (`command_center.py`, removed) blocked on `input()`, printed truncated 120-character previews via the `status` command, and interleaved `logging` output with user input. Long listening sessions need a persistent dashboard: full summary, storyline, transcript, and pipeline activity visible while audio plays.

# Requirements

## Entry point

- [x] Add `argparse` to `main()` with `--help` and `--version`; no other user-facing CLI flags
- [x] Default run (`uv run infinity-audiobook`) always starts the Textual TUI on the main thread
- [x] `run_pipeline(skip_ui=True)` blocks on `shutdown_event` without launching Textual (tests only)
- [x] `run_pipeline(ui_runner=...)` allows injecting a mock UI loop (tests only)
- [x] Remove `command_center_loop`, `print_status`, and the `status` / `stop` text commands

## Layout

- [x] **Summary** — full `## summary` from `story.md` (scrollable)
- [x] **Storyline** — `## story_arc`, `Situation` beat from `## current_state` (Now tab), `## future_plan` (tabs or sub-panels)
- [x] **Past** — `## past` chronological log (scrollable)
- [x] **Transcript** — last N segment texts with `#segment_id` (in-memory ring buffer, N ≥ 5)
- [x] **Activity log** — pipeline events always visible (not gated on `debug_traffic`)
- [x] **Status bar** — LLM provider summary, text/audio queue depth, playback buffer seconds, pending instruction
- [x] **Input footer** — Enter submits story direction (`Context.set_instruction`, replace semantics per [story-state](/configuration/story-state.md))
- [x] **Quit** — `q` or `Ctrl+C` sets `shutdown_event` and exits gracefully

## Data flow

- [x] Thread-safe `UISnapshot` updated from producer threads (segment queued, synthesis started, audio queued)
- [x] TUI reads `story.md` at most once per second on the main thread (not from worker threads)
- [x] Extend `PipelineActivityLogger` (or companion `UIActivitySink`) to append to a fixed-size ring buffer for the activity panel
- [x] When TUI is active, route `logging` WARNING+ to the activity panel (no stdout interleaving)

## Constraints

- [x] Never block the [player](/modules/player.md) OutputStream callback or add queue I/O in the audio callback
- [x] UI is read-only except `Context.set_instruction` — no pipeline semantic changes
- [x] Windows-compatible (Windows Terminal recommended; document minimum terminal requirements)

## Dependencies and docs

- [x] Add `textual` via `uv add textual`
- [x] New package `infinity_audiobook/ui/` (`snapshot.py`, `activity.py`, `app.py`)
- [x] Remove `command_center.py`; migrate any reusable logic into `ui/`
- [x] Update [pipeline](/architecture/pipeline.md), [entry-point](/modules/entry-point.md), [project structure](/architecture/project-structure.md), and `README.md` on completion
- [x] Update `tests/test_main.py` and replace `tests/test_command_center.py` with snapshot/UI tests

# Design

## Library

[Textual](https://textual.textualize.io/) — full-screen layout, scrollable panels, footer input, `call_from_thread` for safe updates from producer threads.

## Architecture

```
Main thread (Textual App)
  ├── periodic timer (≤1 Hz) → read story.md + refresh panels
  ├── footer Input → Context.set_instruction
  └── quit (q / Ctrl+C) → shutdown_event

text_producer / audio_producer → UISnapshot (lock) ← segment + activity events
```

`main.py` wires the pipeline, then calls `run_tui_app(snapshot, context, shutdown_event, ...)`.

## Module layout

```
infinity_audiobook/ui/
  snapshot.py   # thread-safe UISnapshot, transcript ring, metrics
  activity.py   # PipelineActivityLogger → activity ring buffer
  app.py        # Textual App, layout, timers, key bindings
```

## Transcript vs Now

| Panel | Content | Source |
|---|---|---|
| **Storyline → Now** | Brief `Situation` beat | `situation_for_prompt(state.current_state)` |
| **Transcript** | Full spoken segment text with `#N` | `UISnapshot` ring; seeded from `Last narrated` on cold start |

## Transcript source

Ring buffer populated when a segment is queued to `text_queue` (truncated spoken text from `truncate_segment_text`). On cold start, `main.py` calls `UISnapshot.seed_transcript()` with the `Last narrated` block from `## current_state` (one entry) until live segments fill the ring. The same prose is also enqueued for immediate TTS via `queue_replay_from_story()` — see [pipeline startup](/architecture/pipeline.md#startup-sequence).

## Removed

- `command_center.py` (`command_center_loop`, `print_status`)
- User-facing `status` / `stop` commands and the `> ` prompt
- `[ui] mode` setting — not needed (TUI-only)

## v2 (optional, out of v1 scope)

- Player reports `now_playing_segment_id` for highlight in the transcript panel
- Tab key bindings between panels

# Out of scope

- Plain / line-oriented terminal mode for end users
- Editing `story.md` sections in the TUI (disk edits are picked up on the next reload)
- Web or GUI
- Mouse features beyond Textual defaults
- Replacing `debug/llm/traffic.jsonl` file logging

# Test plan

- Unit tests for `UISnapshot` ring buffers and thread-safe updates (no Textual import required)
- `test_main.py`: `skip_ui=True` or mocked `ui_runner`; pipeline start/stop behavior unchanged
- Manual smoke: full session in Windows Terminal; panels update during generation/playback; direction input affects the next segment; graceful quit per [error-handling](/architecture/error-handling.md)

# Completion

Shipped 2026-07-06. Textual TUI is the sole user-facing interface (`infinity_audiobook/ui/`). `command_center.py` removed. `run_pipeline()` supports `skip_ui` and `ui_runner` for tests. Activity and WARNING+ logs route to the TUI activity panel; `story.md` panels refresh at 1 Hz on the main thread. **Now** tab shows `Situation` only; **Transcript** holds `Last narrated` prose.
