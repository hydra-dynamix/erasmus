import os
import time
from typing import Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from pathlib import Path
from erasmus.protocol import get_protocol_manager
from erasmus.utils.paths import get_path_manager
from erasmus.utils.rich_console import get_console_logger
import re
import fnmatch

logger = get_console_logger()

# Add a global to track last rules file write time
_last_rules_write_time = None

path_manager = get_path_manager()
protocol_manager = get_protocol_manager()

def _merge_rules_file() -> None:
    # Split this function into smaller functions in a future refactor
    # Current complexity is necessary for handling various file states and formats
    """
    Merge current .ctx files into the IDE rules file using the meta_rules.md template.
    Refreshes IDE detection to ensure correct rules file is used.
    Overwrites the rules file every time with a fresh merge of the template and current context/protocol content.
    Prompts the user to select a protocol if none is set or the file is missing.
    """
    try:
        architecture = path_manager.architecture_file.read_text()
        progress = path_manager.progress_file.read_text()
        tasks = path_manager.tasks_file.read_text()
        if not protocol_manager.protocol:
            protocol_manager.select_protocol_interactively(
                prompt_title="Select a protocol for the rules file",
                error_title="Protocol not selected"
            )
        protocol = protocol_manager.protocol.content
        template_path = path_manager.template_dir / "meta_rules.md"
        template = template_path.read_text()
        template = template.replace("<!-- Architecture content -->", architecture)
        template = template.replace("<!-- Progress content -->", progress)
        template = template.replace("<!-- Tasks content -->", tasks)
        template = template.replace("<!-- Protocol content -->", protocol)
        path_manager.rules_file.write_text(template)
        logger.info("Rules file merged successfully")
    except Exception as error:
        logger.error(f"Error merging rules file: {error}")


