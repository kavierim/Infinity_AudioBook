---
type: Architecture
title: Data models
description: Segment, AudioChunk, and queue configuration shared across the pipeline.
tags: [architecture, models]
timestamp: 2026-07-05T07:30:00Z
---

# Schema

Defined in `infinity_audiobook/models.py`.

## Segment (`text_queue`)

| Field | Type | Description |
|---|---|---|
| `text` | `str` | Spoken narration (target 80–150 words, hard cap 200) |
| `segment_id` | `int` | Monotonic id from `past` lines (`#N`); negative ids for fallback segments only |

## AudioChunk (`audio_queue`)

| Field | Type | Description |
|---|---|---|
| `audio` | `np.ndarray` | Mono `float32`, 24 kHz |
| `segment_id` | `int` | Matches source segment |

## Constants

| Constant | Value | Purpose |
|---|---|---|
| `SAMPLE_RATE` | 24000 | OmniVoice output and playback |
| `BLOCKSIZE` | 2048 | ~85 ms per callback block |
| `TEXT_QUEUE_MAXSIZE` | 2 | Text prefetch limit |
| `AUDIO_QUEUE_MAXSIZE` | 2 | Audio prefetch limit |
| `MAX_SEGMENT_WORDS` | 200 | Truncate at sentence boundary |
| `PROMPT_PAST_MAX_LINES` | 12 | Past lines in LLM prompt |
| `PAST_ARCHIVE_THRESHOLD` | 25 | Trigger compaction |
| `PAST_KEEP_AFTER_ARCHIVE` | 10 | Past lines kept after compaction |
| `SUMMARY_MAX_WORDS` | 350 | Summary cap in prompts |

See [pipeline](pipeline.md) for how queues connect stages.
