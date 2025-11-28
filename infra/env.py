# infra/env.py

from __future__ import annotations

import functools
from pathlib import Path

from dotenv import load_dotenv


@functools.lru_cache()
def ensure_env_loaded() -> None:
    """
    Load environment variables from the project root .env file exactly once.

    We assume the repo is run from anywhere under the root, so we resolve
    the repo root as the parent of the `infra/` directory and look for `.env`
    there:
        <repo_root>/.env
    """
    repo_root = Path(__file__).resolve().parents[1]
    env_path = repo_root / ".env"

    # This will quietly no-op if .env is missing
    load_dotenv(dotenv_path=env_path)
