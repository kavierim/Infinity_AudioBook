"""Tests for .env loading."""

from __future__ import annotations

import os
from pathlib import Path

from infinity_audiobook.env import load_project_env


def test_load_project_env_reads_gemini_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=from-dotenv\n", encoding="utf-8")

    assert load_project_env(tmp_path) is True
    assert os.environ.get("GEMINI_API_KEY") == "from-dotenv"


def test_load_project_env_missing_file_returns_false(tmp_path: Path) -> None:
    assert load_project_env(tmp_path) is False


def test_load_project_env_does_not_override_existing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "already-set")
    (tmp_path / ".env").write_text("GEMINI_API_KEY=from-dotenv\n", encoding="utf-8")

    load_project_env(tmp_path)
    assert os.environ.get("GEMINI_API_KEY") == "already-set"
