"""Main CLI entry point."""
import click

from erasmus.cli.commands import cli


def main():
    """Main entry point for the CLI."""
    cli(auto_envvar_prefix='ERASMUS')

if __name__ == '__main__':
    main()