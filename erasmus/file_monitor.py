import os
import time
from typing import Optional, Set
from watchdog.observers import ObserverType, Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from loguru import logger
from pathlib import Path
from erasmus.utils.paths import get_path_manager
import re
from erasmus.protocol import ProtocolManager
import xml.etree.ElementTree as ET

# Add a global to track last rules file write time
_last_rules_write_time = None


def _merge_rules_file() -> None:
    """
    Merge current .ctx files into the IDE rules file using the meta_rules.xml template.
    Refreshes IDE detection to ensure correct rules file is used.
    Overwrites the rules file every time with a fresh merge of the template and current context/protocol content.
    Prompts the user to select a protocol if none is set or the file is missing.
    """
    from erasmus.utils.paths import detect_ide_from_env

    global _last_rules_write_time

    detected_ide = detect_ide_from_env()
    path_manager = get_path_manager(detected_ide)
    template_path = path_manager.template_dir / "meta_rules.xml"
    rules_file_path = path_manager.get_rules_file()
    if not template_path.exists():
        # No template available: fallback to raw merge of ctx files
        logger.warning(
            f"Template file not found: {template_path}; falling back to raw merge"
        )
        try:
            architecture_text = path_manager.get_architecture_file().read_text()
            progress_text = path_manager.get_progress_file().read_text()
            tasks_text = path_manager.get_tasks_file().read_text()
            merged_content = "\n".join([architecture_text, progress_text, tasks_text])
            if not rules_file_path:
                logger.warning("No rules file configured; skipping local merge")
            else:
                rules_file_path.write_text(merged_content)
                _last_rules_write_time = rules_file_path.stat().st_mtime
                logger.info(f"Updated local rules file (fallback): {rules_file_path}")
        except Exception as exception:
            logger.error(f"Error during fallback merge: {exception}")
        return
    try:
        # Always start from a fresh template
        template_content = template_path.read_text()
        architecture = (
            path_manager.get_architecture_file().read_text()
            if path_manager.get_architecture_file().exists()
            else ""
        )
        progress = (
            path_manager.get_progress_file().read_text()
            if path_manager.get_progress_file().exists()
            else ""
        )
        tasks = (
            path_manager.get_tasks_file().read_text()
            if path_manager.get_tasks_file().exists()
            else ""
        )
        merged_content = template_content
        merged_content = re.sub(
            r"<!--ARCHITECTURE-->[\s\S]*?<!--/ARCHITECTURE-->",
            architecture,
            merged_content,
        )
        merged_content = re.sub(
            r"<!--PROGRESS-->[\s\S]*?<!--/PROGRESS-->", progress, merged_content
        )
        merged_content = re.sub(
            r"<!--TASKS-->[\s\S]*?<!--/TASKS-->", tasks, merged_content
        )
        # Get protocol value from the current_protocol.txt file, or prompt if missing/invalid
        protocol_value = ""
        current_protocol_path = Path(path_manager.erasmus_dir) / "current_protocol.txt"
        protocol_manager = ProtocolManager()
        protocol_name = None
        if current_protocol_path.exists():
            protocol_name = current_protocol_path.read_text().strip()
        protocol_file = None
        if protocol_name:
            # Ensure protocol_name does not have .xml extension already
            if protocol_name.endswith(".xml"):
                protocol_file = path_manager.protocol_dir / protocol_name
            else:
                protocol_file = path_manager.protocol_dir / f"{protocol_name}.xml"
            print(f"[DEBUG] Loaded protocol name: '{protocol_name}'")
            print(f"[DEBUG] Checking protocol file: {protocol_file}")
            # Fallback to template protocols if not found in user protocol dir
            if not protocol_file.exists():
                template_protocol_file = (
                    path_manager.template_dir / "protocols" / f"{protocol_name}.xml"
                )
                print(
                    f"[DEBUG] Checking template protocol file: {template_protocol_file}"
                )
                if template_protocol_file.exists():
                    protocol_file = template_protocol_file
        if not protocol_name or not protocol_file or not protocol_file.exists():
            # Try to extract protocol from the existing rules file using XML parsing
            if rules_file_path and rules_file_path.exists():
                try:
                    tree = ET.parse(rules_file_path)
                    root = tree.getroot()
                    # Try to find <Protocol> block
                    protocol_elem = root.find(".//Protocol")
                    if protocol_elem is not None:
                        protocol_value = ET.tostring(protocol_elem, encoding="unicode")
                        print("[DEBUG] Extracted protocol from existing rules file.")
                except Exception as e:
                    print(f"[DEBUG] Failed to extract protocol from rules file: {e}")
            if not protocol_value:
                # Prompt user to select a protocol
                protocols = protocol_manager.list_protocols()
                if not protocols:
                    logger.error("No protocols found. Cannot update rules file.")
                    return
                print("Available protocols:")
                for idx, pname in enumerate(protocols):
                    print(f"  {idx + 1}. {pname}")
                while True:
                    choice = input("Select a protocol by number or name: ").strip()
                    selected = None
                    if choice.isdigit():
                        idx = int(choice)
                        if 1 <= idx <= len(protocols):
                            selected = protocols[idx - 1]
                    elif choice in protocols:
                        selected = choice
                    if selected:
                        protocol_name = selected.strip()
                        current_protocol_path.write_text(protocol_name)
                        protocol_file = (
                            path_manager.protocol_dir / f"{protocol_name}.xml"
                        )
                        print(f"[DEBUG] User selected protocol: '{protocol_name}'")
                        print(f"[DEBUG] Checking protocol file: {protocol_file}")
                        # Fallback to template protocols if not found in user protocol dir
                        if not protocol_file.exists():
                            template_protocol_file = (
                                path_manager.template_dir
                                / "protocols"
                                / f"{protocol_name}.xml"
                            )
                            print(
                                f"[DEBUG] Checking template protocol file: {template_protocol_file}"
                            )
                            if template_protocol_file.exists():
                                protocol_file = template_protocol_file
                        if protocol_file.exists():
                            protocol_value = protocol_file.read_text()
                        else:
                            print(f"Protocol file not found: {protocol_file}")
                            continue
                        break
                    print(f"Invalid selection: {choice}")
        else:
            if protocol_file and protocol_file.exists():
                protocol_value = protocol_file.read_text()
        merged_content = re.sub(
            r"<!--PROTOCOL-->[\s\S]*?<!--/PROTOCOL-->", protocol_value, merged_content
        )
        # Overwrite the rules file with the merged content
        if not rules_file_path:
            logger.warning("No rules file configured; skipping local merge")
        else:
            rules_file_path.write_text(merged_content)
            _last_rules_write_time = rules_file_path.stat().st_mtime
            logger.info(f"Updated local rules file: {rules_file_path}")
    except Exception as exception:
        logger.error(f"Error merging rules file: {exception}")


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

    def on_modified(self, file_event: FileSystemEvent) -> None:
        """
        Handle file modification events.
        Args:
            file_event: The file system event
        """
        if file_event.is_directory:
            return

        current_time = time.time()
        file_path = file_event.src_path

        # Ignore changes to rules files (e.g., .codex.md, .cursorrules, .windsurfrules, CLAUDE.md)
        if file_path.endswith(
            (".codex.md", ".cursorrules", ".windsurfrules", "CLAUDE.md")
        ):
            return

        # Check if this is a duplicate event within debounce time
        if file_path in self.last_processed:
            if current_time - self.last_processed[file_path] < self.debounce_time:
                return

        self.processed_events.add(file_path)
        self.last_processed[file_path] = current_time
        logger.info(f"File modified: {file_path}")
        # Only trigger on .ctx.*.xml files
        if (
            file_path.endswith(".ctx.architecture.xml")
            or file_path.endswith(".ctx.progress.xml")
            or file_path.endswith(".ctx.tasks.xml")
        ):
            try:
                _merge_rules_file()
            except Exception as merge_error:
                logger.error(f"Failed to update rules file: {merge_error}")


