---
type: Module
title: Player
description: Feeder thread plus sounddevice OutputStream callback for gapless playback.
tags: [module, audio, playback]
timestamp: 2026-07-05T07:30:00Z
---

# File

`infinity_audiobook/player.py`

# Design constraint

The **OutputStream callback must never block** on queue I/O, TTS, or LLM work. Only the feeder thread touches `audio_queue`.

# Components

## PlaybackBuffer

Thread-safe sample buffer. Feeder appends; callback reads `blocksize` samples.

## Feeder thread

Pops `AudioChunk` from `audio_queue`, appends samples to buffer.

## OutputStream callback

Copies up to `blocksize` (2048) samples to the output device. Pads with zeros on underrun.

# Parameters

| Parameter | Value |
|---|---|
| `samplerate` | 24000 |
| `channels` | 1 |
| `dtype` | float32 |
| `blocksize` | 2048 |

`buffer.pending_samples()` feeds [backpressure](/architecture/pipeline.md). When wired through `PrefetchAccounting`, queue depths are included in the cap check.
