---
type: Feature
title: Reference sources in prompts
description: Inline sources/ text files into non-fiction LLM prompts.
id: reference-sources
status: done
category: polish
created: 2026-07-05T08:00:00Z
updated: 2026-07-05T12:00:00Z
completed: 2026-07-05
tags: [story, non-fiction, prompts]
related:
  - /configuration/story-state.md
  - /modules/text-producer.md
---

# Summary

Load files referenced from `story.md` into tier-1 prompts for non-fiction mode, with an 8 KB cap per file.

# Completion

- **Shipped:** 2026-07-05
- **Summary:** `reference_sources.py` with `expand_references_for_prompt`. Tests in `tests/test_reference_sources.py`.
- **Docs updated:** [story-state](/configuration/story-state.md)
