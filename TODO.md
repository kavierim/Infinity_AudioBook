# Backlog index

Implementation specs live in **[docs/features/](docs/features/index.md)** (`type: Feature`). That directory is the source of truth for requirements and acceptance criteria.

**New backlog item:** copy [docs/features/_template.md](docs/features/_template.md) to `docs/features/<id>.md`, then add a link here and in [features/index.md](docs/features/index.md#backlog).

> **Note for AI agents:** Read the feature spec before implementing. Do not treat bullets below as fixed acceptance criteria.

## Open

- [ ] [Gemini TTS provider](docs/features/gemini-tts.md) — cloud TTS alternative to OmniVoice

## Done

- [x] [Architecture optimization](docs/features/architecture-optimization.md) — unified settings load, startup story reads, language cache

- [x] [Current state with last narrated transcript](docs/features/current-state-transcript.md) — spoken prose + situation in `## current_state`
- [x] [Terminal UI (TUI)](docs/features/tui.md) — Textual dashboard (transcript, summary, storyline, activity log)

- [x] [Remove ACP LLM provider](docs/features/acp-remove.md) — Gemini-only; drop subprocess ACP stack
