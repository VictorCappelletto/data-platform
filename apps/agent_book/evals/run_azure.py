"""Run the golden set against Azure OpenAI (opt-in, billed)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]
for path in (REPO_ROOT, APP_ROOT):
    if path.is_dir() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dotenv import load_dotenv  # noqa: E402

from evals.runner import azure_ready  # noqa: E402


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    if not azure_ready():
        print("Azure OpenAI env missing (AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY).")
        return 1
    os.environ["AGENT_BOOK_EVAL_AZURE"] = "1"
    import pytest

    return pytest.main(
        [
            f"{APP_ROOT / 'tests' / 'test_eval.py'}::test_golden_eval_azure",
            "-q",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
