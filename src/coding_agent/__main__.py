"""WebUI entry point for the Coding AI Agent."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

from coding_agent.config import settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Coding AI Agent WebUI")
    parser.add_argument(
        "--memory-dir",
        type=str,
        default=None,
        help="Override memory persistence directory",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)

    if args.memory_dir:
        settings.memory_dir = Path(args.memory_dir)

    webui_path = os.path.join(os.path.dirname(__file__), "webui", "app.py")
    env = os.environ.copy()
    if args.debug:
        env["CODING_AGENT_DEBUG"] = "1"
    env.setdefault("PYTHONUNBUFFERED", "1")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            webui_path,
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
            "--logger.level",
            "debug" if args.debug else "info",
        ],
        env=env,
        check=True,
    )


if __name__ == "__main__":
    main()
