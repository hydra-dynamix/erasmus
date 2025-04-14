"""
Python Script Packager CLI

This module provides the command-line interface for the Python Script Packager.
It uses typer to create a modern CLI that packages Python projects into standalone
scripts with automatic dependency management using uv.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel

from .builder import generate_script
from .collector import collect_py_files
from .mapping import map_imports_to_packages
from .parser import extract_imports
from .uv_wrapper import wrap_script

# Set up logging with rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("packager")
console = Console()

app = typer.Typer(
    name="packager",
    help="Package Python projects into standalone scripts with uv dependency management",
    add_completion=False,
)


def version_callback(value: bool):
    """Show the version and exit."""
    if value:
        from . import __version__

        console.print(f"Python Script Packager v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        help="Show version and exit.",
        is_eager=True,
    ),
):
    """Package Python projects into standalone scripts with uv dependency management."""
    pass


@app.command()
def package(
    input_path: Path = typer.Argument(
        ...,
        help="Input Python file or directory to package",
        exists=True,
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (defaults to input name with _packed suffix)",
    ),
    group_imports: bool = typer.Option(
        True,
        "--group-imports/--no-group-imports",
        help="Group imports by type (stdlib, third-party, local)",
    ),
    preserve_comments: bool = typer.Option(
        True,
        "--preserve-comments/--no-comments",
        help="Preserve comments in the output",
    ),
):
    """Package a Python file or directory into a standalone script."""
    try:
        # Set default output path if not provided
        if not output_path:
            if input_path.is_file():
                output_path = input_path.with_stem(f"{input_path.stem}_packed")
            else:
                output_path = Path(f"{input_path.name}_packed.py")

        # Generate the script
        script = generate_script(
            input_path,
            output_path=output_path,
            group_imports=group_imports,
            preserve_comments=preserve_comments,
        )

        # Show success message
        console.print(
            Panel.fit(
                f"✨ Successfully packaged script to [bold green]{output_path}[/]",
                title="Success",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}", style="bold red")
        raise typer.Exit(1)


@app.command()
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
    """Entry point for the CLI."""
    try:
        app()
    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    run()
