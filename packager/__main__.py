"""
Python Script Packager CLI

This module provides the command-line interface for the Python Script Packager.
It uses typer to create a modern CLI that packages Python projects into standalone
scripts with automatic dependency management using uv.
"""

import logging
import sys
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
import click

from .builder import generate_script
from .collector import collect_py_files
from .mapping import map_imports_to_packages
from .parser import extract_imports

# Set up logging with rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("packager")
console = Console()


@click.group()
def cli():
    """Python Script Packager CLI."""
    pass


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    help="Output file path. If not provided, will use input name + '_packed.py'",
)
@click.option(
    "--no-comments",
    is_flag=True,
    help="Strip comments from the output",
)
@click.option(
    "--build-dir",
    type=click.Path(),
    default="build",
    help="Build directory for output files",
)
def package(
    input_path: str, output: str = None, no_comments: bool = False, build_dir: str = "build"
):
    """Package a Python project into a single script."""
    try:
        # Ensure build directory exists
        build_path = Path(build_dir)
        build_path.mkdir(parents=True, exist_ok=True)

        # If no output path specified, create one in the build directory
        if not output:
            input_name = Path(input_path).stem
            output = str(build_path / f"{input_name}_packed.py")
        else:
            # If output path is provided, ensure it's in the build directory
            output = str(build_path / Path(output).name)

        # Generate the script
        result = generate_script(
            input_path,
            output,
            preserve_comments=not no_comments,
        )

        if result:
            console.print(f"[green]✨ Successfully packaged script to {output}")
        else:
            console.print("[red]❌ Failed to package script")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}")
        sys.exit(1)


@cli.command()
def list_files(
    directory: Path = typer.Argument(
        ...,
        help="Directory to scan for Python files",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
):
    """List all Python files that would be included in packaging."""
    try:
        files = collect_py_files(directory)
        if not files:
            console.print("[yellow]No Python files found in directory.[/]")
            return

        console.print("\n[bold]Python files found:[/]")
        for file in files:
            console.print(f"  • {file}")
        console.print(f"\nTotal: {len(files)} files")

    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}", style="bold red")
        raise typer.Exit(1)


def run():
    """Entry point for the packager CLI.

    This function is used by the entry point script to run the CLI.
    It simply calls the main() function which runs the Click CLI.
    """
    return main()


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
