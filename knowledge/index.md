---
okf_version: "0.1"
---

# InfinityAudioBook Knowledge Bundle

Agent- and human-readable documentation for the infinite audiobook player. This bundle is the **single source of truth** for architecture, configuration, module design, and [feature specs](features/index.md).

# Getting started

* [Quick start](playbooks/quick-start.md) - Install, configure, and run your first session.
* [Authentication](playbooks/authentication.md) - Gemini API keys.
* [Testing](playbooks/testing.md) - pytest scope and TDD guidelines.

# Architecture

* [Overview](architecture/overview.md) - Goals, platform, and PoC scope.
* [Tech stack](architecture/tech-stack.md) - Python, uv, CUDA, and dependencies.
* [Project structure](architecture/project-structure.md) - Repository layout.
* [Pipeline](architecture/pipeline.md) - Four-stage async pipeline (text → TTS → buffer → speaker).
* [Data models](architecture/data-models.md) - Segments, queues, and audio chunks.
* [Error handling](architecture/error-handling.md) - Failure modes and recovery.
* [Implementation phases](architecture/implementation-phases.md) - Build order for agents and developers.
* [Constraints](architecture/constraints.md) - Coding rules and token usage.

# Configuration

* [settings.ini](configuration/settings.md) - Gemini model tiers, playback limits.
* [story.md](configuration/story-state.md) - Living narrative state file.
* [Playback](configuration/playback.md) - Segment gaps and buffer backpressure.

# Features

* [Feature index](features/index.md) - Implementation specs, acceptance criteria, and delivery history.
* [Feature template](features/_template.md) - Copy for new backlog specs (`type: Feature`).

# Modules

* [Package overview](modules/index.md) - Python module map under `infinity_audiobook/`.

# Playbooks

* [Debugging LLM traffic](playbooks/debugging-llm.md) - `debug/llm/traffic.jsonl` and quota errors.

# References

* [OmniVoice TTS](references/omnivoice.md) - Voice cloning integration.
* [Gemini API](references/gemini-api.md) - Google AI Studio tiered client.

# Related documents (repo root)

* [README.md](../README.md) - Project entry point and quick start.
* [AGENTS.md](../AGENTS.md) - Agent coding instructions.
* [TODO.md](../TODO.md) - Backlog index (links to feature specs).
