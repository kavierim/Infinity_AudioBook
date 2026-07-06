# Features

Implementation specs and delivery history. Each feature is one OKF concept (`type: Feature`) with acceptance criteria and a completion record.

**Before implementing:** read the feature spec in this directory — not `TODO.md` bullets alone.

**New feature:** copy [_template.md](_template.md) to `<id>.md`, fill sections, add a Backlog entry below, and link from `TODO.md`.

# Backlog

## TTS providers

* [Gemini TTS provider](gemini-tts.md) — Cloud TTS alternative to OmniVoice (`status: specced`).

# Done

## Pipeline

* [Architecture optimization](architecture-optimization.md) — unified settings load, startup story read consolidation, `StoryLanguageCache` (`status: done`).

## Dependencies

* [OmniVoice PyPI dependency](omnivoice-pypi.md) — PyPI `omnivoice==0.1.5`, no local clone.

## LLM providers

* [Gemini LLM provider](gemini-llm-provider.md) — `provider = gemini` via REST API.
* [Tiered Gemini LLM models](tiered-gemini-llm.md) — Three model tiers for segment, summary, arc.
* [Remove ACP LLM provider](acp-remove.md) — Gemini-only; dropped subprocess ACP stack.

## Story structure

* [Current state with last narrated transcript](current-state-transcript.md) — `## current_state` holds spoken prose + situation for restart continuity (`status: done`).
* [Story arc (book red thread)](story-arc.md) — `## story_arc` with tier-3 refresh.

## Polish

* [Terminal UI (TUI)](tui.md) — Textual full-screen dashboard; only user-facing interface (`status: done`).
* [Segment gap pause](segment-gap.md) — Configurable silence between segments.
* [Reference sources in prompts](reference-sources.md) — Inline `sources/` for non-fiction.
* [MIT license](license-mit.md) — `LICENSE` file.
* [OKF documentation bundle](okf-documentation.md) — `knowledge/` bundle migration.

## Pipeline robustness

* [Playback backpressure accounting](playback-backpressure.md) — Queue-aware buffer cap.
* [Story language module cleanup](story-language-cleanup.md) — `story_language.py` resolved.
* [Graceful shutdown polish](graceful-shutdown.md) — Documented best-effort shutdown.
