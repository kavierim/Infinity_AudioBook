"""Parse, read, and write the living story.md state file."""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_FILE_LOCK = threading.Lock()

SECTION_KEYS = (
    "title",
    "genre",
    "perspective",
    "language",
    "narrator_tone",
    "story_arc",
    "summary",
    "past",
    "current_state",
    "future_plan",
    "references",
)

EMPTY_PAST_MARKERS = {"*(no events yet)*", ""}
EMPTY_SUMMARY_MARKERS = {"*(no summary yet)*", ""}
EMPTY_STORY_ARC_MARKERS = {"*(no arc yet)*", ""}

_PAST_SEGMENT_ID_RE = re.compile(r"#(\d+):")
_PAST_APPEND_MAX_CHARS = 240
_LAST_NARRATED_LABEL_RE = re.compile(r"^Last narrated \(#(\d+)\):\s*$")
_SITUATION_LABEL = "Situation:"


@dataclass
class CurrentStateBlocks:
    last_narrated: str = ""
    last_segment_id: int | None = None
    situation: str = ""


def parse_current_state(body: str) -> CurrentStateBlocks:
    """Parse structured ## current_state body into narrated prose and situation beat."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        match = _LAST_NARRATED_LABEL_RE.match(line)
        if not match:
            continue

        last_segment_id = int(match.group(1))
        cursor = i + 1
        if cursor < len(lines) and not lines[cursor].strip():
            cursor += 1

        narrated_lines: list[str] = []
        while cursor < len(lines) and lines[cursor].strip() != _SITUATION_LABEL:
            narrated_lines.append(lines[cursor])
            cursor += 1

        last_narrated = "\n".join(narrated_lines).strip()

        if cursor < len(lines) and lines[cursor].strip() == _SITUATION_LABEL:
            cursor += 1
            if cursor < len(lines) and not lines[cursor].strip():
                cursor += 1
            situation = "\n".join(lines[cursor:]).strip()
            return CurrentStateBlocks(
                last_narrated=last_narrated,
                last_segment_id=last_segment_id,
                situation=situation,
            )

        # Last narrated label without Situation: — keep narrated prose; situation empty.
        remainder = "\n".join(lines[cursor:]).strip()
        return CurrentStateBlocks(
            last_narrated=last_narrated,
            last_segment_id=last_segment_id,
            situation=remainder,
        )

    return CurrentStateBlocks(situation=body.strip())


def format_current_state(
    last_narrated: str,
    segment_id: int | None,
    situation: str,
) -> str:
    """Format ## current_state body with Last narrated and Situation blocks."""
    parts: list[str] = []
    narrated = last_narrated.strip()
    if narrated and segment_id is not None:
        parts.extend([f"Last narrated (#{segment_id}):", "", narrated, ""])
    parts.extend([_SITUATION_LABEL, "", situation.strip()])
    return "\n".join(parts)


def situation_for_prompt(body: str) -> str:
    """Return Situation text only (tier 3 arc refresh, cold-start opening)."""
    return parse_current_state(body).situation


def current_state_for_tier1_prompt(body: str) -> tuple[str, str]:
    """Return (last_narrated, situation) for tier-1 segment prompts."""
    blocks = parse_current_state(body)
    return blocks.last_narrated, blocks.situation


def last_narrated_for_replay(body: str) -> tuple[int, str] | None:
    """Return (segment_id, spoken text) when current_state has a replayable segment."""
    blocks = parse_current_state(body)
    text = blocks.last_narrated.strip()
    if text and blocks.last_segment_id is not None:
        return blocks.last_segment_id, text
    return None

STORY_LANGUAGES = {
    "en": "English",
    "fi": "Finnish",
}


def normalize_story_language(value: str) -> str | None:
    """Map user input or story.md value to a supported language code."""
    raw = value.strip().lower()
    if raw in STORY_LANGUAGES:
        return raw
    aliases = {
        "english": "en",
        "finnish": "fi",
        "suomi": "fi",
        "eng": "en",
        "1": "en",
        "2": "fi",
    }
    return aliases.get(raw)


def story_language_name(code: str) -> str:
    return STORY_LANGUAGES.get(code, code)


@dataclass
class StoryState:
    title: str = ""
    genre: str = ""
    perspective: str = ""
    language: str = "en"
    narrator_tone: str = ""
    story_arc: str = ""
    summary: str = ""
    past: str = ""
    current_state: str = ""
    future_plan: str = ""
    references: str = ""

    def is_cold_start(self) -> bool:
        stripped = self.past.strip()
        return stripped in EMPTY_PAST_MARKERS


