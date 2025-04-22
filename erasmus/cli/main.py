"""
Main CLI entry point for Erasmus.
"""

import typer
from erasmus.cli.context_commands import context_app
from erasmus.cli.protocol_commands import protocol_app
from erasmus.cli.setup_commands import setup_app
from erasmus.utils.rich_console import print_table

app = typer.Typer(
    help="Erasmus - Development Context Management System\n\nA tool for managing development contexts, protocols, and Model Context Protocol (MCP) interactions.\n\nFor more information, visit: https://github.com/hydra-dynamics/erasmus"
)

# Add sub-commands
app.add_typer(context_app, name="context", help="Manage development contexts")
app.add_typer(protocol_app, name="protocol", help="Manage protocols")
app.add_typer(setup_app, name="setup", help="Setup Erasmus")


# Custom error handler for unknown commands and argument errors
def print_main_help_and_exit():
    try:
        from rich.console import Console

        console = Console()
        banner = [
            ("green", " _____                                  "),
            ("green", "|  ___|                                 "),
            ("cyan", "| |__ _ __ __ _ ___ _ __ ___  _   _ ___ "),
            ("green", "|  __| '__/ _` / __| '_ ` _ \\| | | / __|"),
            ("cyan", "| |__| | | (_| \\__ \\ | | | | | |_| \\__ \\"),
            ("green", "\\____/_|  \\__,_|___/_| |_| |_|\\__,_|___/"),
        ]
        for color, line in banner:
            console.print(line, style=color)
    except ImportError:
        # Fallback to plain text if rich is not available
        typer.echo(r"""
 _____                                  
|  ___|                                 
| |__ _ __ __ _ ___ _ __ ___  _   _ ___ 
|  __| '__/ _` / __| '_ ` _ \| | | / __|
| |__| | | (_| \__ \ | | | | | |_| \__ \
\____/_|  \__,_|___/_| |_| |_|\__,_|___/
""")
    typer.echo("\n Development Context Management System\n")
    command_rows = [
        ["erasmus context", "Manage development contexts"],
        ["erasmus protocol", "Manage protocols"],
        ["erasmus setup", "Setup Erasmus"],
        ["erasmus watch", "Watch for .ctx file changes"],
        ["erasmus status", "Show current status"],
        ["erasmus version", "Show Erasmus version"],
    ]
    print_table(["Command", "Description"], command_rows, title="Available Erasmus Commands")
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


@app.command()
def status():
    """Show the current Erasmus context and protocol status."""
    from erasmus.context import ContextManager
    from erasmus.protocol import ProtocolManager
    from erasmus.utils.rich_console import print_table
    import os

    context_manager = ContextManager()
    protocol_manager = ProtocolManager()

    # Current context (from .erasmus/current_context.txt if exists)
    current_context = None
    current_context_path = os.path.join(context_manager.base_dir.parent, "current_context.txt")
    if os.path.exists(current_context_path):
        with open(current_context_path) as f:
            current_context = f.read().strip()

    # List all contexts
    try:
        contexts = context_manager.list_contexts()
    except Exception as e:
        contexts = []

    # List all protocols
    try:
        protocols = protocol_manager.list_protocols()
    except Exception as e:
        protocols = []

    print_table(
        ["Status", "Value"],
        [
            ["Current Context", current_context or "(none set)"],
            ["Available Contexts", ", ".join(contexts) if contexts else "(none)"],
            ["Available Protocols", ", ".join(protocols) if protocols else "(none)"],
        ],
        title="Erasmus Status",
    )


@app.command()
def version():
    """Show the Erasmus version."""
    import erasmus

    typer.echo(f"Erasmus version: {erasmus.__version__}")


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
