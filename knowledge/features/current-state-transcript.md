---
type: Feature
title: Current state with last narrated transcript
description: Structure current_state with spoken segment prose plus situation beat so story.md and LLM prompts stay continuous across restarts.
id: current-state-transcript
status: done
category: story-structure
priority: high
created: 2026-07-06T06:15:00Z
updated: 2026-07-06T11:05:00Z
tags: [story, llm, continuity, restart]
related:
  - /configuration/story-state.md
  - /modules/story-state-module.md
  - /modules/text-producer.md
  - /modules/llm-clients.md
  - /features/tui.md
  - /features/last-spoken-persistence.md
---

# Summary

Extend `## current_state` in `story.md` to hold **both** the last spoken segment (full TTS-bound prose) and the situational beat the LLM already returns. Tier-1 prompts and the TUI read this block on cold start so the next segment continues from actual narrated wording, not a one-line `past` log alone.

Supersedes [last-spoken-persistence](/features/last-spoken-persistence.md) (separate `## last_spoken` section is not needed).

# Problem

Today `current_state` is only a brief beat, e.g. *«Sieni-virkamies odottaa lomakkeen täyttämistä…»*. Full narration lives nowhere durable:

| What is stored | What is lost |
|---|---|
| `past` | First sentence only (`derive_past_append`, max 240 chars) |
| `current_state` | Meta-summary; no last spoken prose |
| TUI transcript | In-memory ring buffer — **empty after restart** |

Tier-1 prompts receive `summary` + up to 12 `past` one-liners + `current_state` + `future_plan`. After a restart the LLM does not see how segment #N actually ended (dialogue mid-line, tone, exact imagery). The next segment often **jumps**, **repeats**, or **contradicts** the last narrated passage — especially when `past` and `current_state` were written in an earlier session.

Example from a real session: segments #96–#100 describe being flat; after restart #101–#104 repeat the same beat before the story moves on at #105.

# Requirements

## story.md format

- [x] Define a fixed layout for `## current_state` with two labeled blocks (labels in **English** for reliable parsing; prose in story language):
  - **`Last narrated (#N):`** — full spoken text (`truncate_segment_text` output), segment id from the log
  - **`Situation:`** — LLM `current_state` JSON field (brief beat, story language)
- [x] On cold start / empty story, omit the `Last narrated` block; `Situation` holds the opening beat (unchanged opening semantics)
- [x] Document the format in [story-state](/configuration/story-state.md)

## story_state module

