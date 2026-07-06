---
type: Feature
title: Playback backpressure accounting
description: Count queued audio when enforcing max_buffer_seconds cap.
id: playback-backpressure
status: done
category: pipeline-robustness
created: 2026-07-05T20:00:00Z
updated: 2026-07-05T22:00:00Z
completed: 2026-07-05
tags: [playback, pipeline]
related:
  - /configuration/playback.md
  - /architecture/pipeline.md
---

# Summary

Tighten backpressure so prefetched audio in `text_queue` / `audio_queue` counts toward the buffer limit.

# Completion

- **Shipped:** 2026-07-05
- **Summary:** `buffer_below_limit()` now accounts for samples still in producer queues, not only `PlaybackBuffer.pending_samples()`.
- **Docs updated:** [playback](/configuration/playback.md), [pipeline](/architecture/pipeline.md)
