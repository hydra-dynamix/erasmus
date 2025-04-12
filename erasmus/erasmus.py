import argparse
import asyncio
from pathlib import Path
from typing import Optional

from erasmus.utils.protocols.cli import add_protocol_commands, handle_protocol_commands
from erasmus.utils.logging import get_logger

logger = get_logger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(description="Erasmus: AI Context Watcher for Development.")

    # Create subparsers for different command groups
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add protocol commands
    protocol_parser = subparsers.add_parser("protocol", help="Protocol management commands")
    add_protocol_commands(protocol_parser)

    # Add other command groups
    subparsers.add_parser(
        "cleanup", help="Remove all generated files and restore backups if available"
    )
    subparsers.add_parser("context", help="Context management commands")
    subparsers.add_parser("git", help="Git operations")
    subparsers.add_parser(
        "setup", help="Set up a new project with necessary files and configuration"
    )
    subparsers.add_parser("task", help="Task management commands")
    subparsers.add_parser("update", help="Update project files")
    subparsers.add_parser("watch", help="Watch project files for changes")

    return parser


async def main() -> None:
    """Main entry point for the Erasmus CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "protocol":
        await handle_protocol_commands(args)
        return

    # Handle other commands...
    logger.info(f"Command '{args.command}' not yet implemented")


if __name__ == "__main__":
    asyncio.run(main())
