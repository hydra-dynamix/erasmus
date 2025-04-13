"""Erasmus CLI entry point."""

import click
import logging
import os
from pathlib import Path

from erasmus.utils.paths import SetupPaths
from erasmus.utils.logging import get_logger
from erasmus.cli.commands import cli

logger = get_logger(__name__)


def get_setup_paths(project_root: Path = None) -> SetupPaths:
    """Get a SetupPaths instance.

    Args:
        project_root: Optional project root path. If not provided, uses current directory.

    Returns:
        SetupPaths: A SetupPaths instance
    """
    return SetupPaths.with_project_root(project_root or Path.cwd())


def main():
    """Main entry point for the Erasmus CLI."""
    # Initialize setup paths
    setup_paths = get_setup_paths()

    # Ensure directories exist
    setup_paths.ensure_directories()

    # Run the CLI
    cli()


if __name__ == "__main__":
    main()
