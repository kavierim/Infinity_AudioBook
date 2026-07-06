---
type: Feature
title: Graceful shutdown polish
description: Document and refine shutdown behavior on quit (q) or Ctrl+C.
id: graceful-shutdown
status: done
category: pipeline-robustness
created: 2026-07-05T20:00:00Z
updated: 2026-07-05T22:00:00Z
completed: 2026-07-05
tags: [pipeline, shutdown]
related:
  - /architecture/error-handling.md
  - /modules/entry-point.md
---

# Summary

Review daemon worker threads, join timeouts, and queue drain on shutdown.

# Completion

- **Shipped:** 2026-07-05
- **Summary:** Best-effort shutdown documented; `main.py` joins workers with 5 s timeout. No full queue drain — behavior documented in error handling.
- **Docs updated:** [error-handling](/architecture/error-handling.md)
