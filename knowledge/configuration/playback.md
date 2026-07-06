---
type: Configuration
title: Playback settings
description: Segment gap silence and player buffer cap that pauses LLM/TTS prefetch.
tags: [configuration, playback, audio]
timestamp: 2026-07-05T07:30:00Z
---

# settings.ini

```ini
[playback]
segment_gap_seconds = 1.0    # trailing silence after each segment (0 = off)
max_buffer_seconds = 300     # pause prefetch when buffer exceeds this (0 = unlimited)
```

Loaded by `infinity_audiobook/playback_config.py`. Missing `[playback]` section uses defaults.

# segment_gap_seconds

Appended in `audio_producer.py` after each synthesized segment. Gives a natural pause between narrated chunks.

# max_buffer_seconds

Both [text producer](/modules/text-producer.md) and [audio producer](/modules/audio-producer.md) check total prefetched audio before producing more content.

`PrefetchAccounting` sums:

1. Samples in the playback buffer (`PlaybackBuffer.pending_samples()`).
2. Actual samples in `audio_queue` (each `AudioChunk`).
3. Estimated samples for segments still in `text_queue` (~150 words/minute plus segment gap).

Estimates are conservative so the cap is not exceeded by queued prefetch. `max_buffer_seconds = 0` disables the limit.

Prevents runaway prefetch when the LLM is failing (e.g. API quota) — without this cap the buffer can grow to tens of minutes of fallback narration.

Default: **300 seconds** (5 minutes).

# Audio parameters

| Parameter | Value |
|---|---|
| Sample rate | 24000 Hz |
| Channels | 1 (mono) |
| dtype | float32 |
| blocksize | 2048 (~85 ms) |
| Underrun | Silence in callback |

See [player](/modules/player.md) and [pipeline](/architecture/pipeline.md).