class FileEventHandler(FileSystemEventHandler):
    """
    Handles file system events with debouncing.
    """

    def __init__(self, debounce_time: float = 0.1) -> None:
        """
        Initialize the event handler.
        Args:
            debounce_time: Time in seconds to wait before processing duplicate events
        """
        super().__init__()
        self.debounce_time: float = debounce_time
        self.processed_events: Set[str] = set()
        self.last_processed: dict[str, float] = {}
        self.on_created = None
        self.on_modified = None
        self.on_deleted = None
        self.ignore_directory_events = False

    def _should_process_event(self, event: FileSystemEvent) -> bool:
        """
        Check if an event should be processed based on debouncing and filtering.
        Args:
            event: The file system event
        Returns:
            bool: True if event should be processed
        """
        # Skip directory events if configured
        if self.ignore_directory_events and event.is_directory:
            return False

        current_time = time.time()
        event_key = f"{event.event_type}:{event.src_path}"

        # Check if this is a duplicate event within debounce time
        if event_key in self.last_processed:
            if current_time - self.last_processed[event_key] < self.debounce_time:
                return False

        self.last_processed[event_key] = current_time
        return True

    def on_created(self, event: FileSystemEvent) -> None:
        """
        Handle file creation events.
        Args:
            event: The file system event
        """
        if self._should_process_event(event):
            if self.on_created:
                self.on_created(event)
                # For directory creation, also emit an event for the parent directory
                if event.is_directory:
                    parent_dir = os.path.dirname(event.src_path)
                    if parent_dir:
                        parent_event = FileSystemEvent(
                            event_type="created", src_path=parent_dir, is_directory=True
                        )
                        if self.on_created:
                            self.on_created(parent_event)

    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification events.
        Args:
            event: The file system event
        """
        if self._should_process_event(event):
            if self.on_modified:
                self.on_modified(event)
                # For file modification, also emit an event for the parent directory
                if not event.is_directory:
                    parent_dir = os.path.dirname(event.src_path)
                    if parent_dir:
                        parent_event = FileSystemEvent(
                            event_type="modified", src_path=parent_dir, is_directory=True
                        )
                        if self.on_modified:
                            self.on_modified(parent_event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """
        Handle file deletion events.
        Args:
            event: The file system event
        """
        if self._should_process_event(event):
            if self.on_deleted:
                # Process the original event first
                self.on_deleted(event)
                # For file deletion, also emit an event for the parent directory
                if not event.is_directory:
                    parent_dir = os.path.dirname(event.src_path)
                    if parent_dir:
                        parent_event = FileSystemEvent(
                            event_type="deleted", src_path=parent_dir, is_directory=True
                        )
                        self.on_deleted(parent_event)
                # For directory deletion, also emit an event for the parent directory
                elif event.is_directory:
                    parent_dir = os.path.dirname(event.src_path)
                    if parent_dir:
                        parent_event = FileSystemEvent(
                            event_type="deleted", src_path=parent_dir, is_directory=True
                        )
                        self.on_deleted(parent_event)


class FileMonitor:
    """
    Monitors file system events and updates rules files.
    """

    def __init__(self) -> None:
        """Initialize the file monitor."""
        self.pm = get_path_manager()
        self.debug = os.getenv("ERASMUS_DEBUG", "false").lower() == "true"
        if self.debug:
            logger.info(f"Initialized FileMonitor with path manager: {self.pm}")
        self.observer = Observer()
        self.event_handler = FileEventHandler()
        self.watch_paths: dict[str, bool] = {
            str(self.pm.architecture_file): True,
            str(self.pm.progress_file): True,
            str(self.pm.tasks_file): True,
        }  # path -> recursive
        if self.debug:
            logger.info(f"Watch paths configured: {self.watch_paths}")
        self.ignore_patterns: list[str] = []
        self.on_created = None
        self.on_modified = None
        self.on_deleted = None
        self._is_running = False
        self._last_merge_time = 0
        self._merge_debounce = 0.5  # Debounce time for merging rules

    def _should_merge_rules(self) -> bool:
        """Check if enough time has passed since last merge."""
        current_time = time.time()
        should_merge = current_time - self._last_merge_time > self._merge_debounce
        if should_merge:
            if self.debug:
                logger.debug("Debounce period passed, will merge rules")
            self._last_merge_time = current_time
        elif self.debug:
            logger.debug("Within debounce period, skipping merge")
        return should_merge

    def _handle_context_change(self, event: FileSystemEvent) -> None:
        """Handle changes to context files."""
        if self.debug:
            logger.info(f"Handling context change event: {event.event_type} - {event.src_path}")
        if self._matches_rules_file(event.src_path):
            if self.debug:
                logger.debug(f"Ignoring rules file change: {event.src_path}")
            return

        if self._should_merge_rules():
            logger.info(f"Merging rules due to context file change: {event.src_path}")
            try:
                _merge_rules_file()
                logger.info("Rules merge completed successfully")
            except Exception as error:
                logger.error(f"Error merging rules: {error}")

    def add_watch_path(self, watch_path: str | Path, recursive: bool = False) -> None:
        """Add a path to monitor."""
        watch_path = str(Path(watch_path).resolve())
        if not os.path.exists(watch_path):
            raise FileMonitorError(f"Watch path does not exist: {watch_path}")
        self.watch_paths[watch_path] = recursive
        if self._is_running:
            self.observer.schedule(self.event_handler, watch_path, recursive=recursive)
            logger.info(f"Added watch path: {watch_path}")

    def remove_watch_path(self, watch_path: str | Path) -> None:
        """Remove a monitored path."""
        watch_path = str(Path(watch_path).resolve())
        if watch_path in self.watch_paths:
            del self.watch_paths[watch_path]
            if self._is_running:
                # Find and remove the watch for this path
                for watch in list(self.observer._watches.values()):
                    if watch.path == watch_path:
                        self.observer.unschedule(watch)
                        logger.info(f"Removed watch path: {watch_path}")
                        break

    def add_ignore_pattern(self, pattern: str) -> None:
        """Add a pattern to ignore."""
        self.ignore_patterns.append(pattern)
        logger.info(f"Added ignore pattern: {pattern}")

    def _matches_ignore_pattern(self, file_path: str) -> bool:
        """Check if a file path matches any ignore pattern."""
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.ignore_patterns)

    def _matches_rules_file(self, file_path: str) -> bool:
        """Check if a file path matches any rules file pattern."""
        rules_patterns = [
            r"\.codex\.md$",
            r"\.cursorrules$",
            r"\.windsurfrules$",
            r"CLAUDE\.md$",
        ]
        matches = any(re.search(pattern, file_path) for pattern in rules_patterns)
        if matches and self.debug:
            logger.debug(f"File matches rules pattern: {file_path}")
        return matches

    def start(self) -> None:
        """Start monitoring."""
        if not self.watch_paths:
            raise FileMonitorError("No watch paths configured")

        if self._is_running:
            logger.warning("Monitor is already running")
            return

        logger.info("Starting file monitor...")

        # Set up event handlers
        def on_created_wrapper(event):
            if self.debug:
                logger.debug(f"Created event received: {event.src_path}")
            if self._matches_ignore_pattern(event.src_path):
                if self.debug:
                    logger.debug(f"Ignoring created event due to pattern match: {event.src_path}")
                return
            self._handle_context_change(event)
            if self.on_created:
                self.on_created(event)

        def on_modified_wrapper(event):
            if self.debug:
                logger.debug(f"Modified event received: {event.src_path}")
            if self._matches_ignore_pattern(event.src_path):
                if self.debug:
                    logger.debug(f"Ignoring modified event due to pattern match: {event.src_path}")
                return
            self._handle_context_change(event)
            if self.on_modified:
                self.on_modified(event)

        def on_deleted_wrapper(event):
            if self.debug:
                logger.debug(f"Deleted event received: {event.src_path}")
            if self._matches_ignore_pattern(event.src_path):
                if self.debug:
                    logger.debug(f"Ignoring deleted event due to pattern match: {event.src_path}")
                return
            self._handle_context_change(event)
            if self.on_deleted:
                self.on_deleted(event)

        self.event_handler.on_created = on_created_wrapper
        self.event_handler.on_modified = on_modified_wrapper
        self.event_handler.on_deleted = on_deleted_wrapper

        # Start observer for each watch path
        for watch_path, recursive in self.watch_paths.items():
            # Ensure the watch path exists
            if not os.path.exists(watch_path):
                logger.warning(f"Watch path does not exist, creating: {watch_path}")
                os.makedirs(os.path.dirname(watch_path), exist_ok=True)
                Path(watch_path).touch()

            # Schedule the watch
            try:
                self.observer.schedule(
                    self.event_handler, os.path.dirname(watch_path), recursive=recursive
                )
                logger.info(f"Started monitoring: {watch_path} (recursive={recursive})")
            except Exception as error:
                logger.error(f"Failed to schedule watch for {watch_path}: {error}")

        try:
            self.observer.start()
            logger.info("File monitor observer started successfully")
        except Exception as error:
            logger.error(f"Failed to start observer: {error}")
            return

        self._is_running = True

        # Initial merge of rules
        logger.info("Performing initial rules merge...")
        try:
            _merge_rules_file()
            logger.info("Initial rules merge completed successfully")
        except Exception as error:
            logger.error(f"Error during initial rules merge: {error}")

    def stop(self) -> None:
        """Stop monitoring."""
        if not self._is_running:
            logger.warning("Monitor is not running")
            return

        logger.info("Stopping file monitor...")
        if self.observer.is_alive():
            try:
                self.observer.stop()
                self.observer.join()
                self.observer = Observer()  # Create a new observer for next start
                for watch_path in self.watch_paths:
                    logger.info(f"Stopped monitoring: {watch_path}")
                logger.info("File monitor stopped successfully")
            except Exception as error:
                logger.error(f"Error stopping observer: {error}")
        self._is_running = False

    def __enter__(self) -> "FileMonitor":
        """Start monitoring when entering context."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop monitoring when exiting context."""
        self.stop()


