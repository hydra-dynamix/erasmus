"""
File Watching System
==================

This module provides classes for monitoring file changes in the project.
It includes specialized watchers for different file types and use cases.

Classes:
    BaseWatcher: Generic file system event handler
    MarkdownWatcher: Specialized watcher for markdown documentation files
    ScriptWatcher: Specialized watcher for monitoring script files
    WatcherFactory: Factory class for creating and managing watchers
"""

import ast
import os
import time
from collections.abc import Callable
from pathlib import Path
from threading import Lock

from rich.console import Console
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from erasmus.utils.logging import LogContext, get_logger, log_execution

# Configure logging and console
logger = get_logger(__name__)
console = Console()

class BaseWatcher(FileSystemEventHandler):
    """Base class for file system event handlers."""

    def __init__(self, file_paths: dict[str, Path], callback: Callable[[str, str], None]):
        """Initialize the watcher.

        Args:
            file_paths: Dictionary mapping file keys to their paths
            callback: Function to call when a file changes
        """
        super().__init__()
        # Store both the original mapping and the normalized paths
        self.file_paths = file_paths
        self.callback = callback  # Store the callback
        self._path_mapping = {}
        for key, path in file_paths.items():
            resolved = str(path.resolve())
            self._path_mapping[resolved] = key
            logger.debug(f"Watching {key}: {resolved}")
        self._event_lock = Lock()
        self._last_events: dict[str, float] = {}

    def _should_process_event(self, event_path: str) -> bool:
        """Check if an event should be processed based on debouncing.

        Args:
            event_path: Path of the file that triggered the event

        Returns:
            True if the event should be processed, False otherwise
        """
        with self._event_lock:
            current_time = time.time()
            last_time = self._last_events.get(event_path, 0)

            # Debounce events within 0.1 seconds
            if current_time - last_time < 0.1:
                return False

            self._last_events[event_path] = current_time
            return True

    def _get_file_key(self, file_path: str) -> str | None:
        """Get the file key for a given path.

        Args:
            file_path: Path to look up

        Returns:
            File key if found, None otherwise
        """
        try:
            resolved_path = str(Path(file_path).resolve())
            logger.debug(f"Looking up file key for: {resolved_path}")
            logger.debug(f"Known paths: {list(self._path_mapping.keys())}")
            return self._path_mapping.get(resolved_path)
        except Exception as e:
            logger.exception(f"Error getting file key: {e}")
            return None

    @log_execution()
    def _handle_event(self, event: FileSystemEvent) -> None:
        """Handle a file system event.

        Args:
            event: The file system event to handle
        """
        if event.is_directory:
            logger.debug(f"Ignoring directory event: {event.src_path}")
            return

        file_path = event.src_path
        if not self._should_process_event(file_path):
            logger.debug(f"Debouncing event for: {file_path}")
            return

        file_key = self._get_file_key(file_path)
        if file_key is None:
            logger.debug(f"No file key found for: {file_path}")
            return

        with LogContext(logger, f"handle_event({file_key})"):
            try:
                if os.path.exists(file_path):
                    with open(file_path) as f:
                        content = f.read()
                    # Always accept the content since validation is disabled
                    logger.info(f"📝 Detected changes in {file_key}")
                    self.callback(file_key, content)
                else:
                    # For deletion events, we still want to notify with empty content
                    logger.info(f"File deleted: {file_key}")
                    self.callback(file_key, "")
            except Exception:
                logger.error(
                    f"Error handling event for {file_path}",
                    exc_info=True,
                )

    def _validate_content(self, content: str) -> bool:
        """Validate file content.

        Args:
            content: Content to validate

        Returns:
            Always returns True to accept any content
        """
        return True

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        self._handle_event(event)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        self._handle_event(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        self._handle_event(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file movement events."""
        self._handle_event(event)

class MarkdownWatcher(BaseWatcher):
    """Specialized watcher for markdown documentation files."""
    def __init__(self, file_paths: dict[str, Path], callback: Callable[[str], None]):
        super().__init__(file_paths, callback)

    def _validate_content(self, content: str) -> bool:
        """Validate markdown content.

        Args:
            content: Content to validate

        Returns:
            True if content is valid markdown, False otherwise
        """
        # Basic markdown validation
        lines = content.split("\n")
        if not lines:
            return False

        # Check for title
        return lines[0].startswith("# ")

class ScriptWatcher(BaseWatcher):
    """Specialized watcher for script files.

    TODO:
    - Integrate LSP for real-time validation
    - Add linting checks on file changes
    - Add dynamic unit test runner
    - Add context section for focus=path/to/script.py to track active development
    """
    def __init__(self, file_paths: dict[str, Path | str], callback: Callable[[str], None]):
        """Initialize the script watcher.

        Args:
            file_paths: Dictionary mapping script keys to paths
            callback: Function to call when scripts change
        """
        # Validate all paths
        normalized_paths = {}
        for key, path in file_paths.items():
            path = Path(path)
            if not str(path).endswith('.py'):
                raise ValueError(f"Script path {path} must end with .py")
            normalized_paths[key] = path

        super().__init__(normalized_paths, callback)

    def _validate_content(self, content: str) -> bool:
        """Validate Python script content.

        Args:
            content: Content to validate

        Returns:
            True if content is valid Python, False otherwise
        """
        try:
            ast.parse(content)
            return True
        except SyntaxError:
            return False

def run_observer(observer: Observer):
    """Run an observer in a separate thread.

    Args:
        observer: Observer to run
    """
    observer.start()
    try:
        while observer.is_alive():
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def create_file_watchers(setup_files: dict[str, Path],
                        update_callback: Callable[[str], None],
                        script_path: Path,
                        restart_callback: Callable[[str], None]) -> tuple[Observer, Observer]:
    """Create and configure file watchers.

    Args:
        setup_files: Dictionary mapping file keys to their paths
        update_callback: Callback for file updates
        script_path: Path to the script file
        restart_callback: Callback for script restarts

    Returns:
        Tuple of (markdown_observer, script_observer)
    """
    # Create watchers
    markdown_watcher = MarkdownWatcher(setup_files, update_callback)
    script_watcher = ScriptWatcher(script_path, restart_callback)

    # Create observers
    markdown_observer = Observer()
    script_observer = Observer()

    # Schedule watchers
    markdown_observer.schedule(markdown_watcher, str(script_path.parent), recursive=False)
    script_observer.schedule(script_watcher, str(script_path.parent), recursive=False)

    return markdown_observer, script_observer

class WatcherFactory:
    """Factory class for creating and managing watchers."""

    def __init__(self):
        """Initialize the factory."""
        self.observers: list[Observer] = []

    def create_markdown_watcher(self, file_paths: dict[str, Path], callback: Callable[[str], None]) -> MarkdownWatcher:
        """Create a markdown watcher.

        Args:
            file_paths: Dictionary mapping file keys to their paths
            callback: Function to call when files change

        Returns:
            Configured MarkdownWatcher
        """
        return MarkdownWatcher(file_paths, callback)

    def create_script_watcher(self, file_paths: dict[str, Path], callback: Callable[[str], None]) -> ScriptWatcher:
        """Create a script watcher.

        Args:
            file_paths: Dictionary mapping script keys to paths
            callback: Function to call when scripts change

        Returns:
            Configured ScriptWatcher
        """
        return ScriptWatcher(file_paths, callback)

    def create_observer(self, watcher: FileSystemEventHandler, directory: str) -> Observer:
        """Create and configure an observer.

        Args:
            watcher: Event handler to use
            directory: Directory to watch

        Returns:
            Configured Observer
        """
        observer = Observer()
        observer.schedule(watcher, directory, recursive=False)
        self.observers.append(observer)
        return observer

    def start_all(self) -> None:
        """Start all observers."""
        for observer in self.observers:
            if not observer.is_alive():
                observer.start()

    def stop_all(self) -> None:
        """Stop all observers."""
        for observer in self.observers:
            observer.stop()
            observer.join()
        self.observers.clear()
