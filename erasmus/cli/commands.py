"""CLI interface for Erasmus.

This module provides the command-line interface for interacting with Erasmus.
It uses Click for command parsing and handling.
"""
from typing import Optional
import os
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from watchdog.observers import Observer

from ..core.task import TaskManager, TaskStatus
from ..core.watcher import MarkdownWatcher, ScriptWatcher, run_observer
from ..utils.context import update_context, setup_project, update_specific_file, cleanup_project
from ..utils.git import GitManager

console = Console()
task_manager = TaskManager()

@click.group()
def cli():
    """Erasmus: AI Context Watcher for Development."""
    pass

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
    task_status = TaskStatus[status.upper()]
    task_manager.update_task_status(task_id, task_status)
    console.print(f"📝 Updated task [bold]{task_id}[/] status to [bold green]{status}[/]")

@task.command()
@click.option('--status', type=click.Choice(['pending', 'in_progress', 'completed', 'blocked']), help='Filter tasks by status')
def list(status: Optional[str] = None):
    """List all tasks, optionally filtered by status."""
    task_status = TaskStatus[status.upper()] if status else None
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
    setup_project()
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
    
    # Update initial context
    update_context({})

    # Setup watchers
    markdown_watcher = MarkdownWatcher()
    markdown_observer = Observer()
    markdown_observer.schedule(markdown_watcher, str(pwd), recursive=False)

    script_watcher = ScriptWatcher(__file__)
    script_observer = Observer()
    script_observer.schedule(script_watcher, os.path.dirname(os.path.abspath(__file__)), recursive=False)

    # Start observers
    markdown_observer.start()
    script_observer.start()

    console.print("👀 Watching project files for changes. Press Ctrl+C to stop...")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("Shutting down...")
        markdown_observer.stop()
        script_observer.stop()
        markdown_observer.join()
        script_observer.join()

if __name__ == '__main__':
    cli()
