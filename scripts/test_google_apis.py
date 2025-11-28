# scripts/test_google_apis.py

from __future__ import annotations

import os
import sys
from pathlib import Path

import textwrap

# Optional but recommended: load .env explicitly
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


ROOT = Path(__file__).resolve().parents[1]  # repo root


def load_env():
    """
    Ensure environment variables from .env are available to this process.
    1. If python-dotenv is installed, load ROOT/.env.
    2. Otherwise, rely on shell-exported env vars.
    """
    dotenv_path = ROOT / ".env"
    if load_dotenv is not None and dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path, override=False)


def check_required_env():
    required = ["GOOGLE_MAPS_API_KEY", "GEMINI_API_KEY"]
    missing = [name for name in required if not os.environ.get(name)]

    print("============================================================")
    print("1. Checking environment variables")
    print("============================================================")

    print("\nCurrent values (repr):")
    for name in required:
        print(f"  {name} = {repr(os.environ.get(name))}")

    if missing:
        print(f"\n❌ FAIL: Missing required env vars: {missing}")
        return False
    else:
        print("\n✅ OK: All required env vars are present.")
        return True


def main():
    print("\n============================================================")
    print("Running Google API Integration Tests")
    print("============================================================\n")

    load_env()

    ok_env = check_required_env()

    if not ok_env:
        print(
            textwrap.dedent(
                """
                ------------------------------------------------------------
                Troubleshooting tips:
                - Ensure .env is in the repo root: {root}
                - Ensure it contains lines like:
                    GOOGLE_MAPS_API_KEY=your_key_here
                    GEMINI_API_KEY=your_key_here
                - If you change .env and are relying on `source .env`, make sure
                  you re-run `source .env` in THIS terminal after edits.
                - Or just rely on this script loading .env via python-dotenv.
                ------------------------------------------------------------
                """
            ).format(root=str(ROOT))
        )
        sys.exit(1)

    print("\n(All good on env vars. Next steps would be live API calls here.)")


if __name__ == "__main__":
    main()
