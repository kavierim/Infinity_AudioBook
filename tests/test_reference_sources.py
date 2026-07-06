"""Tests for local reference file loading into prompts."""

from __future__ import annotations

from pathlib import Path

from infinity_audiobook.reference_sources import (
    REFERENCE_FILE_MAX_BYTES,
    expand_references_for_prompt,
)


def test_inlines_markdown_linked_text_file(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    note = sources / "chapter-01.md"
    note.write_text("# Chapter 1\nKey fact about the coast.", encoding="utf-8")

    refs = "- [Chapter 1](./sources/chapter-01.md)"
    expanded = expand_references_for_prompt(refs, tmp_path)
    assert "Key fact about the coast" in expanded
    assert "--- begin ./sources/chapter-01.md ---" in expanded


def test_skips_http_links(tmp_path: Path) -> None:
    refs = "- https://en.wikipedia.org/wiki/Example"
    expanded = expand_references_for_prompt(refs, tmp_path)
    assert expanded == "- https://en.wikipedia.org/wiki/Example"
    assert "--- begin" not in expanded


def test_binary_file_referenced_by_path_only(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    pdf = sources / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    refs = "- [Paper](./sources/paper.pdf)"
    expanded = expand_references_for_prompt(refs, tmp_path)
    assert "[binary file: ./sources/paper.pdf]" in expanded


def test_truncates_large_text_files(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    big = sources / "notes.txt"
    big.write_text("x" * (REFERENCE_FILE_MAX_BYTES + 100), encoding="utf-8")

    refs = "- ./sources/notes.txt"
    expanded = expand_references_for_prompt(refs, tmp_path)
    assert "truncated" in expanded
    assert len(expanded) < REFERENCE_FILE_MAX_BYTES + 200


def test_rejects_paths_outside_project(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    refs = f"- [x](../{outside.name})"
    expanded = expand_references_for_prompt(refs, tmp_path)
    assert "secret" not in expanded