def _split_sections(content: str) -> dict[str, str]:
    """Split markdown by ## headings into section bodies."""
    sections: dict[str, str] = {}
    current_key: str | None = None
    body_lines: list[str] = []

    for line in content.splitlines():
        heading = re.match(r"^##\s+(\S+)\s*$", line)
        if heading:
            if current_key is not None:
                sections[current_key] = "\n".join(body_lines).strip()
            current_key = heading.group(1).lower()
            body_lines = []
        elif current_key is not None:
            body_lines.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(body_lines).strip()

    return sections


def parse_story_md(content: str) -> StoryState:
    sections = _split_sections(content)
    lang_raw = sections.get("language", "en").strip() or "en"
    language = normalize_story_language(lang_raw) or lang_raw
    return StoryState(
        title=sections.get("title", ""),
        genre=sections.get("genre", ""),
        perspective=sections.get("perspective", ""),
        language=language,
        narrator_tone=sections.get("narrator_tone", ""),
        story_arc=sections.get("story_arc", ""),
        summary=sections.get("summary", ""),
        past=sections.get("past", ""),
        current_state=sections.get("current_state", ""),
        future_plan=sections.get("future_plan", ""),
        references=sections.get("references", ""),
    )


def read_story(path: Path) -> StoryState:
    content = path.read_text(encoding="utf-8")
    return parse_story_md(content)


class StoryLanguageCache:
    """Thread-safe story language with mtime-based invalidation."""

    def __init__(self, path: Path, *, default: str = "en") -> None:
        self._path = path
        self._default = default
        self._lock = threading.Lock()
        self._mtime: float | None = None
        self._language = default

    def get(self) -> str:
        """Return story language, re-reading story.md only when the file changes."""
        with self._lock:
            try:
                mtime = self._path.stat().st_mtime
            except OSError:
                return self._language
            if mtime != self._mtime:
                self._language = read_story(self._path).language
                self._mtime = mtime
            return self._language

    def seed(self, language: str) -> None:
        """Seed cache from an already-loaded story state (startup)."""
        with self._lock:
            self._language = language
            try:
                self._mtime = self._path.stat().st_mtime
            except OSError:
                self._mtime = None


def _replace_section(content: str, key: str, new_body: str) -> str:
    pattern = re.compile(
        rf"(^##\s+{re.escape(key)}\s*\n)(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    if not match:
        return content + f"\n## {key}\n\n{new_body}\n"
    return content[: match.start(2)] + new_body + "\n" + content[match.end(2) :]


def _append_past_line(past_body: str, line: str) -> str:
    stripped = past_body.strip()
    if stripped in EMPTY_PAST_MARKERS:
        return line
    if stripped:
        return stripped + "\n" + line
    return line


def apply_segment_update(
    state: StoryState,
    *,
    segment_id: int,
    past_append: str,
    current_state: str,
    future_plan: str,
) -> StoryState:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    past_line = f"- [{timestamp}] #{segment_id}: {past_append}"
    return StoryState(
        title=state.title,
        genre=state.genre,
        perspective=state.perspective,
        language=state.language,
        narrator_tone=state.narrator_tone,
        story_arc=state.story_arc,
        summary=state.summary,
        past=_append_past_line(state.past, past_line),
        current_state=current_state,
        future_plan=future_plan,
        references=state.references,
    )


def write_story_language(path: Path, language: str) -> str:
    """Update the language section in story.md. Returns normalized code."""
    normalized = normalize_story_language(language)
    if not normalized:
        raise ValueError(f"Unsupported language: {language}")
    with _FILE_LOCK:
        content = path.read_text(encoding="utf-8")
        content = _replace_section(content, "language", normalized)
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    return normalized


def write_story_updates(
    path: Path,
    state: StoryState,
    *,
    past_append: str | None = None,
    segment_id: int | None = None,
    current_state: str | None = None,
    future_plan: str | None = None,
) -> StoryState:
    """Atomically update story.md with segment results."""
    with _FILE_LOCK:
        content = path.read_text(encoding="utf-8")
        updated = parse_story_md(content)

        if past_append is not None and segment_id is not None:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            line = f"- [{timestamp}] #{segment_id}: {past_append}"
            new_past = _append_past_line(updated.past, line)
            content = _replace_section(content, "past", new_past)
            updated.past = new_past

        if current_state is not None:
            content = _replace_section(content, "current_state", current_state)
            updated.current_state = current_state

        if future_plan is not None:
            content = _replace_section(content, "future_plan", future_plan)
            updated.future_plan = future_plan

        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)

        return updated


