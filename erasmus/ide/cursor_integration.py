"""
cursor IDE Integration Module
==========================

This module provides specialized integration with the cursor IDE,
handling context synchronization and rule formatting specific to
cursor's requirements.
"""

import asyncio
import contextlib
import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from erasmus.utils.file import safe_read_file, safe_write_file
from erasmus.utils.paths import SetupPaths

from .sync_integration import SyncIntegration

logger = logging.getLogger(__name__)


class CursorContextManager:
    """Manages context for Cursor IDE integration."""

    def __init__(self, project_root: Path):
        """Initialize the context manager.

        Args:
            project_root: Path to the project root directory
        """
        self.setup_paths = SetupPaths.with_project_root(project_root)
        self.rules_file = self.setup_paths.rules_file
        self._update_queue = asyncio.Queue()
        self._running = False
        self._task = None
        self._lock = asyncio.Lock()
        self._errors = []
        self._last_update = {}
        self._pending_updates = set()

    async def start(self):
        """Start the context manager."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._process_updates())
            # Initialize rules file if it doesn't exist
            if not self.rules_file.exists():
                self.rules_file.write_text("{}")

    async def stop(self):
        """Stop the context manager."""
        if self._running:
            self._running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None

    async def queue_update(self, key: str, value: str):
        """Queue an update to the rules file.

        Args:
            key: Key to update
            value: New value
        """
        if not self._running:
            logger.warning("CursorContextManager is not running")
            return False

        update_event = asyncio.Event()
        await self._update_queue.put((key, value, update_event))

        try:
            # Wait for update to complete
            await asyncio.wait_for(update_event.wait(), timeout=5.0)

            # Verify update was written
            if self.rules_file.exists():
                content = self.rules_file.read_text()
                current = json.loads(content)
                if key not in current or current[key] != value:
                    logger.error(f"Update verification failed for {key}")
                    return False
            return True

        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for update to complete: {key}")
            return False
        except Exception as e:
            logger.error(f"Error in queue_update: {str(e)}", exc_info=True)
            return False

    async def process_updates(self):
        """Process all pending updates."""
        if not self._running:
            return

        # Wait for all queued items to be processed
        await self._update_queue.join()

    async def handle_file_change(self, file_path: str):
        """Handle a file change event.

        Args:
            file_path: Path to the changed file
        """
        # Get absolute path for the file
        abs_path = self.setup_paths.project_root / file_path
        if not abs_path.exists():
            logger.error(f"File not found: {abs_path}")
            return

        try:
            content = abs_path.read_text()
            await self.queue_update(file_path, content)
        except Exception as e:
            logger.error(f"Error reading file {abs_path}: {str(e)}", exc_info=True)

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the context manager.

        Returns:
            Dict containing status information
        """
        return {
            "is_running": self._running,
            "has_errors": bool(self._errors),
            "pending_updates": list(self._pending_updates),
            "errors": self._errors.copy(),
            "last_update": self._last_update.copy(),
        }

    async def _process_updates(self):
        """Process updates from the queue."""
        while self._running:
            try:
                key, value, update_event = await self._update_queue.get()
                self._pending_updates.add(key)

                try:
                    async with self._lock:
                        # Read current rules, handle invalid JSON
                        try:
                            rules_content = (
                                self.rules_file.read_text() if self.rules_file.exists() else None
                            )
                            current = json.loads(rules_content) if rules_content else {}
                        except json.JSONDecodeError:
                            logger.warning("Invalid JSON in rules file, resetting to empty state")
                            current = {}

                        # Update rules
                        current[key] = value

                        # Write back
                        self.rules_file.write_text(json.dumps(current, indent=2))

                        # Update status
                        self._last_update = {"key": key, "timestamp": time.time()}
                        self._pending_updates.remove(key)

                    # Set event after lock is released
                    update_event.set()

                except Exception as e:
                    logger.error(f"Error processing update for {key}: {str(e)}", exc_info=True)
                    self._errors.append({"key": key, "error": str(e), "timestamp": time.time()})
                    update_event.set()  # Still set the event to unblock waiting code

                finally:
                    self._update_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in update processor: {str(e)}", exc_info=True)
                if self._update_queue.qsize() > 0:
                    self._update_queue.task_done()  # Ensure we don't deadlock
                continue


class CursorRulesHandler(FileSystemEventHandler):
    """Handles file system events for the rules file."""

    def __init__(self, manager: CursorContextManager):
        """Initialize the handler."""
        self.manager = manager
        self._last_event_time = {}
        self._debounce_delay = 0.1  # 100ms debounce

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if not event.is_directory:
            file_path = Path(event.src_path)
            current_time = time.time()

            # Debounce events for the same file
            if file_path in self._last_event_time:
                if current_time - self._last_event_time[file_path] < self._debounce_delay:
                    return

            self._last_event_time[file_path] = current_time

            # Handle rules file changes
            if file_path == self.manager.rules_file:
                try:
                    # Read the current rules
                    content = safe_read_file(self.manager.rules_file)
                    if not content:
                        return

                    current = json.loads(content)

                    # Store external changes
                    for comp, cont in current.items():
                        if comp not in self.manager._pending_updates:
                            self.manager._external_changes[comp] = cont

                except Exception as e:
                    logger.exception(f"Error handling external change: {e}")

            # Handle source file changes
            elif file_path.suffix == ".md" and file_path.stem.lower() in [
                "architecture",
                "progress",
                "tasks",
            ]:
                try:
                    # Put the file path directly into the thread-safe queue
                    self.manager._thread_queue.put_nowait(file_path)
                except Exception as e:
                    logger.exception(f"Error queueing file change: {e}")
