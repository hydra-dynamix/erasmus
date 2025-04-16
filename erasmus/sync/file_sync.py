"""
File Synchronization Module
=========================

This module handles synchronization of project files to the rules directory,
ensuring that context files are properly copied and updated.
"""

import asyncio
import json
import logging
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from erasmus.utils.file import safe_read_file, safe_write_file
from erasmus.utils.paths import PathManager

logger = logging.getLogger(__name__)

TRACKED_FILES = [".architecture.md", ".progress.md", ".tasks.md"]


class FileChangeHandler(FileSystemEventHandler):
    """Handles file system events for tracked files."""

    def __init__(self, filename: str, callback: Callable[[str], None]):
        """Initialize the handler.

        Args:
            filename: Name of the file to track
            callback: Function to call when file changes
        """
        super().__init__()
        self.filename = filename
        self.callback = callback

    def on_modified(self, event):
        """Handle file modification events."""
        logger.debug(f"[Watcher] Detected modification: {event.src_path}")
        if not event.is_directory and Path(event.src_path).name == self.filename:
            logger.debug(f"[Watcher] Triggering callback for {self.filename}")
            self.callback(self.filename)


class FileSynchronizer:
    """Synchronizes file content between source files and a rules file."""

    TRACKED_FILES = [".architecture.md", ".progress.md", ".tasks.md"]

    def __init__(self, path_manager: PathManager):
        """Initialize the FileSynchronizer.

        Args:
            path_manager: PathManager instance for managing file paths
        """
        self.path_manager = path_manager
        self.content_cache: Dict[str, str] = {}
        self._running: bool = False
        self._errors: Dict[str, str] = {}
        self._pending_syncs: Set[str] = set()
        self._last_sync: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the file synchronizer and initialize the rules file."""
        if not os.path.exists(self.path_manager.rules_file):
            await self.create_rules_file()
        self._running = True
        await self.sync_all()

    async def stop(self) -> None:
        """Stop the file synchronizer."""
        self._running = False

    async def create_rules_file(self) -> None:
        """Create the rules file with initial empty content."""
        async with self._lock:
            try:
                os.makedirs(os.path.dirname(str(self.path_manager.rules_file)), exist_ok=True)
                with open(self.path_manager.rules_file, "w") as f:
                    json.dump({}, f)
            except Exception as e:
                self._errors[str(self.path_manager.rules_file)] = str(e)
                raise

    def _get_key_from_path(self, file_path: str) -> str:
        """Get the key to use in the rules file from a file path.

        Args:
            file_path: Path to the file

        Returns:
            str: Key to use in the rules file
        """
        base_name = os.path.basename(file_path)
        if base_name.startswith(".") and base_name.endswith(".md"):
            return base_name[1:-3]  # Remove leading dot and .md extension
        return base_name[:-3] if base_name.endswith(".md") else base_name

    async def sync_file(self, file_path: str) -> None:
        """Synchronize a single file's content with the rules file.

        Args:
            file_path: Path to the file to synchronize

        Raises:
            FileNotFoundError: If the file does not exist
            PermissionError: If there are permission issues
            json.JSONDecodeError: If the rules file contains invalid JSON
            Exception: For other synchronization errors
        """
        if not self._running:
            return

        self._pending_syncs.add(file_path)
        try:
            async with self._lock:
                if not os.path.exists(file_path):
                    error = "File not found"
                    self._errors[file_path] = error
                    raise FileNotFoundError(error)

                try:
                    with open(file_path, "r") as f:
                        content = f.read()
                except PermissionError as e:
                    self._errors[file_path] = f"Permission denied: {str(e)}"
                    raise

                if content == self.content_cache.get(file_path):
                    return

                self.content_cache[file_path] = content
                await self._update_rules_file()
                self._last_sync[file_path] = datetime.now()
                if file_path in self._errors:
                    del self._errors[file_path]

        except Exception as e:
            self._errors[file_path] = str(e)
            raise
        finally:
            if file_path in self._pending_syncs:
                self._pending_syncs.remove(file_path)

    async def sync_all(self) -> None:
        """Synchronize all tracked files."""
        for file_path in self.TRACKED_FILES:
            try:
                full_path = os.path.join(str(self.path_manager.project_root), file_path)
                await self.sync_file(full_path)
            except Exception as e:
                self._errors[full_path] = str(e)
                raise

    async def _update_rules_file(self) -> None:
        """Update the rules file with current content from all files.

        Raises:
            PermissionError: If the rules file cannot be written
            json.JSONDecodeError: If the current rules file contains invalid JSON
            Exception: For other update errors
        """
        rules_file = str(self.path_manager.rules_file)

        # First try to read existing content if file exists
        if os.path.exists(rules_file):
            try:
                with open(rules_file, "r") as f:
                    content = f.read()
                try:
                    current_content = json.loads(content)
                except json.JSONDecodeError as e:
                    self._errors[rules_file] = f"Invalid JSON: {str(e)}"
                    raise
            except PermissionError as e:
                self._errors[rules_file] = f"Permission denied: {str(e)}"
                raise
        else:
            current_content = {}

        # Update with new content
        for file_path, content in self.content_cache.items():
            key = self._get_key_from_path(file_path)
            current_content[key] = content

        # Write back
        try:
            os.makedirs(os.path.dirname(rules_file), exist_ok=True)
            with open(rules_file, "w") as f:
                json.dump(current_content, f, indent=2)
        except PermissionError as e:
            self._errors[rules_file] = f"Permission denied: {str(e)}"
            raise
        except Exception as e:
            self._errors[rules_file] = str(e)
            raise

    def get_status(self) -> dict:
        """Get the current status of file synchronization.

        Returns:
            dict: Status information including errors, pending syncs, and last sync times
        """
        return {
            "running": self._running,
            "errors": self._errors,
            "pending_syncs": list(self._pending_syncs),
            "last_sync": {k: v.isoformat() for k, v in self._last_sync.items()},
        }
