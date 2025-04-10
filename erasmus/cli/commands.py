"""CLI interface for Erasmus.

This module provides the command-line interface for interacting with Erasmus.
It uses Click for command parsing and handling.
"""
from typing import Optional
import os
import time
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table


from ..core.task import TaskManager, TaskStatus    
from ..core.watcher import WatcherFactory
from ..utils.context import update_context, update_specific_file, cleanup_project, setup_project
from ..git.manager import GitManager
from ..utils.paths import SetupPaths
from .setup import setup as setup_env

from dotenv import load_dotenv

load_dotenv()

console = Console()
task_manager = TaskManager()

@click.group()
def cli():
    """Erasmus: AI Context Watcher for Development."""
    return

# === Task Management Commands ===
@cli.group()
def task():
    """Task management commands."""
    pass

@task.command()
@click.argument('description')
def add(description: str):
    """Add a new task with the given description."""
    new_task = task_manager.add_task(description)
    console.print(f"✨ Created task [bold green]{new_task.id}[/]")
    console.print(f"Description: {new_task.description}")

@task.command()
@click.argument('task_id')
@click.argument('status', type=click.Choice(['pending', 'in_progress', 'completed', 'blocked']))
def status(task_id: str, status: str):
    """Update the status of a task."""
    task_status = TaskStatus[status.lower()]
    task_manager.update_task_status(task_id, task_status)
    console.print(f"📝 Updated task [bold]{task_id}[/] status to [bold green]{status}[/]")

@task.command()
@click.option('--status', type=click.Choice(['pending', 'in_progress', 'completed', 'blocked']), help='Filter tasks by status')
def list(status: Optional[str] = None):
    """List all tasks, optionally filtered by status."""
    task_status = TaskStatus[status.lower()] if status else None
    tasks = task_manager.list_tasks(task_status)
    
    if not tasks:
        console.print("No tasks found.")
        return

    table = Table(show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Description")
    table.add_column("Status", style="green")
    
    for task in tasks:
        table.add_row(
            task.id,
            task.description,
            task.status.value.lower().replace('_', ' ')
        )
    
    console.print(table)

@task.command()
@click.argument('task_id')
@click.argument('note')
def note(task_id: str, note: str):
    """Add a note to a task."""
    task_manager.add_note_to_task(task_id, note)
    console.print(f"📝 Added note to task [bold]{task_id}[/]")

# === Git Commands ===
@cli.group()
def git():
    """Git operations."""
    pass

@git.command()
def status():
    """Show git repository status."""
    git_manager = GitManager(Path.cwd())
    state = git_manager.get_repository_state()
    console.print(state)

@git.command()
@click.argument('message')
def commit(message: str):
    """Create a git commit with the given message."""
    git_manager = GitManager(Path.cwd())
    if git_manager.commit_changes(message):
        console.print("✨ Changes committed successfully")
    else:
        console.print("❌ Failed to commit changes", style="red")

@git.command()
@click.argument('name')
def branch(name: str):
    """Create and switch to a new git branch."""
    git_manager = GitManager(Path.cwd())
    git_manager._run_git_command(["checkout", "-b", name])
    console.print(f"✨ Created and switched to branch: [bold]{name}[/]")

# === Project Commands ===
@cli.command()
def setup():
    """Set up a new project with necessary files and configuration."""
    setup_env()
    console.print("✨ Project setup complete")

@cli.command()
@click.option('--type', type=click.Choice(['architecture', 'progress', 'tasks', 'context']), help='Type of file to update')
@click.option('--content', help='New content for the file')
def update(type: str, content: str):
    """Update project files."""
    update_specific_file(type, content)
    console.print(f"✨ Updated {type} file")

@cli.command()
@click.option('--force', is_flag=True, help='Force cleanup without confirmation')
def cleanup(force: bool):
    """Remove all generated files and restore backups if available."""
    if not force:
        if not click.confirm('This will remove all generated files. Are you sure?'):
            console.print("Cleanup cancelled.")
            return
    cleanup_project()
    console.print("🧹 Cleanup complete")

@cli.command()
def watch():
    """Watch project files for changes."""
    pwd = Path.cwd()
    factory = WatcherFactory()
    setup_paths = SetupPaths(pwd)
    
    # Update initial context without backup
    update_context({}, backup=False)

    # Setup markdown watcher
    markdown_watcher = factory.create_markdown_watcher(
        setup_paths.markdown_files,
        lambda key, content: update_specific_file(key, content)
    )
    factory.create_observer(markdown_watcher, str(pwd))

    # Setup script watcher
    script_watcher = factory.create_script_watcher(
        setup_paths.script_files,
        lambda _: console.print("Script updated")
    )
    factory.create_observer(script_watcher, str(pwd))

    # Start all watchers
    factory.start_all()

    console.print("👀 Watching project files for changes. Press Ctrl+C to stop...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("Shutting down...")
        factory.stop_all()
    
if __name__ == '__main__':
    cli()