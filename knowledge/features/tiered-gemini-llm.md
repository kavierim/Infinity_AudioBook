---
type: Feature
title: Tiered Gemini LLM models
description: Three model tiers for segment, summary, and story-arc tasks.
id: tiered-gemini-llm
status: done
category: llm-providers
created: 2026-07-05T10:00:00Z
updated: 2026-07-05T16:00:00Z
completed: 2026-07-05
tags: [llm, gemini, tiers]
related:
  - /modules/llm-clients.md
  - /configuration/settings.md
  - /modules/text-producer.md
---

# Summary

`TieredGeminiClient` routes segment generation, compaction, and arc refresh to separate models configured in `[llm]`.

# Completion

- **Shipped:** 2026-07-05
- **Summary:** Tier 1 `model_segment`, tier 2 `model_summary`, tier 3 `model_arc` with `arc_refresh_every`. Debug logs include `tier` and `model`.
- **Docs updated:** [settings](/configuration/settings.md), [llm-clients](/modules/llm-clients.md)
