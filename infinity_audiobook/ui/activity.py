"""Activity ring buffer and logging integration for the TUI."""

from __future__ import annotations

import logging
import threading
from collections import deque

from infinity_audiobook.llm_debug import PipelineActivityLogger

logger = logging.getLogger(__name__)

DEFAULT_ACTIVITY_RING_SIZE = 200


class ActivityRing:
    """Fixed-size ring buffer of activity log lines."""

    def __init__(self, capacity: int = DEFAULT_ACTIVITY_RING_SIZE) -> None:
        self._capacity = capacity
        self._lock = threading.Lock()
        self._lines: deque[str] = deque(maxlen=capacity)

    def append(self, line: str) -> None:
        with self._lock:
            self._lines.append(line)

    def snapshot(self) -> list[str]:
        with self._lock:
            return list(self._lines)


class UIActivityLogger(PipelineActivityLogger):
    """Pipeline activity always visible in the TUI activity panel."""

    def __init__(
        self,
        ring: ActivityRing,
        *,
        debug_to_logger: bool = False,
    ) -> None:
        super().__init__(enabled=debug_to_logger)
        self._ring = ring

    def log(self, message: str, *args: object) -> None:
        formatted = message % args if args else message
        self._ring.append(formatted)
        if self.enabled:
            logger.info("[activity] %s", formatted)


class ActivityLogHandler(logging.Handler):
    """Route WARNING+ log records to the activity panel (no stdout interleaving)."""

    def __init__(self, ring: ActivityRing) -> None:
        super().__init__(level=logging.WARNING)
        self._ring = ring

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._ring.append(self.format(record))
        except Exception:
            self.handleError(record)


def configure_tui_logging(ring: ActivityRing) -> None:
    """Replace root handlers so WARNING+ goes to the activity ring only."""
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    handler = ActivityLogHandler(ring)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(handler)
    if root.level == logging.NOTSET:
        root.setLevel(logging.INFO)
