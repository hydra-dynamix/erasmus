"""
Synchronization Integration Module
===============================

This module provides integration between the FileSynchronizer and CursorContextManager,
handling bi-directional synchronization of context files.
"""

import asyncio
import json
import logging
from pathlib import Path

from erasmus.utils.file import safe_read_file, safe_write_file

logger = logging.getLogger(__name__)


class SyncIntegration:
    """Handles integration between FileSynchronizer and CursorContextManager."""

    def __init__(self, context_manager, workspace_path: Path):
        """Initialize the sync integration."""
        self.context_manager = context_manager
        self.workspace_path = workspace_path
        self._running = False
        self._sync_lock = asyncio.Lock()
        self._file_change_events = {}
        self._sync_tasks = []
        self._last_sync = {}
        self._update_retries = {}
        self.source_files = {
            "architecture": workspace_path / ".erasmus/.architecture.md",
            "progress": workspace_path / ".progress.md",
            "tasks": workspace_path / ".tasks.md",
        }

    async def start(self):
        """Start the synchronization integration."""
        self._running = True
        # Perform initial sync
        await self.sync_all()

    async def stop(self):
        """Stop the sync integration."""
        self._running = False
        # Cancel any pending sync tasks
        for task in self._sync_tasks:
            if not task.done():
                task.cancel()
        self._sync_tasks.clear()
        self._file_change_events.clear()

    async def sync_all(self):
        """Synchronize all components."""
        try:
            # Clear any existing events
            self._file_change_events.clear()

            # Process each component sequentially to avoid race conditions
            for component in ["architecture", "progress", "tasks"]:
                file_path = self.source_files[component]
                if file_path.exists():
                    try:
                        # Read content
                        content = file_path.read_text()

                        # Create event for this sync
                        self._file_change_events[component] = asyncio.Event()
                        update_successful = False

                        # Try update with retries
                        for attempt in range(2):
                            if attempt > 0:
                                logger.info(
                                    f"Retrying initial sync for {component} (attempt {attempt + 1})"
                                )
                                await asyncio.sleep(0.2)

                            update_task = asyncio.create_task(
                                self.context_manager.queue_update(component, content),
                            )
                            self._sync_tasks.append(update_task)

                            try:
                                # Wait for update with timeout
                                success = await asyncio.wait_for(update_task, timeout=5.0)

                                if success:
                                    # Verify the update
                                    rules_content = safe_read_file(self.context_manager.rules_file)
                                    if rules_content:
                                        rules = json.loads(rules_content)
                                        if component in rules and rules[component] == content:
                                            update_successful = True
                                            break

                                if attempt == 0:
                                    logger.warning(
                                        f"Initial sync verification failed for {component}, will retry"
                                    )
                                else:
                                    logger.error(
                                        f"Initial sync verification failed for {component} after retry"
                                    )

                            except asyncio.TimeoutError:
                                logger.exception(f"Timeout during initial sync of {component}")
                                if attempt == 1:  # Second attempt
                                    raise
                            finally:
                                if update_task in self._sync_tasks:
                                    self._sync_tasks.remove(update_task)

                        # Set event based on final result
                        if update_successful:
                            self._file_change_events[component].set()

                        # Wait briefly between components
                        await asyncio.sleep(0.2)

                    finally:
                        # Clean up the event
                        if component in self._file_change_events:
                            del self._file_change_events[component]

        except Exception as e:
            logger.exception(f"Error during sync_all: {e}")
            raise

    async def handle_file_change(self, file_path: Path) -> None:
        """Handle changes to source files."""
        if not self._running:
            return

        try:
            # Get the component key from the file name
            component = file_path.stem.lower()
            if component not in ["architecture", "progress", "tasks"]:
                return

            # Create event before any processing
            self._file_change_events[component] = asyncio.Event()
            update_successful = False

            try:
                # Acquire lock to prevent concurrent updates to the same file
                async with self._sync_lock:
                    # Read the updated content
                    content = file_path.read_text()

                    # Update rules file directly
                    rules_file = self.context_manager.rules_file
                    try:
                        current_rules = (
                            json.loads(safe_read_file(rules_file)) if rules_file.exists() else {}
                        )
                    except json.JSONDecodeError:
                        current_rules = {}

                    # Update the specific component
                    current_rules[component] = content

                    # Write updated rules
                    safe_write_file(rules_file, json.dumps(current_rules, indent=2))
                    self._last_sync[component] = content
                    update_successful = True

                    # Set event based on final result
                    if update_successful:
                        self._file_change_events[component].set()

            finally:
                # Clean up the event after all retries
                if component in self._file_change_events:
                    # Wait briefly to ensure any waiters have processed
                    await asyncio.sleep(0.1)
                    del self._file_change_events[component]

        except Exception as e:
            logger.exception(f"Error handling file change for {file_path}: {e}")
            raise

    async def handle_context_change(self, component: str, content: str) -> None:
        """Handle changes to context."""
        if not self._running or component not in self.source_files:
            return

        try:
            async with self._sync_lock:
                file_path = self.source_files[component]
                if not file_path.exists():
                    return

                current_content = safe_read_file(file_path)

                # Only update if content is different and no file change event is pending
                if content != current_content and component not in self._file_change_events:
                    # Write atomically using temporary file
                    temp_path = file_path.with_suffix(".tmp")
                    try:
                        safe_write_file(temp_path, content)
                        temp_path.replace(file_path)
                    finally:
                        if temp_path.exists():
                            temp_path.unlink()

        except Exception as e:
            logger.exception(f"Error handling context change for {component}: {e}")
            raise
