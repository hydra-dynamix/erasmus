"""CLI interface for Erasmus.

This module provides the command-line interface for interacting with Erasmus.
It uses Click for command parsing and handling.
"""

import time
from functools import wraps
from pathlib import Path
import signal
import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from erasmus.core.task import TaskManager, TaskStatus
from erasmus.core.watcher import WatcherFactory
from erasmus.git.manager import GitManager
from erasmus.utils.context import (
    cleanup_project,
    store_context,
    restore_context,
    list_context_dirs,
    print_context_dirs,
    select_context_dir,
    update_context,
    update_specific_file,
    handle_protocol_context,
)
from erasmus.utils.logging import LogContext, get_logger
from erasmus.utils.paths import SetupPaths

from .setup import setup as setup_env
from .protocol import protocol

load_dotenv()

# Configure logging
logger = get_logger(__name__)
console = Console()
task_manager = TaskManager()


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
@log_command
def task():
    """Task management commands."""


@task.command()
@click.argument("description")
@log_command
def add(description: str):
    """Add a new task with the given description."""
    with LogContext(logger, "add_task"):
        logger.debug(f"Adding task with description: {description}")
        new_task = task_manager.add_task(description)
        logger.info(f"Created task {new_task.id}: {description}")
        console.print(f"✨ Created task [bold green]{new_task.id}[/]")
        console.print(f"Description: {new_task.description}")


@task.command()
@click.argument("task_id")
@click.argument("status", type=click.Choice(["pending", "in_progress", "completed", "blocked"]))
@log_command
def status(task_id: str, status: str):
    """Update the status of a task."""
    with LogContext(logger, "update_task_status"):
        logger.debug(f"Updating task {task_id} status to {status}")
        task_status = TaskStatus[status.lower()]
        task_manager.update_task_status(task_id, task_status)
        logger.info(f"Updated task {task_id} status to {status}")
        console.print(f"📝 Updated task [bold]{task_id}[/] status to [bold green]{status}[/]")


@task.command()
@click.option(
    "--status",
    type=click.Choice(["pending", "in_progress", "completed", "blocked"]),
    help="Filter tasks by status",
)
@log_command
def list(status: str | None = None):
    """List all tasks, optionally filtered by status."""
    with LogContext(logger, "list_tasks"):
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


@task.command()
@click.argument("task_id")
@click.argument("note")
@log_command
def note(task_id: str, note: str):
    """Add a note to a task."""
    with LogContext(logger, "add_task_note"):
        logger.debug(f"Adding note to task {task_id}: {note}")
        task_manager.add_note_to_task(task_id, note)
        logger.info(f"Added note to task {task_id}")
        console.print(f"📝 Added note to task [bold]{task_id}[/]")


# === Git Commands ===
@cli.group()
@log_command
def git():
    """Git operations."""


@git.command()
@log_command
def status():
    """Show git repository status."""
    with LogContext(logger, "git_status"):
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


@git.command()
@click.argument("message")
@log_command
def commit(message: str):
    """Create a git commit with the given message."""
    with LogContext(logger, "git_commit"):
        logger.debug(f"Attempting to commit with message: {message}")
        git_manager = GitManager(Path.cwd())
        if git_manager.commit_changes(message):
            logger.info("Successfully committed changes")
            console.print("✨ Changes committed successfully")
        else:
            logger.error("Failed to commit changes")
            console.print("❌ Failed to commit changes", style="red")


@git.command()
@click.argument("name")
@log_command
def branch(name: str):
    """Create and switch to a new git branch."""
    with LogContext(logger, "git_branch"):
        logger.debug(f"Creating and switching to branch: {name}")
        git_manager = GitManager(Path.cwd())
        try:
            git_manager._run_git_command(["checkout", "-b", name])
            logger.info(f"Created and switched to branch: {name}")
            console.print(f"✨ Created and switched to branch: [bold]{name}[/]")
        except Exception:
            logger.error("Failed to create/switch branch", exc_info=True)
            console.print(f"❌ Failed to create branch: {name}", style="red")


# === Project Commands ===
@cli.command()
@log_command
def setup():
    """Set up a new project with necessary files and configuration."""
    with LogContext(logger, "project_setup"):
        logger.info("Starting project setup")
        setup_env()
        logger.info("Project setup completed successfully")
        console.print("✨ Project setup complete")


@cli.command()
@click.option(
    "--type",
    type=click.Choice(["architecture", "progress", "tasks", "context"]),
    help="Type of file to update",
)
@click.option("--content", help="New content for the file")
@log_command
def update(type: str, content: str):
    """Update project files."""
    with LogContext(logger, "update_file"):
        logger.debug(f"Updating {type} file")
        try:
            update_specific_file(type, content)
            logger.info(f"Successfully updated {type} file")
            console.print(f"✨ Updated {type} file")
        except Exception as e:
            logger.error(f"Failed to update {type} file", exc_info=True)
            console.print(f"❌ Failed to update {type} file: {e!s}", style="red")


