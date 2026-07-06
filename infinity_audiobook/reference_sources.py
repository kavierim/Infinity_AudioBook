"""Load local reference files cited in story.md for LLM prompts."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from infinity_audiobook.story_state import references_for_prompt

logger = logging.getLogger(__name__)

REFERENCE_FILE_MAX_BYTES = 8192

_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_LOCAL_PATH_RE = re.compile(
    r"(?<![\w./])(?:\./)?sources/[^\s\)\]>]+",
    re.IGNORECASE,
)

_BINARY_SUFFIXES = frozenset(
    {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".zip",
        ".gz",
        ".wav",
        ".mp3",
        ".mp4",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
    }
)


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _extract_local_paths(line: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    for match in _MARKDOWN_LINK_RE.finditer(line):
        target = match.group(1).strip()
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        if target not in seen:
            seen.add(target)
            paths.append(target)

    for match in _LOCAL_PATH_RE.finditer(line):
        target = match.group(0).strip()
        if target not in seen:
            seen.add(target)
            paths.append(target)

    return paths


def _load_reference_file(
    project_root: Path,
    ref_path: str,
    *,
    max_bytes: int,
) -> str | None:
    normalized = ref_path.replace("\\", "/").lstrip("./")
    resolved = (project_root / normalized).resolve()
    root = project_root.resolve()

    if not _is_within_root(resolved, root):
        logger.warning("Skipping reference outside project root: %s", ref_path)
        return None
    if not resolved.is_file():
        logger.debug("Reference file not found: %s", ref_path)
        return None

    suffix = resolved.suffix.lower()
    if suffix in _BINARY_SUFFIXES:
        return f"[binary file: {ref_path}]"

    try:
        data = resolved.read_bytes()
    except OSError as exc:
        logger.warning("Could not read reference %s: %s", ref_path, exc)
        return f"[unreadable file: {ref_path}]"

    if b"\x00" in data[:512]:
        return f"[binary file: {ref_path}]"

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return f"[binary file: {ref_path}]"

    if len(data) > max_bytes:
        text = text[:max_bytes] + f"\n… (truncated, {len(data)} bytes total)"
    return f"--- begin {ref_path} ---\n{text.rstrip()}\n--- end {ref_path} ---"


def expand_references_for_prompt(
    references: str,
    project_root: Path,
    *,
    max_bytes: int = REFERENCE_FILE_MAX_BYTES,
) -> str:
    """Return references text with inlined plain-text local files under size cap."""
    base = references_for_prompt(references)
    if not base.strip():
        return ""

    output_lines: list[str] = []
    loaded: set[str] = set()

    for line in base.splitlines():
        output_lines.append(line)
        for ref_path in _extract_local_paths(line):
            if ref_path in loaded:
                continue
            loaded.add(ref_path)
            block = _load_reference_file(project_root, ref_path, max_bytes=max_bytes)
            if block:
                output_lines.append(block)

    return "\n".join(output_lines)