class FileMonitor:
    """
    Monitors a path for file changes.
    """

    def __init__(self, watch_path: str | Path) -> None:
        """
        Initialize the file monitor.
        Args:
            watch_path: Path to monitor for changes
        Raises:
            FileNotFoundError: If watch_path does not exist
        """
        if isinstance(watch_path, str):
            watch_path = Path(watch_path)
        if not watch_path.exists():
            raise FileNotFoundError(f"Watch path does not exist: {watch_path}")

        self.watch_path: str = watch_path
        self.event_handler: FileEventHandler = FileEventHandler()
        self.observer: Optional[ObserverType] = None
        self._is_running: bool = False

    def _matches_rules_file(self, file_path: str) -> bool:
        """
        Check if a path matches rules file patterns.
        Args:
            file_path: Path to check
        Returns:
            bool: True if path matches rules file patterns
        """
        return file_path.endswith((".windsurfrules", ".cursorrules"))

    def start(self) -> None:
        """
        Start monitoring the watch path.
        """
        if self._is_running:
            logger.warning("Monitor is already running")
            return

        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.watch_path, recursive=False)
        self.observer.start()
        self._is_running = True
        logger.info(f"Started monitoring: {self.watch_path}")

    def stop(self) -> None:
        """
        Stop monitoring the watch path.
        """
        if not self._is_running:
            logger.warning("Monitor is not running")
            return

        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self._is_running = False
            logger.info(f"Stopped monitoring: {self.watch_path}")

    def __enter__(self) -> "FileMonitor":
        """
        Context manager entry.
        Returns:
            FileMonitor: The monitor instance
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Context manager exit.
        """
        self.stop()
