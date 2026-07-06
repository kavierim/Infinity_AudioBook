---
type: Feature
title: Gemini LLM provider
description: Google AI Studio REST provider behind SegmentGenerator protocol.
id: gemini-llm-provider
status: done
category: llm-providers
created: 2026-07-05T08:00:00Z
updated: 2026-07-05T14:00:00Z
completed: 2026-07-05
tags: [llm, gemini]
related:
  - /references/gemini-api.md
  - /modules/llm-clients.md
  - /configuration/settings.md
---

# Summary

Add `provider = gemini` with `GeminiClient` for segment generation and story compaction via REST API. As of [acp-remove](acp-remove.md), Gemini is the **only** supported LLM provider.

# Completion

- **Shipped:** 2026-07-05
- **Summary:** `GeminiClient` wired into `text_producer.py` and `story_compact.py`. Auth via `GEMINI_API_KEY` / `GOOGLE_API_KEY`. HTTP mocked in tests.
- **Docs updated:** [gemini-api](/references/gemini-api.md), [settings](/configuration/settings.md), [llm-clients](/modules/llm-clients.md)
