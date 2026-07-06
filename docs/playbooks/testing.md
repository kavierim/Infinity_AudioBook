---
type: Playbook
title: Testing
description: Test-driven development scope — what to mock, what to test per module.
tags: [playbook, testing, pytest, tdd]
timestamp: 2026-07-06T09:30:00Z
---

# Run

```bash
uv run pytest
```

# Scope (TDD)

| Area | Tests |
|---|---|
| `story_state.py` | Parse sections, `parse_current_state` / `format_current_state`, `last_narrated_for_replay`, append `past`, replace structured `current_state`/`future_plan`, file lock |
| `text_producer.py` | `queue_replay_from_story`, LLM loop |
| `llm_prompts.py` | `Last narrated` + `Situation` prompt assembly |
| `ui/snapshot.py` | Transcript ring, cold-start seed from disk |
| `ui/app.py` | TUI **Now** panel uses `situation_for_prompt` only |
| Instructions | Replace semantics in `Context` |
| Pipeline | Queue backpressure, player underrun, graceful shutdown |
| Mocks | `OmniVoice.generate` / `create_voice_clone_prompt`, Gemini SDK |

# Integration tests

- Gemini tests are mocked in unit tests.
- Do not run real OmniVoice or Gemini in unit tests until phase 5/6 of [implementation phases](/architecture/implementation-phases.md).

# Test hooks

`main.run_pipeline()` accepts `skip_tts_load`, `skip_ui`, and injectable configs. See [entry point](/modules/entry-point.md).
