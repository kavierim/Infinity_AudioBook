---
type: Feature
title: Persist last spoken segment prose
description: Store full narrated segment text in story.md for seamless LLM continuation across restarts.
id: last-spoken-persistence
status: cancelled
category: story-structure
priority: normal
created: 2026-07-06T05:00:00Z
updated: 2026-07-06T09:25:00Z
tags: [story, llm, continuity]
related:
  - /configuration/story-state.md
  - /modules/story-state-module.md
  - /modules/text-producer.md
  - /modules/llm-clients.md
---

# Summary

Persist the **spoken** segment text (after TTS-bound truncation) in `story.md` and include it in tier-1 LLM prompts so the next segment continues from actual narrated prose, not a one-line log entry.

> **Superseded** by [current-state-transcript](/features/current-state-transcript.md) — embed last narrated prose inside `## current_state` instead of a separate `## last_spoken` section.

# Problem

Every segment loses full prose today:

- `past` stores only a one-line `past_append` (first sentence, max 240 chars via `derive_past_append` in `text_producer.py`)
- LLM JSON field `past_append` is parsed (`SegmentResponse`) but **ignored** at write time
- Tier-1 prompts get `summary_for_prompt` + `past_for_prompt` (max 12 one-line entries) — semantic continuity, not exact wording
- Compaction archives older `past` lines into `summary`; only the last 10 one-liners remain

# Requirements

_Cancelled — requirements absorbed by [current-state-transcript](/features/current-state-transcript.md)._

- [x] ~~Add a dedicated section in `story.md` (e.g. `## last_spoken`)~~ → embedded in `## current_state` as `Last narrated (#N):`
- [x] ~~Store `truncate_segment_text` output~~ → same, via `format_current_state`
- [x] ~~Include in tier-1 prompts~~ → `Last narrated:` placeholder in `llm_prompts.py`
- [x] ~~Reload from disk before each segment~~ → unchanged `read_story` loop
- [x] ~~On compaction, keep last spoken intact~~ → compaction never touches `current_state`
- [x] ~~Tests~~ → `test_story_state.py`, `test_llm_prompts.py`, `test_text_producer_fallback.py`
- [x] ~~Update story-state docs~~ → [story-state](/configuration/story-state.md)

# Design

- Prefer `## last_spoken` over folding into `summary` to keep compaction logic unchanged
- Parse and write the new section in [story-state-module](/modules/story-state-module.md)
- [text-producer](/modules/text-producer.md) writes spoken text after successful segment generation

# Out of scope

- Full segment history (only the most recent spoken segment)
- Changing compaction thresholds or `past` log format

# Test plan

- Parse/write round-trip for `## last_spoken` in `story_state` tests
- Prompt assembly includes last spoken text when section is non-empty
- Compaction does not clear or archive `last_spoken`

# Completion

Cancelled 2026-07-06. Shipped as [current-state-transcript](/features/current-state-transcript.md) — `Last narrated` block inside `## current_state` instead of a separate `## last_spoken` section.
