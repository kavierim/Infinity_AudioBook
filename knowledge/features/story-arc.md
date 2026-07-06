---
type: Feature
title: Story arc (book red thread)
description: story_arc section in story.md with tier-3 LLM refresh.
id: story-arc
status: done
category: story-structure
created: 2026-07-05T10:00:00Z
updated: 2026-07-05T16:00:00Z
completed: 2026-07-05
tags: [story, llm, arc]
related:
  - /configuration/story-state.md
  - /modules/story-state-module.md
  - /modules/text-producer.md
---

# Summary

`## story_arc` in `story.md` gives the LLM a long-range narrative thread; tier-3 refresh updates it periodically.

# Completion

- **Shipped:** 2026-07-05
- **Summary:** Parsed in `story_state.py`; included in tier-1 prompts when non-empty. `story_arc.py` refreshes every `arc_refresh_every` segments. User can edit manually.
- **Docs updated:** [story-state](/configuration/story-state.md)