class FileMonitorError(Exception):
    """Base exception for file monitor errors."""


class ContextFileMonitor:
    """Monitors .ctx files and updates the rules file."""

    def __init__(self) -> None:
        """Initialize the context file monitor."""
        from erasmus.utils.paths import get_path_manager

        self.path_manager = get_path_manager()
        self.observer = Observer()
        self.handler = ContextFileHandler()
        self.root_dir = self.path_manager.get_root_dir()
        self.logger = logger

    def start(self) -> None:
        """Start monitoring context files."""
        try:
            # Watch the root directory for .ctx files
            self.observer.schedule(self.handler, str(self.root_dir), recursive=False)
            self.observer.start()
            self.logger.info(f"Started monitoring {self.root_dir} for .ctx file changes")

            # Initial merge of rules file
            _merge_rules_file()
            self.logger.info("Initial rules file merge completed")

        except Exception as error:
            self.logger.error(f"Error starting context file monitor: {error}")
            raise FileMonitorError(f"Failed to start context file monitor: {error}")

    def stop(self) -> None:
        """Stop monitoring context files."""
        try:
            self.observer.stop()
            self.observer.join()
            self.logger.info("Stopped context file monitor")
        except Exception as error:
            self.logger.error(f"Error stopping context file monitor: {error}")

    def __enter__(self) -> "ContextFileMonitor":
        """Start monitoring when entering context."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop monitoring when exiting context."""
        self.stop()


class ContextFileHandler(FileSystemEventHandler):
    """Handles file system events for context files."""

    def __init__(self, debounce_time: float = 0.5) -> None:
        """Initialize the context file handler.

        Args:
            debounce_time: Time in seconds to wait before processing duplicate events
        """
        super().__init__()
        self.debounce_time = debounce_time
        self.last_processed = {}


    def _should_process_event(self, event: FileSystemEvent) -> bool:
        """Check if an event should be processed.

        Args:
            event: The file system event

        Returns:
            bool: True if the event should be processed
        """
        if event.is_directory:
            return False

        # Only process .ctx.*.md files
        if not str(event.src_path).endswith(".md") or ".ctx." not in str(event.src_path):
            return False

        current_time = time.time()
        if event.src_path in self.last_processed:
            if current_time - self.last_processed[event.src_path] < self.debounce_time:
                return False

        self.last_processed[event.src_path] = current_time
        return True

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.

        Args:
            event: The file system event
        """
        if self._should_process_event(event):
            try:
                self.logger.info(f"Context file modified: {event.src_path}")
                _merge_rules_file()
                self.logger.info("Rules file updated")
            except Exception as error:
                self.logger.error(f"Error handling context file modification: {error}")

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events.

        Args:
            event: The file system event
        """
        if self._should_process_event(event):
            try:
                self.logger.info(f"Context file created: {event.src_path}")
                _merge_rules_file()
                self.logger.info("Rules file updated")
            except Exception as error:
                self.logger.error(f"Error handling context file creation: {error}")

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events.

        Args:
            event: The file system event
        """
        if self._should_process_event(event):
            try:
                self.logger.info(f"Context file deleted: {event.src_path}")
                _merge_rules_file()
                self.logger.info("Rules file updated")
            except Exception as error:
                self.logger.error(f"Error handling context file deletion: {error}")
