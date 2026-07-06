"""Textual full-screen dashboard — the only user-facing interface."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from queue import Queue

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, RichLog, Static, TabbedContent, TabPane

from infinity_audiobook.context import Context
from infinity_audiobook.llm_config import LLMConfig
from infinity_audiobook.models import SAMPLE_RATE
from infinity_audiobook.story_state import (
    EMPTY_PAST_MARKERS,
    EMPTY_STORY_ARC_MARKERS,
    EMPTY_SUMMARY_MARKERS,
    read_story,
    situation_for_prompt,
)
from infinity_audiobook.ui.activity import ActivityRing, configure_tui_logging
from infinity_audiobook.ui.snapshot import UISnapshot
from infinity_audiobook.ui.theme import AUDIOBOOK_THEME

_EMPTY_MARKUP = "[dim italic](empty)[/]"


def _display_body(text: str, empty_markers: frozenset[str] | set[str]) -> str:
    stripped = text.strip()
    if stripped in empty_markers or not stripped:
        return _EMPTY_MARKUP
    return stripped


def _format_activity_line(line: str) -> str:
    upper = line.upper()
    if "ERROR" in upper:
        return f"[bold $error]✗[/] [red]{line}[/]"
    if "WARNING" in upper:
        return f"[bold $warning]![/] [yellow]{line}[/]"
    if "generating segment" in line.lower():
        return f"[bold $accent]◆[/] [cyan]{line}[/]"
    if any(token in line.lower() for token in ("queued", "synthesiz", "playing", "loaded")):
        return f"[bold $success]▸[/] [green]{line}[/]"
    return f"[dim]·[/] {line}"


def _format_transcript(entries: list) -> str:
    blocks = [f"[bold $accent]#{entry.segment_id}[/]\n{entry.text}" for entry in entries]
    return "\n\n".join(blocks)


def _format_status_bar(
    *,
    llm_summary: str,
    text_qsize: int,
    audio_qsize: int,
    buffer_seconds: float,
    instruction: str,
) -> str:
    if buffer_seconds >= 5.0:
        buffer_style = "green"
    elif buffer_seconds >= 1.0:
        buffer_style = "yellow"
    else:
        buffer_style = "red"

    if instruction == "(none)":
        direction = "[dim](none)[/]"
    else:
        direction = f"[bold $accent]{instruction}[/]"

    return (
        f"[bold]LLM[/] {llm_summary}   "
        f"[bold]Queues[/] "
        f"text [cyan]{text_qsize}[/] · audio [cyan]{audio_qsize}[/]   "
        f"[bold]Buffer[/] [{buffer_style}]{buffer_seconds:.1f}s[/]   "
        f"[bold]Direction[/] {direction}"
    )


class InfinityAudioBookApp(App[None]):
    """Full-screen TUI for story state, transcript, and pipeline activity."""

    TITLE = "InfinityAudioBook"
    SUB_TITLE = "infinite narrative · live audiobook"
    CSS_PATH = Path(__file__).with_name("audiobook.tcss")

    BINDINGS = [
        Binding("q", "request_quit", "Quit"),
        Binding("ctrl+c", "request_quit", "Quit", show=False),
    ]

    def __init__(
        self,
        *,
        snapshot: UISnapshot,
        context: Context,
        shutdown_event: threading.Event,
        story_path: Path,
        text_queue: Queue,
        audio_queue: Queue,
        buffer_samples_fn: Callable[[], int],
        llm_config: LLMConfig,
        activity_ring: ActivityRing,
    ) -> None:
        super().__init__()
        self.register_theme(AUDIOBOOK_THEME)
        self.theme = AUDIOBOOK_THEME.name
        self._snapshot = snapshot
        self._instruction_context = context
        self._shutdown_event = shutdown_event
        self._story_path = story_path
        self._text_queue = text_queue
        self._audio_queue = audio_queue
        self._buffer_samples_fn = buffer_samples_fn
        self._llm_config = llm_config
        self._activity_ring = activity_ring
        self._last_activity_count = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="status-bar", markup=True)
        with Horizontal(id="main-row"):
            with Vertical(id="left-col", classes="story-panel"):
                yield Static("Summary", classes="panel-title")
                with VerticalScroll(classes="panel-scroll"):
                    yield Static(_EMPTY_MARKUP, id="summary-panel", classes="panel-body")
            with Vertical(id="right-col", classes="story-panel"):
                yield Static("Storyline", classes="panel-title")
                with TabbedContent():
                    with TabPane("Arc", id="tab-arc"):
                        with VerticalScroll(classes="panel-scroll"):
                            yield Static(_EMPTY_MARKUP, id="arc-panel", classes="panel-body")
                    with TabPane("Now", id="tab-state"):
                        with VerticalScroll(classes="panel-scroll"):
                            yield Static(_EMPTY_MARKUP, id="state-panel", classes="panel-body")
                    with TabPane("Plan", id="tab-plan"):
                        with VerticalScroll(classes="panel-scroll"):
                            yield Static(_EMPTY_MARKUP, id="plan-panel", classes="panel-body")
        with Horizontal(id="bottom-row"):
            with Vertical(id="past-col", classes="story-panel"):
                yield Static("Past", classes="panel-title")
                with VerticalScroll(classes="panel-scroll"):
                    yield Static(_EMPTY_MARKUP, id="past-panel", classes="panel-body")
            with Vertical(id="transcript-col", classes="story-panel"):
                yield Static("Transcript", classes="panel-title")
                with VerticalScroll(classes="panel-scroll"):
                    yield Static(_EMPTY_MARKUP, id="transcript-panel", classes="panel-body")
        with Vertical(id="activity-section"):
            yield Static("Pipeline", id="activity-header")
            yield RichLog(id="activity-log", highlight=True, markup=True, wrap=True)
        with Horizontal(id="prompt-row"):
            yield Static("›", id="prompt-glyph")
            yield Input(
                placeholder="Steer the story — Enter to submit (replaces pending direction)",
                id="direction-input",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self._refresh_story_panels)
        self.set_interval(0.5, self._refresh_live_panels)
        self._refresh_story_panels()
        self._refresh_live_panels()

    def action_request_quit(self) -> None:
        self._shutdown_event.set()
        self.exit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if text:
            self._instruction_context.set_instruction(text)
        event.input.value = ""
        self._refresh_status_bar()

    def _refresh_story_panels(self) -> None:
        if self._shutdown_event.is_set():
            return
        state = read_story(self._story_path)
        self.query_one("#summary-panel", Static).update(
            _display_body(state.summary, EMPTY_SUMMARY_MARKERS)
        )
        self.query_one("#arc-panel", Static).update(
            _display_body(state.story_arc, EMPTY_STORY_ARC_MARKERS)
        )
        self.query_one("#state-panel", Static).update(
            _display_body(situation_for_prompt(state.current_state), set())
        )
        self.query_one("#plan-panel", Static).update(
            _display_body(state.future_plan, set())
        )
        self.query_one("#past-panel", Static).update(
            _display_body(state.past, EMPTY_PAST_MARKERS)
        )

    def _refresh_live_panels(self) -> None:
        if self._shutdown_event.is_set():
            return
        entries = self._snapshot.transcript_snapshot()
        transcript_text = _format_transcript(entries) if entries else _EMPTY_MARKUP
        self.query_one("#transcript-panel", Static).update(transcript_text)

        activity_lines = self._activity_ring.snapshot()
        if len(activity_lines) != self._last_activity_count:
            log = self.query_one("#activity-log", RichLog)
            new_lines = activity_lines[self._last_activity_count :]
            for line in new_lines:
                log.write(_format_activity_line(line))
            self._last_activity_count = len(activity_lines)

        self._refresh_status_bar()

    def _refresh_status_bar(self) -> None:
        buffer_samples = self._buffer_samples_fn()
        buffer_seconds = buffer_samples / SAMPLE_RATE
        instruction = self._instruction_context.peek_instruction() or "(none)"
        status = _format_status_bar(
            llm_summary=self._llm_config.summary(),
            text_qsize=self._text_queue.qsize(),
            audio_qsize=self._audio_queue.qsize(),
            buffer_seconds=buffer_seconds,
            instruction=instruction,
        )
        self.query_one("#status-bar", Static).update(status)


def run_tui_app(
    *,
    snapshot: UISnapshot,
    context: Context,
    shutdown_event: threading.Event,
    story_path: Path,
    text_queue: Queue,
    audio_queue: Queue,
    buffer_samples_fn: Callable[[], int],
    llm_config: LLMConfig,
    activity_ring: ActivityRing,
) -> None:
    """Run the Textual dashboard on the main thread."""
    configure_tui_logging(activity_ring)
    app = InfinityAudioBookApp(
        snapshot=snapshot,
        context=context,
        shutdown_event=shutdown_event,
        story_path=story_path,
        text_queue=text_queue,
        audio_queue=audio_queue,
        buffer_samples_fn=buffer_samples_fn,
        llm_config=llm_config,
        activity_ring=activity_ring,
    )
    try:
        app.run()
    finally:
        shutdown_event.set()
