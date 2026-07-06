---
type: Feature
title: Segment gap pause
description: Configurable silence between narrated segments.
id: segment-gap
status: done
category: polish
created: 2026-07-05T08:00:00Z
updated: 2026-07-05T12:00:00Z
completed: 2026-07-05
tags: [playback, audio]
related:
  - /configuration/playback.md
  - /modules/audio-producer.md
---

# Summary

Append trailing silence after each TTS chunk so segments breathe between narrations.

# Completion

- **Shipped:** 2026-07-05
- **Summary:** `append_segment_gap` in `audio_producer.py`. `[playback] segment_gap_seconds` in `settings.ini` (default 1.0 s; `0` = off).
- **Docs updated:** [playback](/configuration/playback.md)
