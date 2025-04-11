"""Main CLI entry point."""
import os
from pathlib import Path

from erasmus.cli.commands import cli
from erasmus.utils.logging import init_logging


def main():
    """Main entry point for the CLI."""
    # Set up logging
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_dir = Path.home() / ".erasmus" / "logs"
    init_logging(level=log_level, log_dir=log_dir)

    # Run CLI
    cli(auto_envvar_prefix='ERASMUS')

if __name__ == '__main__':
    main()
