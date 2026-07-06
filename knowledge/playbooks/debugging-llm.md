---
type: Playbook
title: Debugging LLM traffic
description: Enable JSONL traffic logs, interpret tiers, and handle Gemini quota errors.
tags: [playbook, debug, llm, gemini]
timestamp: 2026-07-06T09:30:00Z
---

# Enable logging

In `settings.ini`:

```ini
[llm]
debug_traffic = true
```

Or set environment variable:

```bash
AUDIOBOOK_DEBUG_LLM=1
```

# Output

`debug/llm/traffic.jsonl` — one JSON object per line. The `debug/` folder is gitignored.

Each entry includes:

- `operation`: `segment`, `summary`, or `arc`
- `model`: model id used
- `tier`: same as `operation`
- `prompt`, `response` or `error`

# Quota and rate limits

Gemini errors are classified in `gemini_errors.py`. On quota exhaustion the text producer **waits** (`retry_after` seconds) and retries — no fallback audio, no `story.md` update.

Check traffic log for repeated errors. Consider:

- Lower segment frequency (increase [max_buffer_seconds](/configuration/playback.md) won't help quota — reduce usage)
- Use `gemini-2.5-flash-lite` for tier 2 summary

# Fallback segments

Non-quota LLM failures produce a canned lighthouse narration. Log line: `Skipping story.md update for fallback segment`. Indicates LLM parse or transport failure — check traffic log.
