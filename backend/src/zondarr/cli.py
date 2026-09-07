"""Serve the application through the installed Granian command."""

import sys

from granian.cli import cli as granian_cli


def main() -> None:
    """Supply the application target while preserving Granian's server options."""
    granian_cli.main(
        args=[*sys.argv[1:], "--interface", "asgi", "zondarr.app:app"],
        prog_name="zondarr",
    )
