"""Tests for main entry validation."""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from infinity_audiobook.main import PROJECT_ROOT, main, run_pipeline
from infinity_audiobook.story_config import StoryConfig


def test_run_pipeline_validates_assets(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_pipeline(
            story_path=tmp_path / "story.md",
            project_root=tmp_path,
            skip_tts_load=True,
            skip_ui=True,
        )


def test_run_pipeline_starts_with_mocks() -> None:
    if not (PROJECT_ROOT / "assets" / "speaker_reference.wav").is_file():
        pytest.skip("Reference assets missing")

    def fake_ui_runner(shutdown_event: threading.Event, **kwargs) -> None:
        shutdown_event.set()

    with patch("infinity_audiobook.main.TTSEngine") as mock_tts_cls:
        mock_tts = MagicMock()
        mock_tts_cls.return_value = mock_tts
        with patch("infinity_audiobook.main.create_llm_client") as mock_create_llm:
            mock_llm = MagicMock()
            mock_create_llm.return_value = mock_llm
            with patch("infinity_audiobook.main.Player") as mock_player_cls:
                mock_player = MagicMock()
                mock_player.buffer.pending_samples.return_value = 0
                mock_player_cls.return_value = mock_player
                with patch("infinity_audiobook.main.run_text_producer") as mock_text:
                    mock_text.return_value = MagicMock()
                    with patch("infinity_audiobook.main.run_audio_producer") as mock_audio:
                        mock_audio.return_value = MagicMock()
                        run_pipeline(
                            skip_tts_load=True,
                            skip_ui=False,
                            ui_runner=fake_ui_runner,
                            story_config=StoryConfig(language="en"),
                        )

    mock_tts.load.assert_not_called()
    mock_player.start.assert_called_once()


def test_main_version_flag(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        with patch("sys.argv", ["infinity-audiobook", "--version"]):
            main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "0.1.0" in captured.out