@cli.command()
@click.option("--force", is_flag=True, help="Force cleanup without confirmation")
@log_command
def cleanup(force: bool):
    """Remove all generated files and restore backups if available."""
    with LogContext(logger, "cleanup"):
        logger.debug(f"Starting cleanup with force={force}")
        if not force:
            if not click.confirm("This will remove all generated files. Are you sure?"):
                logger.info("Cleanup cancelled by user")
                console.print("Cleanup cancelled.")
                return
        try:
            cleanup_project()
            logger.info("Successfully cleaned up project files")
            console.print("🧹 Cleanup complete")
        except Exception as e:
            logger.error("Failed to clean up project", exc_info=True)
            console.print(f"❌ Cleanup failed: {e!s}", style="red")


@cli.command()
def watch():
    """Watch for changes in project files and update context automatically."""
    with LogContext(logger, "watch"):
        try:
            # Initialize file watchers
            setup_paths = SetupPaths.with_project_root(Path.cwd())
            factory = WatcherFactory()

            # Create watchers for markdown files
            markdown_watcher = factory.create_markdown_watcher(
                setup_paths.markdown_files, update_specific_file
            )

            # Create watchers for protocol files
            protocol_files = {
                "agent_registry": setup_paths.protocols_dir / "agent_registry.json",
                "protocols": setup_paths.protocols_dir / "stored",
            }
            protocol_watcher = factory.create_markdown_watcher(
                protocol_files,
                lambda file_type, content: handle_protocol_context(setup_paths, file_type),
            )

            # Create observers for each watcher
            markdown_observer = factory.create_observer(
                markdown_watcher, str(setup_paths.project_root)
            )
            protocol_observer = factory.create_observer(
                protocol_watcher, str(setup_paths.protocols_dir)
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
@log_command
def context():
    """Context management commands."""
    return


@context.command()
@log_command
def store():
    """Store the current context in the context directory."""
    setup_paths = SetupPaths.with_project_root(Path.cwd())
    success = store_context(setup_paths)
    if success:
        console.print("✨ Context stored successfully")
    else:
        console.print("❌ Failed to store context. Check logs for details.", style="red")


@context.command()
@log_command
@click.argument("context_dir", required=False)
@click.option(
    "--architecture_context_dir",
    type=str,
    help="Context directory to restore (deprecated, use positional argument instead)",
)
def restore(context_dir: str = None, architecture_context_dir: str = None):
    """Restore the context from the specified context directory."""
    # Use context_dir if provided, otherwise fall back to architecture_context_dir
    directory_path = context_dir or architecture_context_dir

    if not directory_path:
        console.print(
            "❌ No context directory specified. Please provide a context directory path.",
            style="red",
        )
        return

    setup_paths = SetupPaths.with_project_root(Path.cwd())
    context_path = Path(directory_path)

    if not context_path.exists():
        console.print(f"❌ Context directory not found: {directory_path}", style="red")
        return

    success = restore_context(setup_paths, context_path)
    if success:
        console.print("✨ Context restored successfully")
    else:
        console.print("❌ Failed to restore context. Check logs for details.", style="red")


@context.command()
@log_command
def list_context():
    """List all context directories."""
    setup_paths = SetupPaths.with_project_root(Path.cwd())
    dirs = list_context_dirs(setup_paths)

    if dirs:
        console.print("Available context directories:")
        for i, dir_path in enumerate(dirs, 1):
            # Try to get a readable name from the directory
            dir_name = Path(dir_path).name
            console.print(f"{i}. {dir_name}")
    else:
        console.print("No context directories found")

    console.print("✨ Context directories listed successfully")


@context.command()
@log_command
def select():
    """Select a context directory to restore."""
    setup_paths = SetupPaths.with_project_root(Path.cwd())
    architecture_context_dir = select_context_dir(setup_paths)

    if not architecture_context_dir:
        console.print("No context directory selected", style="yellow")
        return

    console.print(f"Selected context directory: {architecture_context_dir}")

    # Confirm before restoring
    prompt = "Do you want to restore this context? This will overwrite current files."
    if click.confirm(prompt):
        success = restore_context(setup_paths, architecture_context_dir)
        if success:
            console.print("✨ Context restored successfully")
        else:
            console.print("❌ Failed to restore context. Check logs for details.", style="red")
    else:
        console.print("Context restoration cancelled")


if __name__ == "__main__":
    cli()
