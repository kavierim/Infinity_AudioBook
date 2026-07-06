---
type: Feature
title: Gemini TTS provider
description: Cloud TTS alternative to OmniVoice via Gemini speech generation API.
id: gemini-tts
status: specced
category: tts-providers
priority: normal
created: 2026-07-06T05:00:00Z
updated: 2026-07-06T05:00:00Z
tags: [tts, gemini]
related:
  - /modules/tts.md
  - /modules/audio-producer.md
  - /references/gemini-api.md
  - /configuration/settings.md
---

# Summary

Add Google AI Studio Gemini TTS as an alternative to local OmniVoice voice cloning. Preset cloud voices and style control replace `assets/speaker_reference.*` when selected.

# Problem

Today TTS is OmniVoice-only: local GPU, Hugging Face model load, and bundled speaker reference. Users who already run the Gemini LLM stack may prefer a cloud TTS path with no CUDA requirement.

# Requirements

- [ ] Implement `GeminiTTSEngine` behind the existing `Synthesizer` protocol in [audio-producer](/modules/audio-producer.md)
- [ ] Primary model: `gemini-3.1-flash-tts-preview` (supports streaming)
- [ ] Fallback: `gemini-2.5-flash-preview-tts` if 3.1 is unavailable in region or quota
- [ ] Use Gemini API [speech generation](https://ai.google.dev/gemini-api/docs/interactions/speech-generation) (text → audio), **not** Live API
- [ ] Add `[tts]` section to `settings.ini` (`provider = gemini`, `model`, `voice` / `speech_config`)
- [ ] Reuse `GEMINI_API_KEY` / `GOOGLE_API_KEY` (same key as LLM provider)
- [ ] Map `narrator_tone` from [story.md](/configuration/story-state.md) into style / pacing hints in `speech_config`
- [ ] Decode API audio to mono `float32` at 24 kHz; resample if needed for [player](/modules/player.md)
- [ ] Skip `speaker_reference.*` and local GPU / Hugging Face model load when Gemini TTS is selected
- [ ] Mock API in tests; document preview status, quotas, and billing
- [ ] Update `README.md` and related OKF concepts on completion

# Design

- Trade-off: cloud preset voices + style control vs. local OmniVoice voice cloning from `assets/`
- Wire provider selection in startup alongside existing OmniVoice path ([tts](/modules/tts.md))
- Optional later (out of scope for v1): streaming TTS (3.1) to reduce time-to-first-audio

# Out of scope

- Gemini Live API (bidirectional real-time voice)
- Streaming TTS in the first implementation
- Voice cloning in the cloud path

# Test plan

- Unit tests with mocked Gemini TTS HTTP/SDK responses
- Manual smoke: one segment playback with `provider = gemini` in `settings.ini`
- Verify OmniVoice path unchanged when `provider` is not `gemini`

# Completion

_Not yet shipped._
