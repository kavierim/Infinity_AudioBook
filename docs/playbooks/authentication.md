---
type: Playbook
title: Authentication
description: API keys for Gemini LLM provider.
tags: [playbook, auth, gemini]
timestamp: 2026-07-06T09:30:00Z
---

# .env file

Copy `.env.example` to `.env` at project root. Loaded automatically at startup; existing shell variables take precedence.

```bash
GEMINI_API_KEY=...
# or
GOOGLE_API_KEY=...
```

# Gemini

| Auth | Source |
|---|---|
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) |

Set `provider = gemini` in `[llm]` (default when `settings.ini` is absent).

# Notes

- Free tier available where supported.
- Compaction adds one extra API call (tier 2) when `past` exceeds 25 lines.
- Arc refresh (tier 3) runs every `arc_refresh_every` segments when `## story_arc` exists.

See [settings.ini](/configuration/settings.md) for model tier configuration.
