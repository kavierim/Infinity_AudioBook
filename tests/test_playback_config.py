"""Tests for playback settings."""

from __future__ import annotations

from pathlib import Path

from infinity_audiobook.playback_config import (
    DEFAULT_MAX_BUFFER_SECONDS,
    DEFAULT_SEGMENT_GAP_SECONDS,
    PrefetchAccounting,
    buffer_below_limit,
    estimate_segment_audio_samples,
    load_playback_config,
    max_buffer_samples,
)


def test_missing_file_uses_default(tmp_path: Path) -> None:
    config = load_playback_config(tmp_path / "missing.ini")
    assert config.segment_gap_seconds == DEFAULT_SEGMENT_GAP_SECONDS


def test_missing_playback_section_uses_default(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[story]\nlanguage = en\n", encoding="utf-8")
    config = load_playback_config(ini)
    assert config.segment_gap_seconds == DEFAULT_SEGMENT_GAP_SECONDS


def test_load_segment_gap_from_ini(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[playback]\nsegment_gap_seconds = 0.75\n", encoding="utf-8")
    config = load_playback_config(ini)
    assert config.segment_gap_seconds == 0.75


def test_invalid_gap_falls_back_to_default(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[playback]\nsegment_gap_seconds = not-a-number\n", encoding="utf-8")
    config = load_playback_config(ini)
    assert config.segment_gap_seconds == DEFAULT_SEGMENT_GAP_SECONDS


def test_negative_gap_clamped_to_zero(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[playback]\nsegment_gap_seconds = -2\n", encoding="utf-8")
    config = load_playback_config(ini)
    assert config.segment_gap_seconds == 0.0


def test_load_max_buffer_seconds_from_ini(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[playback]\nmax_buffer_seconds = 120\n", encoding="utf-8")
    config = load_playback_config(ini)
    assert config.max_buffer_seconds == 120.0


def test_default_max_buffer_seconds(tmp_path: Path) -> None:
    ini = tmp_path / "settings.ini"
    ini.write_text("[playback]\nsegment_gap_seconds = 1.0\n", encoding="utf-8")
    config = load_playback_config(ini)
    assert config.max_buffer_seconds == DEFAULT_MAX_BUFFER_SECONDS


def test_buffer_below_limit() -> None:
    cap = max_buffer_samples(60.0)
    assert buffer_below_limit(0, 60.0) is True
    assert buffer_below_limit(cap - 1, 60.0) is True
    assert buffer_below_limit(cap, 60.0) is False
    assert buffer_below_limit(cap + 1_000_000, 60.0) is False


def test_buffer_limit_disabled_when_zero() -> None:
    assert buffer_below_limit(99_999_999, 0.0) is True


def test_estimate_segment_audio_samples_includes_gap() -> None:
    est = estimate_segment_audio_samples("one two three", gap_seconds=1.0)
    assert est > 24_000


def test_prefetch_accounting_totals() -> None:
    buffer = [100]
    accounting = PrefetchAccounting(lambda: buffer[0])
    accounting.on_text_queued(500)
    accounting.on_audio_queued(200)
    assert accounting.total_samples() == 800
    accounting.on_text_dequeued(500)
    accounting.on_audio_dequeued(200)
    assert accounting.total_samples() == 100
