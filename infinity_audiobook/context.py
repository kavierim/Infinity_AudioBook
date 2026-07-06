"""Thread-safe in-memory instruction state."""

from __future__ import annotations

import threading


class Context:
    """Stores the latest user direction for the next LLM call."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current_instruction: str = ""

    def set_instruction(self, text: str) -> None:
        with self._lock:
            self._current_instruction = text

    def get_and_clear_instruction(self) -> str:
        with self._lock:
            instruction = self._current_instruction
            self._current_instruction = ""
            return instruction

    def peek_instruction(self) -> str:
        with self._lock:
            return self._current_instruction
