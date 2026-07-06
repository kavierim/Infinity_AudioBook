"""Optional JSONL logging of LLM prompts and responses."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TRAFFIC_FILENAME = "traffic.jsonl"


class LLMDebugLogger:
    """Append-only logger for LLM traffic when debug is enabled."""

    def __init__(self, log_dir: Path, *, enabled: bool = False) -> None:
        self._enabled = enabled
        self._log_dir = log_dir
        self._log_path = log_dir / TRAFFIC_FILENAME
        self._lock = threading.Lock()
        self._sequence = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def log_path(self) -> Path:
        return self._log_path

    def log_exchange(
        self,
        *,
        provider: str,
        model: str | None,
        operation: str,
        prompt: str,
        response: str = "",
        error: str | None = None,
        tier: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        if not self._enabled:
            return

        with self._lock:
            self._sequence += 1
            record: dict[str, Any] = {
                "seq": self._sequence,
                "ts": datetime.now(timezone.utc).isoformat(),
                "provider": provider,
                "model": model,
                "operation": operation,
                "prompt": prompt,
                "response": response,
            }
            if tier:
                record["tier"] = tier
            if error:
                record["error"] = error
            if extra:
                record.update(extra)

            self._log_dir.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.info("LLM debug: logged %s exchange #%d to %s", operation, self._sequence, self._log_path)


def debug_enabled_from_env() -> bool:
    import os

    return os.environ.get("AUDIOBOOK_DEBUG_LLM", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def parse_debug_flag(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class PipelineActivityLogger:
    """Console activity lines when debug_traffic is enabled."""

    def __init__(self, *, enabled: bool = False) -> None:
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def log(self, message: str, *args: object) -> None:
        if not self._enabled:
            return
        logger.info("[activity] " + message, *args)
