---
type: Architecture
title: Rules and constraints
description: Coding rules, token minimization, and compaction strategy for LLM prompts.
tags: [architecture, constraints, tokens]
timestamp: 2026-07-06T09:30:00Z
---

# Coding rules

- No globals without locks; prefer `queue.Queue`.
- Graceful shutdown for `OutputStream`.
- `audio_queue` maxsize = 2.
- Voice cloning only — no OmniVoice `instruct`.
- All code and docs in English.
- **OutputStream callback must never block** on queue I/O or TTS (see [pipeline](pipeline.md)).

# Token usage

Each segment triggers one Gemini tier-1 call. Minimize tokens:

| Technique | Implementation |
|---|---|
| Rolling `summary` | When `past` exceeds 25 lines, fold older lines into `summary` via `summarize_past()` (tier 2 / `model_summary`); keep last 10 in `past` |
| Truncate `past` in prompts | Last 12 lines only (`past_for_prompt`) |
| Cap `summary` in prompts | Max 350 words (`summary_for_prompt`) |
| `Last narrated` in tier-1 prompts | Full spoken prose from structured `## current_state` (~200 words max via `truncate_segment_text`); may overlap newest `past` line — acceptable for restart continuity |
| Tiered Gemini models | Fast model for segments; lighter model for compaction; larger model reserved for arc refresh |
| Compact prompt template | Short JSON schema; omit empty `references` |

Constants are defined in `infinity_audiobook/models.py` — see [data models](data-models.md).

# Compaction

`story_compact.py`: runs after each segment when `past_line_count > 25`. One extra LLM call folds archived lines into `summary`. On failure, `past` is left unchanged.

`summary` + recent `past` + `Last narrated` + `Situation` carry narrative continuity across restarts. See [story.md configuration](/configuration/story-state.md#compaction).
