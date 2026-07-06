"""Tests for LLM provider settings and factory."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from infinity_audiobook.gemini_tiered import TieredGeminiClient
from infinity_audiobook.llm_config import (
    DEFAULT_GEMINI_MODEL,
    LLMConfig,
    create_llm_client,
    load_llm_config,
)


def test_default_llm_config() -> None:
    config = LLMConfig()
    assert config.provider == "gemini"
    assert config.summary().startswith("gemini tiers:")


def test_gemini_config_summary_uses_default_model() -> None:
    config = LLMConfig(provider="gemini")
    assert config.effective_model_segment() == DEFAULT_GEMINI_MODEL
    assert f"segment={DEFAULT_GEMINI_MODEL}" in config.summary()


def test_load_from_llm_section_gemini(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[llm]\nprovider = gemini\nmodel = gemini-2.5-flash\n", encoding="utf-8")
    config = load_llm_config(ini)
    assert config.provider == "gemini"
    assert config.model == "gemini-2.5-flash"


def test_load_gemini_without_model_uses_default(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[llm]\nprovider = gemini\n", encoding="utf-8")
    config = load_llm_config(ini)
    assert config.model == DEFAULT_GEMINI_MODEL


def test_legacy_cursor_provider_raises(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[llm]\nprovider = cursor\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no longer supported"):
        load_llm_config(ini)


def test_legacy_acp_section_only_raises(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text(
        "[acp]\nprovider = cursor\nmodel = composer-2.5-fast\nmode = ask\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no longer supported"):
        load_llm_config(ini)


def test_llm_section_takes_precedence_over_acp(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text(
        "[llm]\nprovider = gemini\nmodel = gemini-2.5-flash\n"
        "[acp]\nprovider = cursor\nmodel = old-model\n",
        encoding="utf-8",
    )
    config = load_llm_config(ini)
    assert config.provider == "gemini"
    assert config.model == "gemini-2.5-flash"


def test_unknown_llm_provider_raises(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[llm]\nprovider = unknown\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        load_llm_config(ini)


def test_missing_file_uses_defaults(tmp_path: Path) -> None:
    config = load_llm_config(tmp_path / "missing.ini")
    assert config.provider == "gemini"


def test_load_tier_models_from_ini(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text(
        "[llm]\n"
        "provider = gemini\n"
        "model_segment = gemini-2.5-flash\n"
        "model_summary = gemini-2.5-flash-lite\n"
        "model_arc = gemini-2.5-pro\n"
        "arc_refresh_every = 10\n",
        encoding="utf-8",
    )
    config = load_llm_config(ini)
    assert config.model_segment == "gemini-2.5-flash"
    assert config.model_summary == "gemini-2.5-flash-lite"
    assert config.model_arc == "gemini-2.5-pro"
    assert config.arc_refresh_every == 10


def test_single_model_applies_to_all_tiers(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text(
        "[llm]\nprovider = gemini\nmodel = gemini-2.5-flash\n",
        encoding="utf-8",
    )
    config = load_llm_config(ini)
    assert config.model_segment == "gemini-2.5-flash"
    assert config.model_summary == "gemini-2.5-flash"
    assert config.model_arc == "gemini-2.5-flash"


def test_partial_tier_models_fall_back_to_model(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text(
        "[llm]\n"
        "provider = gemini\n"
        "model = gemini-2.5-flash\n"
        "model_arc = gemini-2.5-pro\n",
        encoding="utf-8",
    )
    config = load_llm_config(ini)
    assert config.model_segment == "gemini-2.5-flash"
    assert config.model_summary == "gemini-2.5-flash"
    assert config.model_arc == "gemini-2.5-pro"


def test_arc_refresh_every_defaults_to_20(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[llm]\nprovider = gemini\n", encoding="utf-8")
    config = load_llm_config(ini)
    assert config.arc_refresh_every == 20


def test_arc_refresh_every_zero_disables(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text(
        "[llm]\nprovider = gemini\narc_refresh_every = 0\n",
        encoding="utf-8",
    )
    config = load_llm_config(ini)
    assert config.arc_refresh_every == 0
    assert "arc refresh" not in config.summary()


def test_create_gemini_client(tmp_path: Path) -> None:
    config = LLMConfig(
        provider="gemini",
        model="gemini-2.5-flash",
        model_segment="gemini-2.5-flash",
        model_summary="gemini-2.5-flash-lite",
        model_arc="gemini-2.5-pro",
    )
    with patch("infinity_audiobook.gemini_tiered.TieredGeminiClient") as mock_cls:
        mock_cls.return_value = MagicMock(spec=TieredGeminiClient)
        client = create_llm_client(config, tmp_path / "settings.ini", tmp_path)
        mock_cls.assert_called_once()
        kwargs = mock_cls.call_args.kwargs
        assert kwargs["model_segment"] == "gemini-2.5-flash"
        assert kwargs["model_summary"] == "gemini-2.5-flash-lite"
        assert kwargs["model_arc"] == "gemini-2.5-pro"
        assert kwargs["debug_logger"].enabled is False
        assert client is mock_cls.return_value


def test_load_debug_traffic_from_ini(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text(
        "[llm]\nprovider = gemini\nmodel = gemini-2.5-flash\ndebug_traffic = true\n",
        encoding="utf-8",
    )
    config = load_llm_config(ini)
    assert config.debug_traffic is True
