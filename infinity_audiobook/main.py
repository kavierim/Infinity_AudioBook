"""Entry point — wire pipeline threads and graceful shutdown."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from queue import Queue

from infinity_audiobook import __version__
from infinity_audiobook.env import load_project_env
from infinity_audiobook.settings_paths import SETTINGS_FILENAME
from infinity_audiobook.llm_config import LLMConfig, create_llm_client
from infinity_audiobook.audio_producer import run_audio_producer
from infinity_audiobook.playback_config import PlaybackConfig, PrefetchAccounting
from infinity_audiobook.story_config import StoryConfig
from infinity_audiobook.settings import AppSettings, load_app_settings
from infinity_audiobook.context import Context
from infinity_audiobook.models import AUDIO_QUEUE_MAXSIZE, TEXT_QUEUE_MAXSIZE, AudioChunk, Segment
from infinity_audiobook.player import Player
from infinity_audiobook.story_state import (
    StoryLanguageCache,
    parse_current_state,
    read_story,
    write_story_language,
)
from infinity_audiobook.text_producer import queue_replay_from_story, run_text_producer
from infinity_audiobook.tts import TTSEngine, validate_reference_assets
from infinity_audiobook.ui.activity import ActivityRing, UIActivityLogger
from infinity_audiobook.ui.app import run_tui_app
from infinity_audiobook.ui.snapshot import UISnapshot

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORY_PATH = PROJECT_ROOT / "story.md"

UiRunner = Callable[..., None]


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def run_pipeline(
    *,
    story_path: Path = STORY_PATH,
    project_root: Path = PROJECT_ROOT,
    skip_tts_load: bool = False,
    skip_ui: bool = False,
    ui_runner: UiRunner | None = None,
    language: str | None = None,
    llm_config: LLMConfig | None = None,
    playback_config: PlaybackConfig | None = None,
    story_config: StoryConfig | None = None,
) -> None:
    """Start the full audiobook pipeline."""
    load_project_env(project_root)

    validate_reference_assets(
        project_root / "assets" / "speaker_reference.wav",
        project_root / "assets" / "speaker_reference.txt",
    )

    settings_path = project_root / SETTINGS_FILENAME
    story_state = read_story(story_path)

    app_settings: AppSettings | None = None
    if llm_config is None or playback_config is None or story_config is None:
        app_settings = load_app_settings(
            settings_path,
            default_language=story_state.language,
        )

    llm_settings = llm_config or (app_settings.llm if app_settings else LLMConfig())
    playback_settings = playback_config or (
        app_settings.playback if app_settings else PlaybackConfig()
    )
    story_settings = story_config or (
        app_settings.story if app_settings else StoryConfig(language=story_state.language)
    )

    language_to_apply = language if language is not None else story_settings.language
    if story_state.language != language_to_apply:
        write_story_language(story_path, language_to_apply)
        story_state = read_story(story_path)
        logger.info("Story language set to %s", language_to_apply)

    shutdown_event = threading.Event()
    context = Context()
    snapshot = UISnapshot()
    blocks = parse_current_state(story_state.current_state)
    if blocks.last_narrated and blocks.last_segment_id is not None:
        snapshot.seed_transcript(blocks.last_segment_id, blocks.last_narrated)
    activity_ring = ActivityRing()
    text_queue: Queue[Segment] = Queue(maxsize=TEXT_QUEUE_MAXSIZE)
    audio_queue: Queue[AudioChunk] = Queue(maxsize=AUDIO_QUEUE_MAXSIZE)

    language_cache = StoryLanguageCache(story_path, default=story_state.language)
    language_cache.seed(story_state.language)

    tts = TTSEngine(
        ref_audio=project_root / "assets" / "speaker_reference.wav",
        ref_text_file=project_root / "assets" / "speaker_reference.txt",
    )

    # Load TTS model (downloads weights on first run)
    if not skip_tts_load:
        logger.info("Loading OmniVoice model...")
        tts.load()
        tts.set_language(story_state.language)

    llm_client = create_llm_client(llm_settings, settings_path, project_root)
    activity = UIActivityLogger(
        activity_ring,
        debug_to_logger=llm_settings.debug_traffic,
    )

    player = Player(audio_queue, shutdown_event)
    prefetch = PrefetchAccounting(player.buffer.pending_samples)
    player.bind_prefetch(prefetch)
    player.start()

    prefetch_total = prefetch.total_samples

    queue_replay_from_story(
        story_path,
        text_queue,
        story_state=story_state,
        gap_seconds=playback_settings.segment_gap_seconds,
        prefetch=prefetch,
        activity=activity,
    )

    audio_thread = run_audio_producer(
        text_queue,
        audio_queue,
        shutdown_event,
        tts,
        story_path=story_path,
        language_cache=language_cache,
        gap_seconds=playback_settings.segment_gap_seconds,
        buffer_samples_fn=prefetch_total,
        max_buffer_seconds=playback_settings.max_buffer_seconds,
        prefetch=prefetch,
        activity=activity,
    )

    text_thread = run_text_producer(
        text_queue,
        context,
        story_path,
        shutdown_event,
        llm_client,
        project_root=project_root,
        arc_refresh_every=llm_settings.arc_refresh_every,
        buffer_samples_fn=prefetch_total,
        max_buffer_seconds=playback_settings.max_buffer_seconds,
        gap_seconds=playback_settings.segment_gap_seconds,
        prefetch=prefetch,
        activity=activity,
        snapshot=snapshot,
    )

    def _handle_signal(signum: int, frame: object) -> None:
        logger.info("Signal %s received — shutting down", signum)
        shutdown_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_signal)

    ui_kwargs = dict(
        snapshot=snapshot,
        context=context,
        shutdown_event=shutdown_event,
        story_path=story_path,
        text_queue=text_queue,
        audio_queue=audio_queue,
        buffer_samples_fn=prefetch_total,
        llm_config=llm_settings,
        activity_ring=activity_ring,
    )

    try:
        if skip_ui:
            shutdown_event.wait()
        elif ui_runner is not None:
            ui_runner(**ui_kwargs)
        else:
            run_tui_app(**ui_kwargs)
    finally:
        shutdown_event.set()
        logger.info("Shutting down...")
        player.stop()
        text_thread.join(timeout=5.0)
        audio_thread.join(timeout=5.0)
        if text_thread.is_alive() or audio_thread.is_alive():
            logger.warning(
                "Worker threads did not exit within timeout; "
                "in-flight LLM/TTS may be abandoned"
            )
        logger.info("Goodbye.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="InfinityAudioBook — infinite audiobook player",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.parse_args()

    _configure_logging()
    try:
        run_pipeline()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:
        logger.error("Fatal error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
