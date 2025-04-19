"""
Main CLI entry point for Erasmus.
"""

import typer
from erasmus.cli.context_commands import app as context_app
from erasmus.cli.protocol_commands import app as protocol_app
from erasmus.cli.setup_commands import app as setup_app
from erasmus.utils.rich_console import print_table

app = typer.Typer(
    help="""
    Erasmus - Development Context Management System
    
    A tool for managing development contexts, protocols, and Model Context Protocol (MCP) interactions.
    
    For more information, visit: https://github.com/hydra-dynamics/erasmus
    """
)

# Add sub-commands
app.add_typer(context_app, name="context", help="Manage development contexts")
app.add_typer(protocol_app, name="protocol", help="Manage protocols")
app.add_typer(setup_app, name="setup", help="Setup Erasmus")


# Custom error handler for unknown commands and argument errors
def print_main_help_and_exit():
    typer.echo("\nErasmus - Development Context Management System")
    command_rows = [
        ["erasmus context", "Manage development contexts"],
        ["erasmus protocol", "Manage protocols"],
        ["erasmus setup", "Setup Erasmus"],
    ]
    print_table(
        ["Command", "Description"], command_rows, title="Available Erasmus Commands"
    )
    typer.echo("\nFor more information about a command, run:")
    typer.echo("  erasmus <command> --help")
    raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Erasmus - Development Context Management System
    """
    if ctx.invoked_subcommand is None:
        print_main_help_and_exit()


# Patch Typer's error handling to show help on unknown command
import sys
from typer.main import get_command
from typer.core import TyperGroup
from click import UsageError

original_command = get_command(app)


class HelpOnErrorGroup(TyperGroup):
    def main(self, *args, **kwargs):
        try:
            return super().main(*args, **kwargs)
        except UsageError as e:
            typer.echo(str(e))
            print_main_help_and_exit()


app.command_class = HelpOnErrorGroup


@app.command()
def watch():  # pragma: no cover
    """Watch for changes to .ctx files and update the IDE rules file automatically.

    Press Ctrl+C to stop watching.
    """
    import time
    from erasmus.utils.paths import get_path_manager
    from erasmus.file_monitor import FileMonitor

    pm = get_path_manager()
    root = pm.get_root_dir()
    monitor = FileMonitor(str(root))
    monitor.start()
    typer.echo(f"Watching {root} for .ctx file changes (Ctrl+C to stop)...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
        typer.echo("Stopped watching.")


if __name__ == "__main__":
    from click import UsageError

    try:
        app(standalone_mode=False)
    except UsageError as e:
        typer.echo(str(e))
        print_main_help_and_exit()
    except Exception as error:
        print_table(["Error"], [[str(error)]], title="CLI Error")
        raise typer.Exit(1)
    except SystemExit as e:
        if e.code != 2:
            raise
