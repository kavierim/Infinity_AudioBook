---
type: Module
title: Story state
description: Parse, read, and atomically write story.md with file locking.
tags: [module, story-state]
timestamp: 2026-07-06T09:25:00Z
---

# File

`infinity_audiobook/story_state.py`

# StoryState dataclass

Fields mirror [story.md sections](/configuration/story-state.md): `title`, `genre`, `perspective`, `language`, `narrator_tone`, `story_arc`, `summary`, `past`, `current_state`, `future_plan`, `references`.

`StoryState.current_state` holds the raw section body (structured or legacy plain text). Use `parse_current_state()` to split it.

# CurrentStateBlocks

| Field | Meaning |
|---|---|
| `last_narrated` | Full spoken segment prose (`truncate_segment_text` output) |
| `last_segment_id` | `#N` from the `Last narrated (#N):` label, or `None` |
| `situation` | Brief situational beat (LLM-authored or opening beat) |

# Key functions

| Function | Purpose |
|---|---|
| `read_story(path)` | Parse `story.md` into `StoryState` |
| `write_story_updates(...)` | Append past, replace state/plan after segment |
| `write_story_compact(...)` | Update summary and trimmed past |
| `write_story_arc(...)` | Replace story_arc section |
| `write_story_language(...)` | Set language code |
| `next_segment_id(past)` | Monotonic `#N` from existing past lines |
| `derive_past_append(text)` | First-sentence summary for past line |
| `truncate_segment_text(text)` | Cap at 200 words, sentence boundary |
| `past_for_prompt(past, max_lines=12)` | Truncate for LLM |
| `summary_for_prompt(summary, max_words=350)` | Truncate for LLM |
| `story_arc_section_present(content)` | Check if `## story_arc` exists |
| `parse_current_state(body)` | Split `Last narrated` + `Situation` blocks |
| `format_current_state(...)` | Write structured `current_state` body |
| `situation_for_prompt(body)` | Situation beat only (tier 3, TUI Now tab, cold start) |
| `current_state_for_tier1_prompt(body)` | `(last_narrated, situation)` for tier 1 |
| `last_narrated_for_replay(body)` | `(segment_id, text)` for startup TTS replay, or `None` |
| `StoryLanguageCache` | Mtime-based language cache for audio producer hot path |

# StoryLanguageCache

Thread-safe cache keyed on `story.md` mtime. `seed(language)` initializes from startup `StoryState`; `get()` re-parses only when the file changes on disk.

# Concurrency

Global `_FILE_LOCK` plus atomic write (temp file + rename).

# Languages

Supported codes: `en`, `fi`. Aliases accepted at startup prompt (`english`, `suomi`, etc.).
