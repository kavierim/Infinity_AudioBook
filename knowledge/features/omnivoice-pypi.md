---
type: Feature
title: OmniVoice PyPI dependency
description: Switch omnivoice from local path dependency to PyPI 0.1.5.
id: omnivoice-pypi
status: done
category: dependencies
created: 2026-07-05T08:00:00Z
updated: 2026-07-05T12:00:00Z
completed: 2026-07-05
tags: [tts, omnivoice, dependencies]
related:
  - /references/omnivoice.md
  - /modules/tts.md
---

# Summary

Replace `[tool.uv.sources]` path override with PyPI `omnivoice==0.1.5` so the project installs without a sibling OmniVoice clone.

# Completion

- **Shipped:** 2026-07-05
- **Summary:** Removed path dependency; `uv sync` works on a clean machine. Tests and docs updated.
- **Docs updated:** [omnivoice](/references/omnivoice.md), `README.md`, `AGENTS.md`
