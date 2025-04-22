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
import subprocess

import typer
from rich.console import Console
from rich.logging import RichHandler
from click import Context, UsageError
from typer.core import TyperGroup
from packager.paths import get_packager_path_manager

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

custom_help_shown = False


# Add version-control subcommand group
class HelpOnErrorGroup(TyperGroup):
    def main(self, *args, **kwargs):
        try:
            return super().main(*args, **kwargs)
        except UsageError as e:
            print_version_control_help_and_exit()
        except Exception:
            print_version_control_help_and_exit()


version_app = typer.Typer(
    help="Version control operations using version.json", cls=HelpOnErrorGroup
)


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


def print_packager_help_and_exit():
    """Show packager help menu and exit with error code."""
    console.print("\n[bold]Packager Help Menu[/]")
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
    global custom_help_shown
    if custom_help_shown:
        sys.exit(1)
    console.print(f"\n[red]Error: {msg}[/]")
    print_packager_help_and_exit()


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
        print_packager_help_and_exit()


@app.command()
def package(
    input_path: str | None = typer.Argument(
        None, help="Path to Python file or directory to package (defaults to 'erasmus')"
    ),
    output_file: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    preserve_comments: bool = typer.Option(
        True, "--preserve-comments/--no-comments", help="Preserve comments in output"
    ),
    internal_use_version: str | None = None,
):
    """Package a Python file or directory into a single executable script."""
    try:
        path_manager = get_packager_path_manager()
        if input_path is None:
            input_path = str(path_manager.get_src_dir())
        else:
            input_path = str(input_path)
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

        # Convert py_files to a list of strings
        py_files_str = [str(file) for file in py_files]

        # Determine library name from input_path
        if input_path.is_file():
            library_name = input_path.stem
        else:
            library_name = input_path.name

        # Determine version
        version = internal_use_version if internal_use_version is not None else "0.0.0"

        # Use path manager to get output path
        if version == "0.0.0":
            # Clean up previous dry run scripts
            dry_run_dir = path_manager.get_dry_run_path(library_name)
            for f in dry_run_dir.glob(f"{library_name}_v0.0.0*.py"):
                f.unlink()
            output_path = path_manager.get_unique_output_path(library_name, "0.0.0")
        else:
            output_path = path_manager.get_unique_output_path(library_name, version)

        output_path = generate_script(py_files_str, output_path, preserve_comments)
        logger.debug("Generated script at: %s", output_path)
        typer.echo(f"Successfully packaged to '{output_path}'.")

        # Run the installer build script after packaging, passing the current bundle path
        try:
            subprocess.run(["bash", "scripts/build_installer.sh", str(output_path)], check=True)
            typer.echo("Installer build script completed.")
        except Exception as e:
            typer.echo(f"Installer build script failed: {e}")

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
            print_packager_help_and_exit()

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


@version_app.callback()
def version_main(ctx: typer.Context):
    """Version control submenu."""
    if ctx.invoked_subcommand is None:
        print_version_control_help_and_exit()


def print_version_control_help_and_exit():
    global custom_help_shown
    custom_help_shown = True
    console.print("\n[bold]DEBUG: This is the real help menu[/]")
    console.print("\n[bold]Version Control Help Menu[/]")
    command_rows = [
        ["version-control show", "Show the current version and last updated timestamp"],
        [
            "version-control bump",
            "Bump the version: specify which part to increment (e.g., 'major', 'minor', or 'patch'). Optionally add --description for a change log.",
        ],
        ["version-control log", "Show the version change log"],
    ]
    console.print("\n[bold]Available Version Control Commands:[/]")
    for cmd, desc in command_rows:
        console.print(f"  {cmd:<35} {desc}")
    console.print("\nFor more information about a command, run:")
    console.print("  erasmus-packager version-control <command> --help")
    raise typer.Exit(1)


