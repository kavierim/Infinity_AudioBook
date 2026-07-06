---
type: Feature
title: Remove ACP LLM provider
description: Drop Cursor/Copilot/custom subprocess LLM; Gemini REST API is the only supported provider.
id: acp-remove
status: done
category: llm-providers
priority: normal
created: 2026-07-06T08:45:00Z
updated: 2026-07-06T11:45:00Z
tags: [llm, gemini, acp, cleanup]
related:
  - /modules/llm-clients.md
  - /modules/entry-point.md
  - /modules/text-producer.md
  - /configuration/settings.md
  - /references/gemini-api.md
  - /architecture/pipeline.md
  - /architecture/implementation-phases.md
  - /features/gemini-llm-provider.md
  - /features/tiered-gemini-llm.md
---

# Summary

Remove the Agent Client Protocol (ACP) subprocess path (`cursor`, `copilot`, `custom`) and standardize on **Gemini only** for segment generation, past compaction, and story-arc refresh. Simplify startup (no parallel ACP boot or readiness gate), configuration (`[llm]` only), and documentation.

Functional parity is already covered: [tiered Gemini LLM](tiered-gemini-llm.md) implements all three tiers that ACP exposed via `ACPClient`.

# Problem

The project has a mature [tiered Gemini client](/modules/llm-clients.md). Maintaining ACP adds:

| Cost | Detail |
|---|---|
| Dual LLM stacks | Subprocess JSON-RPC vs REST SDK |
| Startup complexity | `acp-start` thread, `llm_ready_event`, subprocess `start()` / `stop()` |
| Auth surface | `agent login`, `CURSOR_API_KEY`, Copilot CLI |
| Code + tests | `acp_client.py` (~570 lines), `acp_config.py`, two dedicated test modules |
| Doc drift | ACP playbooks, protocol reference, provider tables in settings |

The backlog goal is a **Google API only** LLM path: one provider, one auth model, less code.

# Requirements

## Code removal

- [x] Delete `infinity_audiobook/acp_client.py`
- [x] Delete `infinity_audiobook/acp_config.py`
- [x] Delete `tests/test_acp_client.py`
- [x] Delete `tests/test_acp_config.py`

## Code migration

