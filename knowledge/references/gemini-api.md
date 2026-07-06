---
type: Reference
title: Gemini API
description: Google AI Studio generateContent client with three model tiers for segment, summary, and arc.
resource: https://aistudio.google.com/
tags: [reference, llm, gemini]
timestamp: 2026-07-05T07:30:00Z
---

# Stack

| Component | Package / module |
|---|---|
| SDK | `google-genai>=2.10.0` |
| Low-level client | `infinity_audiobook/gemini_client.py` |
| Tier router | `infinity_audiobook/gemini_tiered.py` |
| Errors | `infinity_audiobook/gemini_errors.py` |

# API

- `generateContent` with `response_mime_type: application/json`
- Stateless per call (no chat session)
- Auth: `GEMINI_API_KEY` or `GOOGLE_API_KEY`

# Default models

| Tier | Setting key | Default when unset |
|---|---|---|
| 1 segment | `model_segment` | `gemini-2.5-flash` |
| 2 summary | `model_summary` | `gemini-2.5-flash` |
| 3 arc | `model_arc` | `gemini-2.5-flash` |

Configure per-tier models in [settings.ini](/configuration/settings.md). Recommended production split: flash / flash-lite / pro.

# Operations

| Method | JSON response field |
|---|---|
| `generate_segment()` | `segment_text`, `current_state` (Situation beat), `future_plan` |
| `summarize_past()` | `summary` |
| `refresh_story_arc()` | `story_arc` |

Prompt templates: `infinity_audiobook/llm_prompts.py`. Tier-1 prompts include a `Last narrated:` block parsed from `## current_state` plus a separate `Now: {situation}` line. The JSON `current_state` field is the Situation beat only.

# Citations

[1] [Google AI Studio](https://aistudio.google.com/)
[2] [Gemini API documentation](https://ai.google.dev/gemini-api/docs)
