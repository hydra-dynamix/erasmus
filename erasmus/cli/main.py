"""Main CLI entry point."""
import click

from .setup import setup

@click.group()
def cli():
    """Erasmus - AI Context Watcher for Development."""
    pass

# Register commands
cli.add_command(setup)

if __name__ == '__main__':
    cli() 