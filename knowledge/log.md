# Directory Update Log

## 2026-07-06
* **Shipped**: [architecture-optimization](features/architecture-optimization.md) — `settings.py` unified loader; startup `story.md` read consolidation; `StoryLanguageCache` for audio producer; docs updated.
* **Shipped**: [acp-remove](features/acp-remove.md) — removed ACP stack; Gemini-only LLM; `settings_paths.py`; docs and tests updated.
* **Update**: [story-state](configuration/story-state.md#restart--resume), [pipeline](architecture/pipeline.md), [tui](features/tui.md), [current-state-transcript](features/current-state-transcript.md), [text-producer](modules/text-producer.md), [entry-point](modules/entry-point.md), [testing](playbooks/testing.md), [quick-start](playbooks/quick-start.md) — startup TTS replay (`queue_replay_from_story`), parallel ACP boot, TUI **Now** = Situation only.
* **Update**: [story-state](configuration/story-state.md), [text-producer](modules/text-producer.md), [llm-clients](modules/llm-clients.md), [pipeline](architecture/pipeline.md), [constraints](architecture/constraints.md), [quick-start](playbooks/quick-start.md), [testing](playbooks/testing.md), ACP protocol (since removed), [gemini-api](references/gemini-api.md), [tui](features/tui.md), [last-spoken-persistence](features/last-spoken-persistence.md) — docs aligned with structured `current_state`.
* **Shipped**: [current-state-transcript](features/current-state-transcript.md) — structured `## current_state` with `Last narrated` + `Situation`; tier-1 prompts, TUI cold-start transcript seed.
* **Update**: [current-state-transcript](features/current-state-transcript.md) — requirements tightened (text_producer, story_arc, parsing rules, LLM Situation-only instruction, upgrade gap).
* **Shipped**: [tui](features/tui.md) — Textual full-screen dashboard replaces command center; `infinity_audiobook/ui/` package; `textual` dependency.
* **Update**: [quick-start](playbooks/quick-start.md), [error-handling](architecture/error-handling.md), [tech-stack](architecture/tech-stack.md), [implementation-phases](architecture/implementation-phases.md), `AGENTS.md` — TUI quit (`q`) and footer input; removed stale `status` / `stop` / `>` prompt references.
* **Creation**: Added [features](features/index.md) directory with `type: Feature` specs; migrated backlog from `TODO.md`. Open: [gemini-tts](features/gemini-tts.md), [last-spoken-persistence](features/last-spoken-persistence.md).

## 2026-07-05 (review fixes)
* **Code**: Preserve user instructions across Gemini retries; negative fallback segment ids; ACP subprocess restart; JSON parse retry; ACP `create_plan` → skipped; tier in ACP debug logs.
* **Update**: [settings](configuration/settings.md) `[story]` section, startup flow, [error handling](architecture/error-handling.md), ACP protocol (since removed), [entry point](modules/entry-point.md).

## 2026-07-05
* **Migration**: Moved remaining content from root `spec.md` into OKF bundle; deleted `spec.md`.
* **Creation**: Added [overview](architecture/overview.md), [tech stack](architecture/tech-stack.md), [project structure](architecture/project-structure.md), [error handling](architecture/error-handling.md), [implementation phases](architecture/implementation-phases.md), [constraints](architecture/constraints.md), and [testing playbook](playbooks/testing.md).
* **Update**: Enhanced [TTS module](modules/tts.md), ACP protocol (since removed), [settings](configuration/settings.md), and [story state](configuration/story-state.md).
* **Creation**: Initial OKF knowledge bundle for v0.1.0 release prep.
* **Creation**: Added [pipeline](architecture/pipeline.md), [settings](configuration/settings.md), [story.md](configuration/story-state.md), module docs, playbooks, and external references.
