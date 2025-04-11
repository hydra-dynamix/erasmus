"""
cursor IDE Integration Module
==========================

This module provides specialized integration with the cursor IDE,
handling context synchronization and rule formatting specific to
cursor's requirements.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from ..utils.file import safe_read_file, safe_write_file
from .sync_integration import SyncIntegration

logger = logging.getLogger(__name__)

class CursorContextManager:
    """Manages context updates for the cursor IDE."""

    def __init__(self, workspace_path: Path):
        """Initialize the CursorContextManager."""
        self.workspace_path = workspace_path
        self.rules_file = workspace_path / ".cursorrules" / "rules.json"
        self.batch_delay = 0.1  # seconds
        self._update_queue = asyncio.Queue()
        self._current_rules = {}
        self._update_task = None
        self._running = False
        self._error_counts = defaultdict(int)
        self._lock = asyncio.Lock()
        self._watcher = None
        self._processing = False
        self._last_write_time = 0
        self._write_event = asyncio.Event()
        self._update_complete = asyncio.Event()
        self._pending_updates = {}
        self._external_changes = {}
        self._sync_integration = None
        self._observer = None
        self._recovery_task = None
        self._update_events = {}
        self._file_change_queue = asyncio.Queue()
        self._file_change_task = None
        self._thread_queue = asyncio.Queue()  # Queue for thread-safe communication
        self._thread_task = None

    async def start(self):
        """Start the context manager."""
        if self._running:
            return

        try:
            # Create rules directory if it doesn't exist
            rules_dir = self.rules_file.parent
            rules_dir.mkdir(parents=True, exist_ok=True)

            # Initialize rules file if it doesn't exist
            try:
                if not self.rules_file.exists():
                    # Write empty JSON object to file
                    safe_write_file(self.rules_file, "{}")

                # Load current rules
                content = safe_read_file(self.rules_file)
                self._current_rules = json.loads(content) if content else {}
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.error(f"Error loading rules file: {e}")
                self._current_rules = {}
                # Ensure we have a valid rules file
                safe_write_file(self.rules_file, "{}")

            # Set running flag before starting tasks
            self._running = True

            # Start the update processing loop
            self._update_task = asyncio.create_task(self._process_updates())

            # Start the file change processing loop
            self._file_change_task = asyncio.create_task(self._process_file_changes())

            # Start the thread queue processing loop
            self._thread_task = asyncio.create_task(self._process_thread_queue())

            # Initialize file watcher
            self._watcher = CursorRulesHandler(self)
            self._observer = Observer()
            self._observer.schedule(self._watcher, str(self.workspace_path), recursive=False)
            self._observer.daemon = True
            self._observer.start()

            # Start recovery task
            self._recovery_task = asyncio.create_task(self._monitor_and_recover())

            # Initialize sync integration
            self._sync_integration = SyncIntegration(self, self.workspace_path)

            # Wait for tasks to be ready
            await asyncio.sleep(0.2)

            # Start sync integration and perform initial sync
            await self._sync_integration.start()

            # Wait for initial sync to complete
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error starting context manager: {e}")
            # Clean up on error
            await self.stop()
            raise

    async def stop(self):
        """Stop the context manager."""
        if not self._running:
            return

        self._running = False

        # Stop the observer
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

        # Stop sync integration
        if self._sync_integration:
            await self._sync_integration.stop()

        # Cancel tasks
        for task in [self._update_task, self._recovery_task, self._file_change_task, self._thread_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Clear state
        self._watcher = None
        self._current_rules = {}
        self._pending_updates.clear()
        self._external_changes.clear()
        self._update_task = None
        self._recovery_task = None
        self._update_events.clear()
        self._file_change_task = None
        self._thread_task = None

    async def queue_update(self, component: str, content: Any) -> bool:
        """Queue an update for processing."""
        if not self._running:
            logger.warning("CursorContextManager is not running")
            return False

        try:
            # Create an event for this update
            update_event = asyncio.Event()
            self._update_events[component] = update_event

            # Queue the update
            self._pending_updates[component] = content
            await self._update_queue.put((component, content))

            try:
                # Wait for update to be processed
                await asyncio.wait_for(update_event.wait(), timeout=5.0)

                # Wait briefly for file system sync
                await asyncio.sleep(0.1)

                # Verify the update was written correctly
                verify_content = safe_read_file(self.rules_file)
                verify_rules = json.loads(verify_content) if verify_content else {}

                if component in verify_rules and verify_rules[component] == content:
                    return True

                logger.error(f"Update verification failed for {component}")
                return False

            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for update to complete: {component}")
                return False

        except Exception as e:
            logger.error(f"Error queueing update: {e}")
            return False

        finally:
            # Clean up
            if component in self._update_events:
                del self._update_events[component]
            if component in self._pending_updates:
                del self._pending_updates[component]

    async def _process_updates(self):
        """Process queued updates."""
        while self._running:
            try:
                # Get the next update
                component, content = await self._update_queue.get()

                # Process update immediately
                async with self._lock:
                    try:
                        # Read current rules
                        rules_content = safe_read_file(self.rules_file)
                        current = json.loads(rules_content) if rules_content else {}

                        # Store external changes that aren't being updated
                        new_external_changes = {}
                        for comp, cont in self._external_changes.items():
                            if comp not in self._pending_updates:
                                current[comp] = cont
                            else:
                                new_external_changes[comp] = cont
                        self._external_changes = new_external_changes

                        # Apply update
                        current[component] = content

                        # Write update atomically
                        temp_file = self.rules_file.with_suffix('.tmp')
                        try:
                            safe_write_file(temp_file, json.dumps(current, indent=2))
                            temp_file.replace(self.rules_file)

                            # Update current rules
                            self._current_rules = current.copy()

                            # Notify waiters
                            if component in self._update_events:
                                self._update_events[component].set()
                            if component in self._pending_updates:
                                del self._pending_updates[component]

                            # Notify sync integration of context change
                            if self._sync_integration:
                                try:
                                    await self._sync_integration.handle_context_change(component, content)
                                except Exception as e:
                                    logger.error(f"Error in sync integration: {e}")

                        finally:
                            if temp_file.exists():
                                temp_file.unlink()

                    except Exception as e:
                        logger.error(f"Error processing update for {component}: {e}")
                        # Set event even on error to prevent timeouts
                        if component in self._update_events:
                            self._update_events[component].set()
                        if component in self._pending_updates:
                            del self._pending_updates[component]

            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                await asyncio.sleep(0.1)

    async def _process_file_changes(self):
        """Process file change events."""
        while self._running:
            try:
                # Get the next file change
                file_path = await self._file_change_queue.get()

                # Process the file change
                if self._sync_integration:
                    await self._sync_integration.handle_file_change(file_path)

            except Exception as e:
                logger.error(f"Error processing file change: {e}")
                await asyncio.sleep(0.1)

    async def _process_thread_queue(self):
        """Process items from the thread-safe queue."""
        while self._running:
            try:
                # Get the next item from the thread queue
                file_path = await self._thread_queue.get()

                # Queue it for file change processing
                await self._file_change_queue.put(file_path)

            except Exception as e:
                logger.error(f"Error processing thread queue: {e}")
                await asyncio.sleep(0.1)

    async def _monitor_and_recover(self):
        """Monitor the rules file and recover from errors."""
        while self._running:
            try:
                # Check if rules file is valid
                content = safe_read_file(self.rules_file)
                try:
                    current = json.loads(content) if content else {}
                except json.JSONDecodeError:
                    # File is corrupted, restore from backup
                    logger.warning("Rules file corrupted, restoring from current state")
                    safe_write_file(self.rules_file, json.dumps(self._current_rules, indent=2))

                # Brief wait before next check
                await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(f"Error in recovery monitor: {e}")
                await asyncio.sleep(1.0)

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
                    logger.error(f"Error handling external change: {e}")

            # Handle source file changes
            elif file_path.suffix == ".md" and file_path.stem.lower() in ["architecture", "progress", "tasks"]:
                try:
                    # Put the file path directly into the thread-safe queue
                    self.manager._thread_queue.put_nowait(file_path)
                except Exception as e:
                    logger.error(f"Error queueing file change: {e}")