@version_app.command("show")
def show_version():
    """Show the current version and last updated timestamp."""
    version_file = Path("version.json")
    if not version_file.exists():
        typer.echo("version.json not found.")
        raise typer.Exit(1)
    with open(version_file) as f:
        data = json.load(f)
    typer.echo(f"Version: {data.get('version')}")
    typer.echo(f"Last updated: {data.get('last_updated')}")


@version_app.command("bump")
def bump_version(
    part: str = typer.Argument(
        ...,
        help="Which part to bump: 'major' (1.2.3→2.0.0, breaking changes), 'minor' (1.2.3→1.3.0, new features), or 'patch' (1.2.3→1.2.4, bug fixes). Example: 'packager version-control bump minor --description \"Add feature\"'",
    ),
    description: str = typer.Option("", help="Description of the change"),
    input_path: str | None = typer.Option(
        None, "--input", help="Path to Python file or directory to package (defaults to 'erasmus')"
    ),
):
    """Bump the version (major, minor, or patch) and log the change, then package the project."""
    try:
        if not description:
            description = typer.prompt("Enter a description for this version change")
        version_file = Path("version.json")
        if not version_file.exists():
            typer.echo("version.json not found.")
            raise typer.Exit(1)
        with open(version_file) as f:
            data = json.load(f)
        version = data.get("version", "0.0.0").split(".")
        if len(version) != 3:
            typer.echo("Invalid version format in version.json.")
            raise typer.Exit(1)
        major, minor, patch = map(int, version)
        if part == "major":
            major += 1
            minor = 0
            patch = 0
        elif part == "minor":
            minor += 1
            patch = 0
        elif part == "patch":
            patch += 1
        else:
            typer.echo("Invalid part. Use 'major', 'minor', or 'patch'.")
            print_version_control_help_and_exit()
            return
        import datetime

        now = datetime.datetime.now().isoformat()
        new_version = f"{major}.{minor}.{patch}"
        data["version"] = new_version
        data["last_updated"] = now
        if "changes" not in data:
            data["changes"] = []
        data["changes"].append(
            {"description": description or f"Bump {part}", "type": part, "timestamp": now}
        )
        with open(version_file, "w") as f:
            json.dump(data, f, indent=2)
        typer.echo(f"Version bumped to {new_version}")
        # Run the packager after bumping the version
        from packager.__main__ import package

        # Always pass a string or None for input_path
        if input_path is not None:
            input_path_arg = str(input_path)
        else:
            input_path_arg = None
        package(input_path=input_path_arg, internal_use_version=new_version)
    except Exception:
        print_version_control_help_and_exit()
        return


@version_app.command("log")
def version_log():
    """Show the version change log."""
    version_file = Path("version.json")
    if not version_file.exists():
        typer.echo("version.json not found.")
        raise typer.Exit(1)
    with open(version_file) as f:
        data = json.load(f)
    changes = data.get("changes", [])
    if not changes:
        typer.echo("No version changes logged.")
        return
    for change in changes:
        typer.echo(f"[{change['timestamp']}] {change['type']}: {change['description']}")


app.add_typer(version_app, name="version-control", help="Version control operations")


def run():
    """Entry point for the packager CLI."""
    try:
        # If the user ran just 'packager version-control', show custom help
        if (
            len(sys.argv) >= 2
            and sys.argv[1] == "version-control"
            and (len(sys.argv) == 2 or sys.argv[2].startswith("-"))
        ):
            print_version_control_help_and_exit()
        # If the user ran 'packager version-control bump' with no PART argument, show custom help
        if (
            len(sys.argv) >= 3
            and sys.argv[1] == "version-control"
            and sys.argv[2] == "bump"
            and (len(sys.argv) == 3 or sys.argv[3].startswith("-"))
            and not ("--help" in sys.argv or "-h" in sys.argv)
        ):
            print_version_control_help_and_exit()
        app()
    except UsageError as e:
        handle_error(str(e))
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as error:
        handle_error(str(error))
    return 0


if __name__ == "__main__":
    sys.exit(run())
