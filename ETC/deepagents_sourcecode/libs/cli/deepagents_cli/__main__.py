"""Module runner for `python -m deepagents_cli`.

This file intentionally does the smallest possible amount of work before
delegating to `deepagents_cli.main.cli_main`.
"""

from deepagents_cli.main import cli_main

if __name__ == "__main__":
    cli_main()
