---
type: Feature
title: "<Display name>"
description: "<One-line summary for index.md and agents>"
id: "<slug>"                    # filename without .md; use in commit messages (feature:<slug>)
status: backlog                 # backlog | specced | in_progress | done | cancelled
category: "<group>"             # e.g. llm-providers | tts-providers | story-structure | polish | pipeline
priority: normal                # low | normal | high — optional
created: <YYYY-MM-DDTHH:MM:SSZ>
updated: <YYYY-MM-DDTHH:MM:SSZ>
completed:                      # YYYY-MM-DD when status: done; omit otherwise
tags: [<topic>, …]
related:
  - /modules/<module>.md
  - /configuration/<config>.md
  - /architecture/<doc>.md
---

<!-- HOW TO USE
1. Copy this file to knowledge/features/<id>.md (do not ship _template.md itself).
2. Fill frontmatter; set status: specced when requirements are review-ready.
3. Write acceptance criteria as checkboxes under # Requirements — agents treat these as the definition of done.
4. Link related OKF concepts; prefer bundle-relative paths (/modules/…).
5. Add an entry to knowledge/features/index.md (Backlog or Done).
6. Add a one-line link in TODO.md if the item is on the open backlog.
7. On ship: check all boxes, set status: done, fill # Completion, update related module/configuration docs, append knowledge/log.md.
-->

# Summary

<!-- 2–4 sentences: what ships, who benefits, key user-visible or architectural outcome. -->

# Problem

<!-- Why now? Pain points, gaps, or maintenance cost. Tables and concrete examples help. -->

# Requirements

<!-- Group with ## headings when the feature touches multiple areas. Every checkbox is acceptance criteria. -->

## Code

- [ ] …

## Configuration

- [ ] …

## Documentation

- [ ] Update related OKF concepts listed in `related:` frontmatter
- [ ] Update `README.md` if user-facing behavior or quick start changes
- [ ] Update `AGENTS.md` if agent workflow or constraints change
- [ ] Append [log.md](/log.md) on ship

## Tests

- [ ] `uv run pytest` passes
- [ ] …

# Design

<!-- Technical approach, trade-offs, data flow, API shape. Diagrams or before/after tables welcome. -->

# Out of scope

<!-- Explicit boundaries — prevents scope creep during implementation. -->

# Test plan

<!-- How to verify beyond unit tests: manual smoke steps, edge cases, regression checks. -->

# Completion

<!-- Fill when shipped. Leave as _Not yet shipped._ until then.

Example:
Shipped YYYY-MM-DD. <What changed in code.> Docs updated: <links>. Breaking: <yes/no + migration note if any>.
-->

_Not yet shipped._