def past_line_count(past: str) -> int:
    stripped = past.strip()
    if stripped in EMPTY_PAST_MARKERS:
        return 0
    return len([line for line in stripped.splitlines() if line.strip()])


def split_past_for_archive(past: str, keep_lines: int) -> tuple[list[str], list[str]]:
    """Split past into lines to fold into summary and lines to keep."""
    stripped = past.strip()
    if stripped in EMPTY_PAST_MARKERS:
        return [], []
    lines = [line for line in stripped.splitlines() if line.strip()]
    if len(lines) <= keep_lines:
        return [], lines
    return lines[:-keep_lines], lines[-keep_lines:]


def join_past_lines(lines: list[str]) -> str:
    if not lines:
        return "*(no events yet)*"
    return "\n".join(lines)


def story_arc_section_present(content: str) -> bool:
    """True when story.md contains a ## story_arc heading."""
    return bool(re.search(r"^##\s+story_arc\s*$", content, re.MULTILINE | re.IGNORECASE))


def story_arc_for_prompt(story_arc: str) -> str:
    """Return story arc body for LLM prompts, or empty when unset."""
    stripped = story_arc.strip()
    if stripped in EMPTY_STORY_ARC_MARKERS:
        return ""
    return stripped


def write_story_arc(path: Path, story_arc: str) -> StoryState:
    """Replace the story_arc section after a tier-3 refresh."""
    with _FILE_LOCK:
        content = path.read_text(encoding="utf-8")
        content = _replace_section(content, "story_arc", story_arc)
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
        return parse_story_md(content)


def summary_for_prompt(summary: str, max_words: int = 350) -> str:
    stripped = summary.strip()
    if stripped in EMPTY_SUMMARY_MARKERS:
        return "(none)"
    words = stripped.split()
    if len(words) <= max_words:
        return stripped
    return " ".join(words[:max_words]) + " …"


def write_story_compact(path: Path, *, summary: str, past: str) -> StoryState:
    """Replace summary and past after folding archived events into the summary."""
    with _FILE_LOCK:
        content = path.read_text(encoding="utf-8")
        content = _replace_section(content, "summary", summary)
        content = _replace_section(content, "past", past)
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
        return parse_story_md(content)


def past_for_prompt(past: str, max_lines: int = 12) -> str:
    """Return only recent past lines for LLM prompts (full past stays in story.md)."""
    stripped = past.strip()
    if stripped in EMPTY_PAST_MARKERS:
        return stripped
    lines = [line for line in stripped.splitlines() if line.strip()]
    if len(lines) <= max_lines:
        return stripped
    omitted = len(lines) - max_lines
    recent = "\n".join(lines[-max_lines:])
    return f"({omitted} earlier events omitted)\n{recent}"


def references_for_prompt(references: str) -> str:
    """Strip comments and blank lines from references for prompts."""
    lines = []
    for line in references.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
            continue
        lines.append(line)
    return "\n".join(lines) if lines else ""


def truncate_segment_text(text: str, max_words: int = 200) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    truncated = " ".join(words[:max_words])
    for sep in (". ", "! ", "? "):
        idx = truncated.rfind(sep)
        if idx > 0:
            return truncated[: idx + 1].strip()
    return truncated


def derive_past_append(segment_text: str, *, max_chars: int = _PAST_APPEND_MAX_CHARS) -> str:
    """One-line past log derived from the narrated segment (first sentence)."""
    text = " ".join(segment_text.split()).strip()
    if not text:
        return ""

    sentence = text
    for i, char in enumerate(text):
        if char in ".!?" and (i == len(text) - 1 or text[i + 1].isspace()):
            sentence = text[: i + 1].strip()
            break

    if len(sentence) > max_chars:
        return sentence[: max_chars - 1].rstrip() + "…"
    return sentence


def max_past_segment_id(past: str) -> int:
    """Highest #N segment id already present in the past log."""
    stripped = past.strip()
    if stripped in EMPTY_PAST_MARKERS:
        return 0
    ids = [int(match.group(1)) for match in _PAST_SEGMENT_ID_RE.finditer(past)]
    return max(ids) if ids else 0


def next_segment_id(past: str) -> int:
    """Next segment id — continues across restarts from existing past lines."""
    return max_past_segment_id(past) + 1
