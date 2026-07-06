---
type: Configuration
title: story.md
description: Single source of truth for narrative state — read before every segment, updated after each success.
tags: [configuration, story, narrative]
timestamp: 2026-07-06T11:05:00Z
---

# Overview

`story.md` at project root holds all narrative state. The text producer reloads it from disk before every LLM call (manual edits are picked up immediately).

# Sections

Each section uses `## heading` followed by free-form markdown body.

| Section | Updated by | Purpose |
|---|---|---|
| `title`, `genre`, `perspective`, `language` | User | Metadata (`language`: `en` or `fi`) |
| `narrator_tone` | User | Prose style for LLM (not TTS voice) |
| `story_arc` | LLM tier 3 + user | Long-form through-line; enables arc refresh |
| `summary` | LLM compaction | Compressed older history |
| `past` | LLM + user | Chronological event log |
| `current_state` | LLM + writer | Last narrated prose + situation beat (see below) |
| `future_plan` | LLM + user | Planned beats ahead |
| `references` | User | URLs and local files (non-fiction) |

Add `## story_arc` to enable tier-3 refresh every `arc_refresh_every` segments (see [settings](settings.md)).

# Read / write rules

- **Read:** Before each LLM call, reload `story.md` from disk (picks up manual edits).
- **Write:** After a successful segment:
  - **Append** to `past`: `- [{ISO8601}] #{segment_id}: {past_append}` where `past_append` is derived from the first sentence of `segment_text` (not a separate LLM field).
  - **Segment id:** monotonic `#N` parsed from existing `past` lines (survives restarts).
  - **Replace** `current_state` with structured body: `Last narrated (#N):` (spoken text after `truncate_segment_text`) + `Situation:` (LLM `current_state` JSON field — brief beat only).
  - **Replace** `future_plan` with LLM output.
  - **Replace** `story_arc` when tier 3 runs (`refresh_story_arc()` every `arc_refresh_every` successful segments, only when `## story_arc` exists in `story.md`).
- **Lock:** File lock (`threading.Lock` + atomic write via temp file rename).

Failed LLM calls use a fallback segment and **do not** update `story.md`.

# User instruction semantics

- Terminal input **replaces** the previous unconsumed instruction.
- Included in the next successful LLM call as `user_direction`.
- Cleared only after a **successful** segment generation (not on fallback or Gemini quota/service retry).
- Does not flush queues; affects only future LLM calls.

# Cold start

When `past` is empty or contains only `*(no events yet)*`, the opening segment is generated from the `Situation` beat in `current_state` + `future_plan` (no `Last narrated` block yet).

# current_state format

Structured layout (machine labels in English; prose in story language):

```markdown
## current_state

Last narrated (#112):

Full spoken segment text (truncate_segment_text output)…

Situation:

Brief situational beat returned by the LLM.
```

- On cold start / before the first successful segment, omit the `Last narrated` block; `Situation` holds the opening beat.
- Legacy plain-text `current_state` bodies parse as `Situation` only (`last_narrated` empty).
- Malformed structured bodies (e.g. `Last narrated (#N):` without a `Situation:` label) degrade safely: prose after the label is kept in `last_narrated`, `situation` may be empty until the next successful segment rewrite.
- **Upgrade gap:** after upgrading on a story with existing `past` lines, restart continuity uses `summary` + `past` + `Situation` until one new segment rewrites `current_state` with `Last narrated`.
- Compaction updates `summary` and `past` only — does not rewrite `current_state`.

# Restart / resume

When `## current_state` contains a `Last narrated (#N):` block after a prior session:

| Consumer | What it reads |
|---|---|
| **TTS on startup** | `queue_replay_from_story()` enqueues the spoken text to `text_queue` before the first LLM call — playback resumes without waiting for a new segment |
| **TUI Transcript** | `UISnapshot.seed_transcript()` shows the same prose in the transcript panel |
| **TUI Storyline → Now** | `situation_for_prompt()` — **Situation** beat only (narration is in Transcript) |
| **Tier-1 LLM** | `last_narrated` + `situation` as separate prompt fields |
| **Tier-3 arc** | `situation` only |

Replay does **not** append to `past` or rewrite `current_state`. The next successful LLM segment uses the next monotonic `#N` from `past`.

# Compaction

When `past` exceeds 25 lines, tier 2 folds older lines into `summary` (keeps last 10 in `past`). One extra LLM call. On failure, `past` is unchanged.

# References (non-fiction)

```markdown
## references

- [Chapter notes](./sources/chapter-01.md)
- https://example.com/article
```

`reference_sources.py` inlines plain-text and markdown files under `sources/` up to **8 KB** per file. Binary files are listed by path only.

# Language

Set at startup (`en` / `fi`) or in `## language`. Drives LLM prompts and [TTS language](/modules/tts.md). The bundled speaker reference WAV is English; Finnish narration works but the clone timbre stays English.
