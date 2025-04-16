"""
Python Script Packager CLI

This module provides the command-line interface for the Python Script Packager.
It uses Typer to create a modern CLI that packages Python projects into standalone
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

from .builder import build_script
from .collector import collect_py_files
from .mapping import map_imports_to_packages
from .parser import extract_imports, strip_imports

# Create Typer app
app = typer.Typer(help="Python Script Packager CLI.")
console = Console()


def setup_logging(verbose: bool = False):
    """Set up logging configuration based on verbose flag."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
    return logging.getLogger("packager")


@app.command()
def package(
    input_path: str = typer.Argument(..., help="Path to Python file or directory to package"),
    output_path: Optional[str] = typer.Option(
        None, "--output-path", "-o", help="Path to output file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    Package a Python file or directory into a single executable script.
    """
    logger = setup_logging(verbose)

    input_path = Path(input_path)
    if not input_path.exists():
        logger.error(f"Input path does not exist: {input_path}")
        raise typer.Exit(1)

    # Collect Python files
    py_files = list(collect_py_files(input_path))
    if not py_files:
        logger.error(f"No Python files found in {input_path}")
        raise typer.Exit(1)

    logger.debug(f"Found {len(py_files)} Python files")

    # Determine output path
    if output_path:
        output_path = Path(output_path)
    else:
        if input_path.is_file():
            output_path = input_path.with_suffix(".packaged.py")
        else:
            output_path = input_path / f"{input_path.name}.packaged.py"

    # Generate script content
    logger.debug("Generating script content")
    try:
        script_content = build_script(py_files)
    except Exception as e:
        logger.error(f"Error generating script: {e}")
        raise typer.Exit(1)

    # Write output
    logger.debug(f"Writing script to {output_path}")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(script_content)
        logger.info(f"Successfully packaged to {output_path}")
    except Exception as e:
        logger.error(f"Error writing output file: {e}")
        raise typer.Exit(1)


@app.command()
def list_files(
    directory: Path = typer.Argument(
        ..., help="Directory to list Python files from", exists=True, file_okay=False, dir_okay=True
    ),
):
    """List all Python files that would be included in packaging."""
    try:
        if not directory.exists():
            console.print(f"[red]Error: Directory '{directory}' does not exist")
            raise typer.Exit(1)
        if not directory.is_dir():
            console.print(f"[red]Error: '{directory}' is not a directory")
            raise typer.Exit(1)

        files = collect_py_files(directory)
        if not files:
            console.print("[yellow]No Python files found in directory.[/]")
            return

        console.print("\n[bold]Python files found:[/]")
        for file in files:
            console.print(f"  • {file}")
        console.print(f"\nTotal: {len(files)} files")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}")
        raise typer.Exit(1)


@app.command()
def version():
    """Show the version of the packager."""
    console.print("Python Script Packager v0.1.0")
    return 0


def run():
    """Entry point for the packager CLI.

    This function is used by the entry point script to run the CLI.
    It simply calls the main() function which runs the Typer CLI.
    """
    return main()


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
