# Backlog index

Implementation specs live in **[knowledge/features/](knowledge/features/index.md)** (`type: Feature`). That directory is the source of truth for requirements and acceptance criteria.

**New backlog item:** copy [knowledge/features/_template.md](knowledge/features/_template.md) to `knowledge/features/<id>.md`, then add a link here and in [features/index.md](knowledge/features/index.md#backlog).

> **Note for AI agents:** Read the feature spec before implementing. Do not treat bullets below as fixed acceptance criteria.

## Open

- [ ] [Gemini TTS provider](knowledge/features/gemini-tts.md) — cloud TTS alternative to OmniVoice

## Done

- [x] [Architecture optimization](knowledge/features/architecture-optimization.md) — unified settings load, startup story reads, language cache

- [x] [Current state with last narrated transcript](knowledge/features/current-state-transcript.md) — spoken prose + situation in `## current_state`
- [x] [Terminal UI (TUI)](knowledge/features/tui.md) — Textual dashboard (transcript, summary, storyline, activity log)

- [x] [Remove ACP LLM provider](knowledge/features/acp-remove.md) — Gemini-only; drop subprocess ACP stack
