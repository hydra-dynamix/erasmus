"""Erasmus CLI entry point."""

from pathlib import Path

from erasmus.utils.paths import SetupPaths
from erasmus.utils.logging import get_logger
from erasmus.cli.commands import cli
from erasmus.inference import ErasmusInference
import click
import asyncio

logger = get_logger(__name__)


def get_setup_paths(project_root: Path = None) -> SetupPaths:
    """Get a SetupPaths instance.

    Args:
        project_root: Optional project root path. If not provided, uses current directory.

    Returns:
        SetupPaths: A SetupPaths instance
    """
    return SetupPaths.with_project_root(project_root or Path.cwd())

@click.group()
def main():
    """Main entry point for the Erasmus CLI."""
    # Initialize setup paths
    setup_paths = get_setup_paths()
    setup_paths.ensure_directories()

@main.command()
@click.option('--message', '-m', multiple=True, help='Message(s) for chat.')
def inference(message):
    """Run a chat/inference session with tool call support."""
    ei = ErasmusInference()
    messages = [{"role": "user", "content": m} for m in message]
    async def run():
        result = await ei.chat(messages)
        print(result)
    asyncio.run(run())

main.add_command(cli)

if __name__ == "__main__":
    main()
