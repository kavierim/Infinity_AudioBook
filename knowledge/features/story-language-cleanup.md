---
type: Feature
title: Story language module cleanup
description: Remove or repurpose unused story_language.py interactive prompt.
id: story-language-cleanup
status: done
category: pipeline-robustness
created: 2026-07-05T20:00:00Z
updated: 2026-07-05T22:00:00Z
completed: 2026-07-05
tags: [story, startup]
related:
  - /modules/entry-point.md
  - /configuration/settings.md
---

# Summary

Resolve drift between `story_language.py` (tested but unwired) and runtime `story_config.py` + `[story] language` in `settings.ini`.

# Completion

- **Shipped:** 2026-07-05
- **Summary:** Removed standalone `story_language.py`; language helpers (`normalize_story_language`, `write_story_language`) live in `story_state.py`. Startup uses `story_config.py` and `[story] language` in `settings.ini`. Tests remain in `tests/test_story_language.py`.
- **Docs updated:** [entry-point](/modules/entry-point.md)