- [x] `CurrentStateBlocks` dataclass: `last_narrated`, `last_segment_id`, `situation`
- [x] `parse_current_state(body) -> CurrentStateBlocks` — see [Parsing](#parsing)
- [x] `format_current_state(last_narrated, segment_id, situation) -> str`
- [x] `situation_for_prompt(body) -> str` — `Situation` text only (tier 3, cold-start opening)
- [x] `current_state_for_tier1_prompt(body) -> tuple[str, str]` — `(last_narrated, situation)` for prompt assembly
- [x] Tests in `tests/test_story_state.py` and `tests/test_llm_prompts.py`

## Write path (text_producer)

- [x] After each **successful** segment, [text-producer](/modules/text-producer.md) calls `format_current_state(spoken_text, counter_segment_id, response.current_state)` and passes the result to `write_story_updates(..., current_state=...)`
- [x] Spoken text = `truncate_segment_text` output (not raw LLM `segment_text`)
- [x] Compaction only touches `summary` / `past` — does not rewrite `current_state` (verify in tests)
- [x] Failed / fallback segments do **not** update `current_state` (existing rule)

## Read path (LLM)

- [x] [text-producer](/modules/text-producer.md) passes `current_state_for_tier1_prompt(state.current_state)` into `generate_segment` (not the raw section body)
- [x] [llm_prompts.py](/modules/llm-clients.md) tier-1 `PROMPT_TEMPLATE`:
  - separate placeholders `{last_narrated}` and `{situation}` (replace single `{current_state}`)
  - instruct model: JSON `current_state` = brief **Situation** beat only — do **not** repeat `Last narrated` prose
- [x] `read_story` before every segment already reloads disk — no extra cache
- [x] LLM JSON schema stays `{ segment_text, current_state, future_plan }`; `Last narrated` is writer-owned, never LLM-authored

## Read path (tier 3 arc)

- [x] [story_arc.py](/modules/story-state-module.md) passes `situation_for_prompt(state.current_state)` to `refresh_story_arc`, not the raw section body

## Read path (TUI)

- [x] On startup, `queue_replay_from_story()` enqueues `Last narrated` for immediate TTS (no wait for LLM)
- [x] On startup, seed the transcript ring from parsed `Last narrated` + `last_segment_id` in `current_state` (one entry) until live segments fill the ring — per [tui](/features/tui.md)
- [x] Storyline **Now** tab shows `Situation` text only (`Last narrated` appears in Transcript)

# Design

## Section template

```markdown
## current_state

Last narrated (#112):

Sieni-virkamies odotti. Marvinin optiset sensorit välähtivät punaisina kuin…

Situation:

Sieni-virkamies odottaa lomakkeen täyttämistä, kun Marvin menettää kärsivällisyytensä.
```

- Blank line after each label line; prose may be multiple paragraphs.
- Segment id in the label must match the `past` line just appended for that segment.
- If spoken text is empty (should not happen on success), omit the `Last narrated` block.
- Labels stay English even for Finnish stories — machine anchors only; narrative prose stays in story language.

## Parsing

`parse_current_state(body)` rules:

1. If body matches structured form — line `Last narrated (#N):` (regex `^Last narrated \(#(\d+)\):\s*$`), then prose until a line exactly `Situation:` — parse `last_narrated`, `last_segment_id`, `situation`.
2. Otherwise treat the **entire** body as `situation` with `last_narrated=""` and `last_segment_id=None` (legacy / hand-edited files).
3. If `Situation:` label is missing but `Last narrated` matched, prose after the label is kept in `last_narrated`; `situation` may be empty until the next successful segment rewrite.
4. Never fail `read_story` on bad structure — degrade to legacy parse.

Manual edits: users may edit `Situation` freely; editing `Last narrated` is allowed (next segment uses the edited prose). Removing labels reverts to legacy parse until the next successful segment rewrite.

## Prompt assembly (tier 1)

```
Next audiobook segment … JSON current_state = brief Situation only (do not repeat Last narrated).

Story summary:
…

Recent past:
…

Last narrated:
{last_narrated or (none)}

Now: {situation}
Plan: {future_plan}
```

**Token note:** `Last narrated` (~200 words) may overlap the newest `past` line (first sentence of the same segment). Acceptable cost for restart continuity; do not dedupe in v1.

## Tier 3 arc refresh

Uses `situation_for_prompt(state.current_state)` plus `summary` and `future_plan` — no `Last narrated` prose.

## Migration and upgrade gap

Existing `story.md` files with a plain-text `current_state` body parse as `situation = full body`, `last_narrated = ""`.

**Known limitation:** after upgrading code on a story that already has `past` entries, **the first restart still lacks `Last narrated`** until one new segment succeeds and rewrites `current_state`. Continuity on that first post-upgrade segment is the same as today (`summary` + `past` + `Situation`). Document in [story-state](/configuration/story-state.md).

No bootstrap from `past` alone — `past` holds only the first sentence, not full prose.

## Relation to past / summary

- `past` one-liners remain for human scan and compaction input — unchanged.
- `Last narrated` is the authoritative “continue from here” prose for tier 1.

# Out of scope

- Full multi-segment transcript history in `story.md` (TUI ring stays in-memory for recent N only)
- Changing `past` log format or compaction thresholds
- Asking the LLM to author the `Last narrated` block
- Localized machine labels (`Viimeksi kerrottu` / `Tilanne`) — English labels only in v1
- Backfilling `Last narrated` from historical segments without re-running the LLM

# Test plan

- Round-trip `parse_current_state` / `format_current_state` for structured body
- Legacy plain `current_state` parses as situation-only (`last_narrated=""`)
- Malformed body (missing `Situation:` label) degrades safely
- `build_prompt` includes `Last narrated` block when present; omits when empty
- `build_prompt` JSON instruction mentions Situation-only `current_state`
- `text_producer` integration: successful segment writes both blocks with correct `#N`
- `story_arc` receives situation-only, not full section body
- TUI cold start: transcript panel shows one entry from disk when `Last narrated` exists
- TUI **Now** tab shows `Situation` only when structured `current_state` is present
- Startup replay: `queue_replay_from_story` enqueues last narrated segment before first LLM call
- Compaction does not remove or alter `Last narrated` in `current_state`
- Cold start opening: `situation_for_prompt` with no `Last narrated` block returns opening beat only

# Completion

Shipped 2026-07-06. `story_state.py` adds `CurrentStateBlocks`, `parse_current_state`, `format_current_state`, `situation_for_prompt`, `current_state_for_tier1_prompt`, and `last_narrated_for_replay`. Tier-1 prompts use separate `Last narrated` / `Situation` placeholders; `text_producer` writes spoken prose after each successful segment; tier-3 arc refresh uses situation only; TUI **Transcript** seeds from disk; TUI **Now** shows situation only; startup TTS replay via `queue_replay_from_story()` before the first LLM call.