- [x] Move `FALLBACK_SEGMENT` to `infinity_audiobook/llm_prompts.py` (next to `SegmentResponse`)
- [x] Relocate `SETTINGS_FILENAME` to a neutral module (`llm_config.py` or `settings_paths.py`) — imported today from `acp_config` by `main.py`, `playback_config.py`, `story_config.py`, `llm_config.py`
- [x] `llm_config.py`: `VALID_LLM_PROVIDERS = frozenset({"gemini"})`; default `provider = "gemini"` when `settings.ini` is missing
- [x] `llm_config.py`: remove `uses_acp()`, `[acp]` fallback in `load_llm_config()`, and ACP branch in `create_llm_client()`
- [x] `llm_config.py`: reject `provider` in `cursor`, `copilot`, `custom` with the error message defined in [Design](#legacy-provider-error)
- [x] `main.py`: remove `skip_acp`, `acp-start` thread, `llm_ready` event, and `llm_ready_event=` passed to text producer
- [x] `main.py`: remove `hasattr(llm_client, "stop")` shutdown branch
- [x] `text_producer.py`: import `FALLBACK_SEGMENT` from `llm_prompts`; remove `ACPClient` import and type union
- [x] `text_producer.py`: remove `llm_ready_event` from `text_producer_loop()` and `run_text_producer()` signatures and wait loop
- [x] Fix imports: `tests/conftest.py`, `tests/test_pipeline.py` (`SegmentResponse` from `llm_prompts`, not `acp_client`)

## Configuration

- [x] `settings.example.ini`: remove `[acp]` section; show `provider = gemini` as the default under `[llm]`
- [x] `.env.example`: remove `CURSOR_API_KEY` comment

## Documentation (OKF + repo root)

- [x] [settings.md](/configuration/settings.md) — Gemini-only `[llm]`; remove `[acp]` section
- [x] [llm-clients.md](/modules/llm-clients.md) — Gemini-only factory; fallback cites `llm_prompts.FALLBACK_SEGMENT`
- [x] [entry-point.md](/modules/entry-point.md) — remove ACP boot and `skip_acp`
- [x] [text-producer.md](/modules/text-producer.md) — remove ACP provider row and `llm_ready_event`
- [x] [modules/index.md](/modules/index.md) — drop `acp_config.py` from supporting modules list
- [x] [pipeline.md](/architecture/pipeline.md) — Gemini-only LLM step; remove parallel ACP boot
- [x] [constraints.md](/architecture/constraints.md) — remove ACP permission and `new_session()` bullets
- [x] [error-handling.md](/architecture/error-handling.md) — remove ACP subprocess failure row
- [x] [implementation-phases.md](/architecture/implementation-phases.md) — phase 4 = Gemini LLM (not ACP)
- [x] [project-structure.md](/architecture/project-structure.md) — drop `acp_*.py`
- [x] [tech-stack.md](/architecture/tech-stack.md) — remove `agent` CLI / ACP references
- [x] [authentication.md](/playbooks/authentication.md) — Gemini-only auth
- [x] [quick-start.md](/playbooks/quick-start.md) — `GEMINI_API_KEY` default; remove `agent login`
- [x] [testing.md](/playbooks/testing.md) — remove ACP scope and `skip_acp`
- [x] [debugging-llm.md](/playbooks/debugging-llm.md) — remove ACP section and “switch provider” workaround
- [x] Delete [acp-protocol.md](/references/acp-protocol.md); update [references/index.md](/references/index.md)
- [x] `README.md` — Gemini-only LLM; update auth step
- [x] `AGENTS.md` — remove ACP provider table, phase-4 ACP note, ACP auth prerequisite
- [x] Append [log.md](/log.md) on ship

## Tests

- [x] `uv run pytest` — full suite green
- [x] `test_llm_config.py`: legacy `provider = cursor` (and `[acp]`-only ini) → `ValueError` with migration message
- [x] `test_main.py`: remove `skip_acp=True` kwargs; pipeline still starts with injectable `llm_config`
- [x] `test_playback_config.py`: stop using `[acp]` section in fixture ini files
- [x] No test imports from `acp_client` or `acp_config`
- [x] No test depends on `agent` CLI or real subprocess

# Design

## Provider model

| Before | After |
|---|---|
| `gemini` → `TieredGeminiClient` | unchanged |
| `cursor` / `copilot` / `custom` → `ACPClient` | **removed** — `ValueError` at config load |

## Default when `settings.ini` is absent

`LLMConfig(provider="gemini", …)` with tier models falling back to `DEFAULT_GEMINI_MODEL`. Log: `No settings.ini found — using default LLM provider (gemini)` (not `cursor`).

## Startup simplification

**Before:** `load TTS` → `create LLM client` → `[acp-start thread]` → `llm_ready_event` → `text producer`

**After:** `load TTS` → `TieredGeminiClient` → `text producer`

Cold-start TTS replay (`queue_replay_from_story`) is unchanged.

## Fallback segment

Keep behavior: canned lighthouse narration on non-quota LLM failure; negative `segment_id`; `story.md` not updated. Only move `FALLBACK_SEGMENT` to `llm_prompts.py`.

## Legacy provider error

On `load_llm_config()` when `provider` is `cursor`, `copilot`, or `custom`:

```
ValueError: LLM provider '<name>' is no longer supported. Set provider = gemini in [llm] and configure GEMINI_API_KEY or GOOGLE_API_KEY.
```

Raise before TTS model load so misconfiguration fails fast.

## SETTINGS_FILENAME relocation

Prefer `infinity_audiobook/settings_paths.py` (single constant) if `llm_config.py` would create circular imports with `playback_config` / `story_config`. Otherwise colocate in `llm_config.py`.

## Files touched (inventory)

| Action | Path |
|---|---|
| Delete | `acp_client.py`, `acp_config.py`, `test_acp_client.py`, `test_acp_config.py`, `references/acp-protocol.md` |
| Edit | `llm_config.py`, `llm_prompts.py`, `main.py`, `text_producer.py`, `playback_config.py`, `story_config.py`, test files listed above |
| Edit | `settings.example.ini`, `.env.example`, `README.md`, `AGENTS.md`, OKF docs in Requirements |

# Out of scope

- OmniVoice TTS (local GPU path stays)
- [Gemini TTS provider](gemini-tts.md) — separate feature
- New non-Gemini LLM providers
- Automatic migration of existing `settings.ini` files
- Archiving `acp-protocol.md` elsewhere — delete from bundle

# Test plan

1. `uv run pytest`
2. No `settings.ini`, `GEMINI_API_KEY` set → pipeline starts without `agent` on `PATH`
3. `settings.ini` with `provider = cursor` → `ValueError` before TTS load
4. LLM failure (mocked) → fallback segment plays with negative `segment_id`; `story.md` unchanged

# Completion

Shipped 2026-07-06. Removed ACP stack (~570 lines + tests); Gemini-only `load_llm_config`. Added `settings_paths.py`; `FALLBACK_SEGMENT` moved to `llm_prompts.py`. Docs updated: settings, llm-clients, pipeline, authentication, references. Breaking: `provider = cursor` fails at startup — set `provider = gemini` and API key.
