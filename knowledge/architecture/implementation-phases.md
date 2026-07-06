---
type: Architecture
title: Implementation phases
description: Ordered build phases for agents and developers — each phase must pass tests before the next.
tags: [architecture, implementation, phases]
timestamp: 2026-07-06T09:30:00Z
---

# Build order

Implement in order. Each phase must pass its tests before the next.

| Phase | Deliverable | External deps |
|---|---|---|
| 1 | `pyproject.toml`, pipeline skeleton, mocks | none |
| 2 | `player.py` + audio tests | sounddevice |
| 3 | `story_state.py` + tests | none |
| 4 | Gemini LLM client + tests | `GEMINI_API_KEY` or `GOOGLE_API_KEY` |
| 5 | `tts.py` + integration | CUDA, Hugging Face model |
| 6 | End-to-end polish | all |

**Do not** run real OmniVoice or Gemini in unit tests — mock both until phase 5/6.

# Phase checklist (detail)

1. **Pipeline skeleton** — Threads, queues, simulated delays.
2. **Seamless playback** — `OutputStream` + callback, test tones.
3. **Story state** — `story_state.py`: parse, read, write, lock `story.md`.
4. **Gemini integration** — Tiered client, prompt, JSON parse, state writeback.
5. **OmniVoice** — Voice cloning with bundled `speaker_reference.*`; wire to audio producer.
6. **Polish** — Textual TUI, segment gaps, reference file loading for non-fiction.

See [testing playbook](/playbooks/testing.md) for TDD scope per module.
