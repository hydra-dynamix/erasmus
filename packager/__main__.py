"""
Python Script Packager CLI

This module provides the command-line interface for the Python Script Packager.
It uses Typer to create a modern CLI that packages Python projects into standalone
scripts with automatic dependency management using uv.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.logging import RichHandler
from click import Context, UsageError

from packager.builder import generate_script, order_files
from packager.collector import collect_py_files
from packager.mapping import map_imports_to_packages, get_required_packages
from packager.parser import parse_imports, extract_code_body, ImportSet

# Set up logging
logger = logging.getLogger(__name__)

# Create Typer app
app = typer.Typer(
    help="Python Script Packager CLI.",
    no_args_is_help=True,
    add_completion=False,
)
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


def print_help_and_exit():
    """Show help menu and exit with error code."""
    console.print("\nPython Script Packager CLI")
    command_rows = [
        [
            "erasmus-packager package",
            "Package a Python file or directory into a single executable script",
        ],
        [
            "erasmus-packager list-files",
            "List all Python files that would be included in packaging",
        ],
        ["erasmus-packager version", "Show the version of the packager"],
    ]
    console.print("\n[bold]Available Commands:[/]")
    for cmd, desc in command_rows:
        console.print(f"  {cmd:<30} {desc}")

    console.print("\nFor more information about a command, run:")
    console.print("  erasmus-packager <command> --help")
    sys.exit(1)


def handle_error(msg: str):
    """Handle errors by showing the error message and help menu."""
    console.print(f"\n[red]Error: {msg}[/]")
    print_help_and_exit()


def get_version_info():
    """Get version information from version.json."""
    try:
        version_file = Path("version.json")
        if not version_file.exists():
            return "0.0.0"  # Default version if file doesn't exist

        with open(version_file, "r") as f:
            version_data = json.load(f)
            return version_data.get("version", "0.0.0")
    except Exception as e:
        logger.warning(f"Error reading version.json: {e}")
        return "0.0.0"


@app.callback()
def main(ctx: typer.Context):
    """Python Script Packager CLI."""
    if ctx.invoked_subcommand is None:
        print_help_and_exit()


@app.command()
def package(
    input_path: str = typer.Argument(..., help="Path to Python file or directory to package"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    preserve_comments: bool = typer.Option(
        True, "--preserve-comments/--no-comments", help="Preserve comments in output"
    ),
) -> None:
    """Package a Python file or directory into a single executable script."""
    try:
        input_path = Path(input_path)
        if not input_path.exists():
            typer.echo(f"Error: Input path '{input_path}' does not exist.")
            raise typer.Exit(1)

        # Collect Python files
        py_files = []
        if input_path.is_file() and input_path.suffix == ".py":
            py_files = [input_path]
        elif input_path.is_dir():
            py_files = list(input_path.glob("**/*.py"))
        else:
            typer.echo(f"Error: Input path '{input_path}' is not a Python file or directory.")
            raise typer.Exit(1)

        if not py_files:
            typer.echo(f"Error: No Python files found in '{input_path}'.")
            raise typer.Exit(1)

        typer.echo(f"Found {len(py_files)} Python files to package.")

        # Extract package name from input path
        package_name = input_path.name if input_path.is_dir() else input_path.stem
        logger.debug("Package name: %s", package_name)

        # Build set of local module names and ignore list
        local_modules = {Path(f).stem for f in py_files}
        ignore_modules = {Path(f).stem for f in py_files}
        ignore_modules.add("erasmus")
        ignore_modules.add(".")

        # Extract imports and code
        imports = ImportSet()
        code_body = []

        # Order files so dependencies are included first
        try:
            from packager.builder import analyze_dependencies

            dependencies = analyze_dependencies([Path(f) for f in py_files])
            ordered_files = order_files(dependencies, [Path(f) for f in py_files])
            py_files = ordered_files
        except Exception as e:
            logger.warning(f"Could not order files by dependencies: {e}")

        for file in py_files:
            logger.debug("Processing file: %s", file)
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract imports from the file
            file_imports, errors = parse_imports(content)
            if errors:
                for error in errors:
                    logger.warning("Error parsing imports in %s: %s", file, error)

            logger.debug(
                "File imports: stdlib=%s, third_party=%s, local=%s",
                file_imports.stdlib,
                file_imports.third_party,
                file_imports.local,
            )

            # Filter out imports that belong to the package being bundled
            filtered_imports = ImportSet()

            # Filter stdlib imports
            for imp in file_imports.stdlib:
                if not imp.startswith(package_name):
                    filtered_imports.stdlib.add(imp)

            # Filter third-party imports
            for imp in file_imports.third_party:
                if not imp.startswith(package_name):
                    filtered_imports.third_party.add(imp)

            # Filter local imports
            for imp in file_imports.local:
                if not imp.startswith(package_name):
                    filtered_imports.local.add(imp)

            logger.debug(
                "Filtered imports: stdlib=%s, third_party=%s, local=%s",
                filtered_imports.stdlib,
                filtered_imports.third_party,
                filtered_imports.local,
            )

            # Update the main imports set
            imports.update(filtered_imports)

            # Extract code body (excluding imports)
            file_code = extract_code_body(file, preserve_comments, ignore_modules=ignore_modules)
            code_body.append(f"# Code from {file.name}\n{file_code}")

        # Determine output file path
        if output_file:
            output_path = Path(output_file)
        else:
            # Read version from version.json
            version_file = Path("version.json")
            if version_file.exists():
                with open(version_file, "r") as vf:
                    version_data = json.load(vf)
                    version = version_data.get("version", "0.0.0")
            else:
                version = "0.0.0"

            # Determine folder name
            if input_path.is_file():
                folder_name = input_path.stem
            else:
                folder_name = input_path.name

            build_dir = Path("build") / version
            build_dir.mkdir(parents=True, exist_ok=True)
            output_path = build_dir / f"{folder_name}_v{version}.py"

        # Convert py_files to a list of strings
        py_files_str = [str(file) for file in py_files]

        # Generate the script
        output_path = generate_script(py_files_str, output_path, preserve_comments)
        logger.debug("Generated script at: %s", output_path)
        typer.echo(f"Successfully packaged to '{output_path}'.")

    except Exception as e:
        logger.exception("Error packaging files")
        typer.echo(f"Error: {str(e)}")
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
            handle_error(f"Directory '{directory}' does not exist")
        if not directory.is_dir():
            handle_error(f"'{directory}' is not a directory")

        files = collect_py_files(directory)
        if not files:
            console.print("[yellow]No Python files found in directory.[/]")
            print_help_and_exit()

        console.print("\n[bold]Python files found:[/]")
        for file in files:
            console.print(f"  • {file}")
        console.print(f"\nTotal: {len(files)} files")

    except Exception as e:
        handle_error(str(e))


@app.command()
def version():
    """Show the version of the packager."""
    console.print("Python Script Packager v0.1.0")
    return 0


def run():
    """Entry point for the packager CLI."""
    try:
        app()
    except UsageError as e:
        handle_error(str(e))
    except Exception as error:
        handle_error(str(error))
    except SystemExit as e:
        sys.exit(e.code)
    return 0


if __name__ == "__main__":
    sys.exit(run())
