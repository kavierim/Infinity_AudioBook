"""Load API keys and secrets from a project-root .env file."""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def load_project_env(project_root: Path) -> bool:
    """Load `.env` from *project_root* if present.

    Existing process environment variables are not overwritten.
    Returns True when a `.env` file was found and loaded.
    """
    env_path = project_root / ".env"
    if not env_path.is_file():
        return False
    load_dotenv(env_path, override=False)
    logger.debug("Loaded environment from %s", env_path)
    return True
