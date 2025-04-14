"""CLI interface for Erasmus.

This module provides the command-line interface for interacting with Erasmus.
It uses Click for command parsing and handling.
"""

import signal
import subprocess
import time
from subprocess import PIPE
from functools import wraps
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from erasmus.core.task import TaskManager, TaskStatus
from erasmus.core.watcher import WatcherFactory
from erasmus.git.manager import GitManager
from erasmus.utils.context import (
    handle_protocol_context,
    restore_context,
    select_context_dir,
    store_context,
    update_specific_file,
)
from erasmus.utils.logging import LogContext, get_logger
from erasmus.utils.paths import SetupPaths

from erasmus.cli.protocol import protocol


load_dotenv()

# Configure logging
logger = get_logger(__name__)
console = Console()
task_manager = TaskManager()

SETUP_PATHS = SetupPaths.with_project_root(Path.cwd())


def log_command(f):
    """Decorator to log CLI command execution."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        cmd_name = f.__name__
        with LogContext(logger, f"command_{cmd_name}"):
            try:
                logger.info(f"Executing command: {cmd_name}")
                if kwargs:
                    logger.debug(f"Command arguments: {kwargs}")
                result = f(*args, **kwargs)
                logger.info(f"Command {cmd_name} completed successfully")
                return result
            except Exception:
                logger.error(f"Command {cmd_name} failed", exc_info=True)
                raise

    return wrapper


@click.group()
@log_command
def cli():
    """Erasmus: AI Context Watcher for Development."""
    return


# Add protocol commands
cli.add_command(protocol)


# === Task Management Commands ===
@cli.group()
@click.pass_context
def task(ctx):
    """Task management commands."""
    return


@task.command()
@click.argument("description")
@click.pass_context
def add(ctx, description: str):
    """Add a new task with the given description."""
    with LogContext(logger, "add_task"):
        try:
            logger.debug(f"Adding task with description: {description}")
            new_task = task_manager.add_task(description)
            logger.info(f"Created task {new_task.id}: {description}")
            console.print(f"✨ Created task [bold green]{new_task.id}[/]")
            console.print(f"Description: {new_task.description}")
        except Exception as e:
            logger.error(f"Failed to add task: {e}", exc_info=True)
            console.print(f"❌ Failed to add task: {e}", style="red")
            ctx.exit(1)


@task.command()
@click.argument("task_id")
@click.argument("status", type=click.Choice(["pending", "in_progress", "completed", "blocked"]))
@click.pass_context
def status(ctx, task_id: str, status: str):
    """Update the status of a task."""
    with LogContext(logger, "update_task_status"):
        try:
            logger.debug(f"Updating task {task_id} status to {status}")
            task_status = TaskStatus[status.lower()]
            task_manager.update_task_status(task_id, task_status)
            logger.info(f"Updated task {task_id} status to {status}")
            console.print(f"📝 Updated task [bold]{task_id}[/] status to [bold green]{status}[/]")
        except Exception as e:
            logger.error(f"Failed to update task status: {e}", exc_info=True)
            console.print(f"❌ Failed to update task status: {e}", style="red")
            ctx.exit(1)


@task.command()
@click.option(
    "--status",
    type=click.Choice(["pending", "in_progress", "completed", "blocked"]),
    help="Filter tasks by status",
)
@click.pass_context
def list(ctx, status: str | None = None):
    """List all tasks, optionally filtered by status."""
    with LogContext(logger, "list_tasks"):
        try:
            logger.debug(f"Listing tasks with status filter: {status}")
            task_status = TaskStatus[status.lower()] if status else None
            tasks = task_manager.list_tasks(task_status)

            if not tasks:
                logger.info("No tasks found")
                console.print("No tasks found.")
                return

            logger.info(f"Found {len(tasks)} tasks")
            table = Table(show_header=True)
            table.add_column("ID", style="cyan")
            table.add_column("Description")
            table.add_column("Status", style="green")

            for task in tasks:
                logger.debug(f"Adding task to table: {task.id} - {task.status}")
                table.add_row(
                    task.id,
                    task.description,
                    task.status.value.lower().replace("_", " "),
                )

            console.print(table)
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}", exc_info=True)
            console.print(f"❌ Failed to list tasks: {e}", style="red")
            ctx.exit(1)


@task.command()
@click.argument("task_id")
@click.argument("note")
@click.pass_context
def note(ctx, task_id: str, note: str):
    """Add a note to a task."""
    with LogContext(logger, "add_task_note"):
        try:
            logger.debug(f"Adding note to task {task_id}: {note}")
            task_manager.add_note_to_task(task_id, note)
            logger.info(f"Added note to task {task_id}")
            console.print(f"📝 Added note to task [bold]{task_id}[/]")
        except Exception as e:
            logger.error(f"Failed to add note: {e}", exc_info=True)
            console.print(f"❌ Failed to add note: {e}", style="red")
            ctx.exit(1)


# === Git Commands ===
@cli.group()
@click.pass_context
def git(ctx):
    """Git operations."""
    return


@git.command()
@click.pass_context
def status(ctx):
    """Show git repository status."""
    with LogContext(logger, "git_status"):
        try:
            logger.debug("Getting repository status")
            git_manager = GitManager(Path.cwd())
            state = git_manager.get_repository_state()
            logger.info(
                f"Repository status - Branch: {state['branch']}, "
                + f"Staged: {len(state['staged'])}, "
                + f"Unstaged: {len(state['unstaged'])}, "
                + f"Untracked: {len(state['untracked'])}",
            )
            console.print(state)
        except Exception as e:
            logger.error(f"Failed to get git status: {e}", exc_info=True)
            console.print(f"❌ Failed to get git status: {e}", style="red")
            ctx.exit(1)


@git.command()
@click.argument("message")
@click.pass_context
def commit(ctx, message: str):
    """Create a git commit with the given message."""
    with LogContext(logger, "git_commit"):
        try:
            logger.debug(f"Attempting to commit with message: {message}")
            git_manager = GitManager(Path.cwd())
            if git_manager.commit_changes(message):
                logger.info("Successfully committed changes")
                console.print("✨ Changes committed successfully")
            else:
                logger.error("Failed to commit changes")
                console.print("❌ Failed to commit changes", style="red")
                ctx.exit(1)
        except Exception as e:
            logger.error(f"Failed to commit changes: {e}", exc_info=True)
            console.print(f"❌ Failed to commit changes: {e}", style="red")
            ctx.exit(1)


@git.command()
@click.argument("name")
@click.pass_context
def branch(ctx, name: str):
    """Create and switch to a new git branch."""
    with LogContext(logger, "git_branch"):
        try:
            logger.debug(f"Creating and switching to branch: {name}")
            git_manager = GitManager(Path.cwd())
            git_manager._run_git_command(["checkout", "-b", name])
            logger.info(f"Created and switched to branch: {name}")
            console.print(f"✨ Created and switched to branch: [bold]{name}[/]")
        except Exception as e:
            logger.error(f"Failed to create/switch branch: {e}", exc_info=True)
            console.print(f"❌ Failed to create branch: {name}", style="red")
            ctx.exit(1)


# === Project Commands ===
@cli.command()
@click.pass_context
def setup(ctx):
    """Set up a new project with necessary files and configuration."""
    with LogContext(logger, "project_setup"):
        try:
            logger.info("Starting project setup")
            from erasmus.cli.setup import setup_env

            setup_env()
            logger.info("Project setup completed successfully")
            console.print("✨ Project setup complete")
        except Exception as e:
            logger.error(f"Project setup failed: {e}", exc_info=True)
            console.print(f"❌ Project setup failed: {e}", style="red")
            ctx.exit(1)


@cli.command()
@click.option(
    "--type",
    type=click.Choice(["architecture", "progress", "tasks", "context"]),
    help="Type of file to update",
)
@click.option("--content", help="New content for the file")
@click.pass_context
def update(ctx, type: str, content: str):
    """Update project files."""
    with LogContext(logger, "update_file"):
        try:
            logger.debug(f"Updating {type} file")
            update_specific_file(type, content)
            logger.info(f"Successfully updated {type} file")
            console.print(f"✨ Updated {type} file")
        except Exception as e:
            logger.error(f"Failed to update {type} file: {e}", exc_info=True)
            console.print(f"❌ Failed to update {type} file: {e}", style="red")
            ctx.exit(1)


@cli.command()
@click.option("--force", is_flag=True, help="Force cleanup without confirmation")
@click.pass_context
def cleanup(ctx, force: bool):
    """Remove all generated files."""
    with LogContext(logger, "cleanup"):
        try:
            result = subprocess.run(
                ["bash", "scripts/cleanup.sh"], check=True, stdout=PIPE, stdin=PIPE
            )
            console.print(result.stdout)
            logger.info("Successfully cleaned up project files")
            console.print("🧹 Cleanup complete")
        except Exception as e:
            logger.error(f"Failed to clean up project: {e}", exc_info=True)
            console.print(f"❌ Cleanup failed: {e}", style="red")
            ctx.exit(1)


@cli.command()
def watch():
    """Watch for changes in project files and update context automatically."""
    with LogContext(logger, "watch"):
        try:
            # Initialize file watchers

            factory = WatcherFactory()

            # Create watchers for markdown files
            markdown_watcher = factory.create_markdown_watcher(
                SETUP_PATHS.markdown_files, update_specific_file
            )

            # Create watchers for protocol files
            protocol_files = {
                "agent_registry": SETUP_PATHS.protocols_dir / "agent_registry.json",
                "protocols": SETUP_PATHS.protocols_dir / "stored",
            }
            protocol_watcher = factory.create_markdown_watcher(
                protocol_files,
                lambda file_type, content: handle_protocol_context(SETUP_PATHS, file_type),
            )

            # Create observers for each watcher
            markdown_observer = factory.create_observer(
                markdown_watcher, str(SETUP_PATHS.project_root)
            )
            protocol_observer = factory.create_observer(
                protocol_watcher, str(SETUP_PATHS.protocols_dir)
            )

            # Start all watchers
            factory.start_all()
            logger.info("👀 Watching for file changes...")
            console.print("👀 Watching for file changes... Press Ctrl+C to stop")

            # Flag to control the main loop
            running = True

            # Handle shutdown gracefully
            def handle_shutdown(signum, frame):
                nonlocal running
                logger.info("Shutting down watchers...")
                console.print("\n🛑 Shutting down watchers...")
                factory.stop_all()
                logger.info("All watchers stopped")
                console.print("✨ All watchers stopped successfully")
                running = False

            # Register signal handlers
            signal.signal(signal.SIGINT, handle_shutdown)
            signal.signal(signal.SIGTERM, handle_shutdown)

            # Keep the main thread alive
            while running:
                time.sleep(1)

        except Exception as e:
            logger.error(f"Error in watch command: {e}", exc_info=True)
            console.print(f"❌ Error in watch command: {e}", style="red")
            raise


@cli.group()
@click.pass_context
def context(ctx):
    """Context management commands."""
    return


@context.command()
@click.pass_context
def store(ctx):
    """Store the current context in the context directory."""
    with LogContext(logger, "store_context"):
        try:
            success = store_context(SETUP_PATHS)
            if success:
                logger.info("Context stored successfully")
                console.print("✨ Context stored successfully")
            else:
                logger.error("Failed to store context")
                console.print("❌ Failed to store context. Check logs for details.", style="red")
                ctx.exit(1)
        except Exception as e:
            logger.error(f"Failed to store context: {e}", exc_info=True)
            console.print(f"❌ Failed to store context: {e}", style="red")
            ctx.exit(1)


@context.command()
@click.argument(
    "path", type=click.Path(exists=True, dir_okay=True, file_okay=False), required=False
)
@click.pass_context
def restore(ctx, path):
    """Restore the context from the context directory.

    If PATH is provided, restore from that specific directory.
    Otherwise, restore from the default project_context directory.
    """
    with LogContext(logger, "restore_context"):
        try:
            context_path = Path(path) if path else None
            success = restore_context(SETUP_PATHS, context_path)
            if success:
                logger.info("Context restored successfully")
                console.print("✨ Context restored successfully")
            else:
                logger.error("Failed to restore context")
                console.print("❌ Failed to restore context. Check logs for details.", style="red")
                ctx.exit(1)
        except Exception as e:
            logger.error(f"Failed to restore context: {e}", exc_info=True)
            console.print(f"❌ Failed to restore context: {e}", style="red")
            ctx.exit(1)


@context.command()
@click.pass_context
def list(ctx):
    """List all available context directories."""
    with LogContext(logger, "list_context_dirs"):
        try:
            context_dirs = SETUP_PATHS.context_dir.iterdir()
            context_dir_names = [dir_path.name for dir_path in context_dirs if dir_path.is_dir()]

            if context_dir_names:
                logger.info(f"Found {len(context_dir_names)} context directories")
                console.print("Available context directories:")
                for i, dir_name in enumerate(context_dir_names, 1):
                    # Try to get a readable name from the directory
                    console.print(f"{i}. {dir_name}")
            else:
                logger.info("No context directories found")
                console.print("No context directories found")

            console.print("✨ Context directories listed successfully")
        except Exception as e:
            logger.error(f"Failed to list context directories: {e}", exc_info=True)
            console.print(f"❌ Failed to list context directories: {e}", style="red")
            ctx.exit(1)


@context.command()
@click.pass_context
def select(ctx):
    """Select a context directory to restore."""
    with LogContext(logger, "select_context"):
        try:
            architecture_context_dir = select_context_dir(SETUP_PATHS)

            if not architecture_context_dir:
                logger.info("No context directory selected")
                console.print("No context directory selected", style="yellow")
                return

            logger.info(f"Selected context directory: {architecture_context_dir}")
            console.print(f"Selected context directory: {architecture_context_dir}")

            # Confirm before restoring
            prompt = "Do you want to restore this context? This will overwrite current files."
            if click.confirm(prompt):
                success = restore_context(SETUP_PATHS, architecture_context_dir)
                if success:
                    logger.info("Context restored successfully")
                    console.print("✨ Context restored successfully")
                else:
                    logger.error("Failed to restore context")
                    console.print(
                        "❌ Failed to restore context. Check logs for details.", style="red"
                    )
                    ctx.exit(1)
            else:
                logger.info("Context restoration cancelled")
                console.print("Context restoration cancelled")
        except Exception as e:
            logger.error(f"Failed to select context: {e}", exc_info=True)
            console.print(f"❌ Failed to select context: {e}", style="red")
            ctx.exit(1)


if __name__ == "__main__":
    cli()
