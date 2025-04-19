
# __init__.py
"""
Erasmus - Development Context Management System
"""

from erasmus.cli import cli
from erasmus.context import ContextManager, ContextError
from erasmus.protocol import ProtocolManager, ProtocolError
from erasmus.utils import get_path_manager

__version__ = "0.1.0"
__all__ = [
    "cli",
    "ContextManager",
    "ContextError",
    "ProtocolManager",
    "ProtocolError",
    "get_path_manager",
]


# protocol.py
"""
Protocol management functionality for Erasmus.
"""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from loguru import logger
from erasmus.utils.paths import get_path_manager
from erasmus.utils.sanatizer import _sanitize_string, _sanitize_xml_content

path_manager = get_path_manager()


class ProtocolError(Exception):
    """Exception raised for protocol-related errors."""

    pass


class ProtocolModel(BaseModel):
    """
    Represents a protocol, including its name, path, and content.
    """

    name: str
    path: str
    content: str


class ProtocolManager:
    """
    Manages protocol files for Erasmus.
    Loads base protocol templates from erasmus.erasmus/templates/protocols and custom user protocols from erasmus.erasmus/protocol.
    Provides methods to list, get, create, update, and delete protocols.
    """

    def __init__(self, base_dir: Optional[str] = None, user_dir: Optional[str] = None) -> None:
        # Always use path_manager.template_dir / 'protocols' unless base_dir is explicitly provided
        self.base_template_dir: Path = (
            Path(base_dir) if base_dir is not None else path_manager.template_dir / "protocols"
        )
        self.user_protocol_dir: Path = Path(user_dir) if user_dir else path_manager.protocol_dir
        self.base_template_dir.mkdir(parents=True, exist_ok=True)
        self.user_protocol_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"Initialized ProtocolManager with base template dir: {self.base_template_dir} and user protocol dir: {self.user_protocol_dir}"
        )

    def _sanitize_name(self, protocol_name: str) -> str:
        """Sanitize a protocol name for filesystem use."""
        return _sanitize_string(protocol_name)

    def _get_protocol_path(self, protocol_name: str, is_template: bool = False) -> Path:
        """
        Get the path for a protocol file.
        Args:
            protocol_name: The protocol name
            is_template: If True, look in the template directory; else, user directory
        Returns:
            Path to the protocol file
        """
        sanitized_name = self._sanitize_name(protocol_name)
        directory = self.base_template_dir if is_template else self.user_protocol_dir
        return directory / f"{sanitized_name}.xml"

    def list_protocols(
        self, include_templates: bool = True, include_user: bool = True
    ) -> list[str]:
        """
        List all available protocol names.
        Args:
            include_templates: Include base templates
            include_user: Include user protocols
        Returns:
            List of protocol names
        """
        protocol_names = set()
        if include_templates:
            protocol_names.update(
                [protocol_path.stem for protocol_path in self.base_template_dir.glob("*.xml")]
            )
        if include_user:
            protocol_names.update(
                [protocol_path.stem for protocol_path in self.user_protocol_dir.glob("*.xml")]
            )
        return sorted(protocol_names)

    def get_protocol(self, protocol_name: str) -> Optional[ProtocolModel]:
        """
        Get a protocol by name, searching user protocols first, then templates.
        Args:
            protocol_name: The protocol name
        Returns:
            ProtocolModel if found, else None
        """
        sanitized_name = self._sanitize_name(protocol_name)
        user_path = self._get_protocol_path(sanitized_name, is_template=False)
        template_path = self._get_protocol_path(sanitized_name, is_template=True)
        if user_path.exists():
            content = user_path.read_text()
            return ProtocolModel(name=sanitized_name, path=str(user_path), content=content)
        elif template_path.exists():
            content = template_path.read_text()
            return ProtocolModel(name=sanitized_name, path=str(template_path), content=content)
        else:
            return None

    def create_protocol(self, protocol_name: str, content: str) -> ProtocolModel:
        """
        Create a new user protocol.
        Args:
            protocol_name: The protocol name
            content: The protocol content
        Returns:
            The created ProtocolModel
        Raises:
            FileExistsError: If a user protocol with the same name already exists
        """
        sanitized_name = self._sanitize_name(protocol_name)
        protocol_path = self._get_protocol_path(sanitized_name, is_template=False)
        if protocol_path.exists():
            raise FileExistsError(f"Protocol '{sanitized_name}' already exists.")
        # Use template if content is not provided or empty
        if not isinstance(content, str) or not content.strip():
            template_path = path_manager.template_dir / "protocol.xml"
            if template_path.exists():
                content = template_path.read_text()
            else:
                content = '<?xml version="1.0" encoding="UTF-8"?>\n<Protocol></Protocol>'
        else:
            # If content is not valid XML, wrap it in <Protocol>...</Protocol>
            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(content)
            except Exception:
                content = f'<?xml version="1.0" encoding="UTF-8"?>\n<Protocol>{content}</Protocol>'
        protocol_path.write_text(_sanitize_xml_content(content))
        logger.info(f"Created protocol: {sanitized_name}")
        return ProtocolModel(name=sanitized_name, path=str(protocol_path), content=content)

    def update_protocol(self, protocol_name: str, content: str) -> ProtocolModel:
        """
        Update an existing user protocol.
        Args:
            protocol_name: The protocol name
            content: The new protocol content
        Returns:
            The updated ProtocolModel
        Raises:
            FileNotFoundError: If the protocol does not exist in user protocols
        """
        sanitized_name = self._sanitize_name(protocol_name)
        protocol_path = self._get_protocol_path(sanitized_name, is_template=False)
        if not protocol_path.exists():
            raise FileNotFoundError(f"Protocol '{sanitized_name}' not found in user protocols.")
        # Ensure content is a valid XML string
        if not isinstance(content, str) or not content.strip():
            content = '<?xml version="1.0" encoding="UTF-8"?>\n<Protocol></Protocol>'
        else:
            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(content)
            except Exception:
                content = f'<?xml version="1.0" encoding="UTF-8"?>\n<Protocol>{content}</Protocol>'
        protocol_path.write_text(_sanitize_xml_content(content))
        logger.info(f"Updated protocol: {sanitized_name}")
        return ProtocolModel(name=sanitized_name, path=str(protocol_path), content=content)

    def delete_protocol(self, protocol_name: str) -> None:
        """
        Delete a user protocol.
        Args:
            protocol_name: The protocol name
        Raises:
            FileNotFoundError: If the protocol does not exist in user protocols
            PermissionError: If attempting to delete a template protocol
        """
        sanitized_name = self._sanitize_name(protocol_name)
        protocol_path = self._get_protocol_path(sanitized_name, is_template=False)
        template_path = self._get_protocol_path(sanitized_name, is_template=True)
        # Prevent deletion if protocol is a template
        if template_path.exists():
            raise PermissionError(
                f"Cannot delete template protocol: '{sanitized_name}'. Only custom (user) protocols can be deleted."
            )
        if not protocol_path.exists():
            raise FileNotFoundError(f"Protocol '{sanitized_name}' not found in user protocols.")
        protocol_path.unlink()
        logger.info(f"Deleted protocol: {sanitized_name}")

ProtocolError = ProtocolError
ProtocolModel = ProtocolModel

# file_monitor.py
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

FileEventHandler = FileEventHandler

# environment.py
"""Environment configuration management."""

import re
import os
from pathlib import Path
from typing_extensions import Callable
from pydantic import BaseModel, ConfigDict
from getpass import getpass
from erasmus.utils.logging import timeit


class EnvironmentError(Exception):
    """Base exception for environment configuration errors."""

    pass


def is_sensitive_variable(name: str) -> bool:
    """
    Check if a variable name contains common sensitive terms.

    Args:
        name: The variable name to check

    Returns:
        True if the variable is likely sensitive, False otherwise
    """
    sensitive_terms = [
        "key",
        "token",
        "secret",
        "password",
        "credential",
        "auth",
        "api_key",
        "access_token",
        "private",
        "ssh",
        "certificate",
    ]

    name_lower = name.lower()
    return any(term in name_lower for term in sensitive_terms)


def mask_sensitive_value(value: str) -> str:
    """
    Mask a sensitive value for display.

    Args:
        value: The value to mask

    Returns:
        Masked value (first 2 chars + 3 stars)
    """
    if not value or len(value) <= 2:
        return "***"
    return value[:2] + "***"


class VariableDefinition(BaseModel):
    """Definition of an environment variable."""

    name: str
    type: type
    required: bool = True
    default: any = None
    validator: Callable[[any], bool] | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def is_sensitive(self) -> bool:
        """Check if this variable is sensitive."""
        return is_sensitive_variable(self.name)


class EnvironmentConfig(BaseModel):
    """Manages environment configuration with validation."""

    definitions: dict[str, VariableDefinition] = {}
    _variables: dict[str, any] = {}

    def list_variables(self):
        for name, definition in self._definitions.items():
            if definition.is_sensitive:
                print(f"{name}: ****")
            else:
                print(f"{name}: {self._variables[name]}")

    def define_required(self, name: str, type_: type, **kwargs) -> None:
        """Define a required environment variable."""
        self._definitions[name] = VariableDefinition(name=name, type=type_, required=True, **kwargs)

    def define_optional(self, name: str, type_: type, **kwargs) -> None:
        """Define an optional environment variable."""
        self._definitions[name] = VariableDefinition(
            name=name, type=type_, required=False, **kwargs
        )

    def set(self, name: str, value: str) -> None:
        """Set an environment variable value."""
        if name not in self._definitions:
            raise EnvironmentError(f"Variable {name} not defined")

        definition = self._definitions[name]
        try:
            # Convert value to the specified type
            converted_value = definition.type(value)

            # Apply validation
            if definition.min_value is not None and converted_value < definition.min_value:
                raise EnvironmentError(
                    f"{name} must be greater than or equal to {definition.min_value}"
                )

            if definition.max_value is not None and converted_value > definition.max_value:
                raise EnvironmentError(
                    f"{name} must be less than or equal to {definition.max_value}"
                )

            if definition.pattern is not None and isinstance(converted_value, str):
                if not re.match(definition.pattern, converted_value):
                    raise EnvironmentError(f"{name} must match pattern {definition.pattern}")

            if definition.validator is not None and not definition.validator(converted_value):
                raise EnvironmentError(f"{name} failed custom validation")

            self._variables[name] = converted_value

        except (ValueError, TypeError) as e:
            raise EnvironmentError(f"Invalid value for {name}: {str(e)}")

    def get(self, name: str, default: any = None) -> any:
        """
        Get an environment variable value.

        Args:
            name: The variable name
            default: Default value if not found

        Returns:
            The variable value or default
        """
        if name not in self._variables:
            return default
        return self._variables[name]

    def get_masked(self, name: str) -> str:
        """
        Get a masked representation of a variable value.

        Args:
            name: The variable name

        Returns:
            Masked value if sensitive, actual value otherwise
        """
        if name not in self._variables:
            return ""

        value = self._variables[name]
        definition = self._definitions[name]

        if definition.is_sensitive and isinstance(value, str):
            return mask_sensitive_value(value)
        return str(value)

    @timeit
    def load_from_file(self, file_path: str | Path) -> None:
        """Load environment variables from a file."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise EnvironmentError(f"Environment file not found: {file_path}")

        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        name, value = line.split("=", 1)
                        name = name.strip()
                        value = value.strip()
                        self.set(name, value)
                    except ValueError:
                        continue

    @timeit
    def load_from_system(self) -> None:
        """Load environment variables from system environment."""
        for name, definition in self._definitions.items():
            if name in os.environ:
                self.set(name, os.environ[name])

    def prompt_for_missing(self) -> None:
        """Prompt for missing required variables."""
        for name, definition in self._definitions.items():
            if definition.required and name not in self._variables:
                if definition.is_sensitive:
                    value = getpass(f"Enter {name}: ")
                else:
                    value = input(f"Enter {name}: ")
                self.set(name, value)

    @timeit
    def validate(self) -> None:
        """Validate all environment variables according to their definitions."""
        for variable_key, variable_definition in self._definitions.items():
            variable_value = self._variables.get(variable_key)
            if variable_definition.required and variable_value is None:
                raise EnvironmentError(f"Missing required environment variable: {variable_key}")
            if variable_value is not None:
                if not isinstance(variable_value, variable_definition.type):
                    raise TypeError(
                        f"Environment variable '{variable_key}' should be of type {variable_definition.type.__name__}"
                    )
                if variable_definition.validator and not variable_definition.validator(
                    variable_value
                ):
                    raise ValueError(
                        f"Environment variable '{variable_key}' failed custom validation."
                    )

    @timeit
    def merge(self, other: "EnvironmentConfig") -> None:
        """Merge another environment configuration into this one."""
        # First merge definitions
        for name, definition in other._definitions.items():
            if name not in self._definitions:
                self._definitions[name] = definition

        # Then merge values
        for name, value in other._variables.items():
            self.set(name, str(value))

EnvironmentError = EnvironmentError
is_sensitive_variable = is_sensitive_variable
mask_sensitive_value = mask_sensitive_value
VariableDefinition = VariableDefinition
EnvironmentConfig = EnvironmentConfig

# __main__.py
"""
Main entry point for the Erasmus CLI.
"""

from erasmus.cli import cli


def main() -> None:
    """Main function for the Erasmus CLI."""
    cli()


if __name__ == "__main__":
    main()

main = main

# context.py
"""
Context Manager for handling development context files.

This module provides functionality for managing context files in the .erasmus/context
directory, including saving, loading, and sanitizing content.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from pydantic import BaseModel
from loguru import logger
from erasmus.utils.paths import get_path_manager
from erasmus.utils.sanatizer import _sanitize_string, _sanitize_xml_content
from erasmus.utils.rich_console import get_console
from typing import Optional

console = get_console()


class ContextError(Exception):
    """Exception raised for context-related errors."""

    pass


class ContextFileError(ContextError):
    """Exception raised for file operation errors."""

    pass


class ContextValidationError(ContextError):
    """Exception raised for content validation errors."""

    pass


path_manager = get_path_manager()


class CtxModel(BaseModel):
    """
    Represents a development context, including all relevant file contents and paths.
    """

    path: str
    architecture: str
    progress: str
    tasks: str
    protocol: str = ""


class CtxMngrModel(BaseModel):
    """
    Model for managing a collection of CtxModel instances and the context directory path.
    """

    contexts: list[CtxModel] = []
    # Base directory for contexts (alias for context_dir)
    context_dir: Path = path_manager.get_context_dir()
    base_dir: Path = path_manager.get_context_dir()
    context: CtxModel | None = None
    architecture_path: str | Path = path_manager.get_architecture_file()
    progress_path: str | Path = path_manager.get_progress_file()
    tasks_path: str | Path = path_manager.get_tasks_file()
    architecture_content: str = ""
    progress_content: str = ""
    tasks_content: str = ""
    protocol_content: str = ""


class ContextManager(CtxMngrModel):
    """
    Manages development context files in the .erasmus/context directory.
    Uses CtxModel as the in-memory storage for context data.
    Handles context selection, loading, saving, and file operations for architecture, progress, and tasks only.
    Protocol handling is managed by erasmus/protocol.py.
    """

    def __init__(self, base_dir: Optional[str] = None, base_path: Optional[str] = None) -> None:
        """
        Initialize the context manager.

        Args:
            base_dir: Base directory for contexts. Defaults to path_manager.get_context_dir().
            base_path: Alias for base_dir (for compatibility).
        """
        # Initialize BaseModel internals
        super().__init__()
        # Determine base directory parameter (base_path overrides base_dir)
        chosen_dir = base_path if base_path is not None else base_dir
        # Set base directory for contexts
        self.base_dir: Path = Path(chosen_dir) if chosen_dir else path_manager.get_context_dir()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized ContextManager with base path: {self.base_dir}")
        self.context: Optional[CtxModel] = None
        self.architecture_path: Path = path_manager.get_architecture_file()
        self.progress_path: Path = path_manager.get_progress_file()
        self.tasks_path: Path = path_manager.get_tasks_file()
        self.architecture_content: Optional[str] = None
        self.progress_content: Optional[str] = None
        self.tasks_content: Optional[str] = None
        # Initialization complete

    def create_context(
        self,
        context_name: str,
        architecture_content: str = None,
        progress_content: str = None,
        tasks_content: str = None,
    ) -> None:
        """Create a new development context using XML templates for architecture, progress, and tasks. Optionally accept user content for each file."""
        sanitized_name = self._sanitize_name(context_name)
        context_dir = path_manager.get_context_dir() / sanitized_name
        if context_dir.exists():
            raise ContextError(f"Context already exists: {context_name}")
        # Create context directory
        context_dir.mkdir(parents=True, exist_ok=False)
        # Use the correct template directory from the path manager
        template_dir = path_manager.template_dir
        template_map = {
            "ctx.architecture.xml": (
                template_dir / "architecture.xml",
                architecture_content,
                "Architecture",
            ),
            "ctx.progress.xml": (
                template_dir / "progress.xml",
                progress_content,
                "Progress",
            ),
            "ctx.tasks.xml": (template_dir / "tasks.xml", tasks_content, "Tasks"),
        }
        for target_name, (
            template_path,
            user_content,
            root_tag,
        ) in template_map.items():
            content = None
            if user_content is not None and user_content.strip():
                try:
                    ET.fromstring(user_content)
                    content = user_content
                except Exception:
                    content = f'<?xml version="1.0" encoding="UTF-8"?>\n<{root_tag}>{user_content}</{root_tag}>'
            elif template_path.exists():
                content = template_path.read_text()
            else:
                content = f'<?xml version="1.0" encoding="UTF-8"?>\n<{root_tag}></{root_tag}>'
            (context_dir / target_name).write_text(content)

    def get_context(self, context_name: str) -> CtxModel:
        """Get a context model by name."""
        return self.get_context_model(context_name)

    @property
    def base_path(self) -> Path:
        """Alias for base_dir: get the base directory path for contexts."""
        return self.base_dir

    def save_context_file(self, context_name: str, filename: str, content: str) -> None:
        """Save raw content to a file in the specified context."""
        context_dir = self.get_context_path(context_name)
        context_dir.mkdir(parents=True, exist_ok=True)
        file_path = context_dir / filename
        file_path.write_text(content)

    def load_context_file(self, context_name: str, filename: str) -> str:
        """Load content from a file in the specified context, returning sanitized text."""
        context_dir = self.get_context_path(context_name)
        file_path = context_dir / filename
        if not file_path.exists():
            return ""
        raw = file_path.read_text()
        return self._sanitize_content(raw)

    def list_context_files(self, context_name: str) -> list[str]:
        """List all file names in the specified context directory."""
        context_dir = self.get_context_path(context_name)
        if not context_dir.exists():
            return []
        return [
            context_file.name for context_file in context_dir.iterdir() if context_file.is_file()
        ]

    def delete_context_file(self, context_name: str, filename: str) -> None:
        """Delete a file in the specified context directory."""
        context_dir = self.get_context_path(context_name)
        file_path = context_dir / filename
        if file_path.exists():
            file_path.unlink()

    def update_architecture(self, context_name: str, content: str) -> None:
        """Update the architecture file content for a context."""
        self.save_context_file(context_name, "ctx.architecture.xml", content)

    def update_progress(self, context_name: str, content: str) -> None:
        """Update the progress file content for a context."""
        self.save_context_file(context_name, "ctx.progress.xml", content)

    def update_tasks(self, context_name: str, content: str) -> None:
        """Update the tasks file content for a context."""
        self.save_context_file(context_name, "ctx.tasks.xml", content)
        # End of initialization

    def _sanitize_name(self, context_name: str) -> str:
        """
        Sanitize a context name for filesystem use.
        Args:
            context_name: The context name to sanitize.
        Returns:
            The sanitized name.
        """
        return _sanitize_string(context_name)

    def _get_context_dir(self, context_name: str) -> Path:
        """
        Get the directory for a context.
        Args:
            context_name: The context name.
        Returns:
            The context directory path.
        """
        return self.base_dir / self._sanitize_name(context_name)

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename to be ASCII-only and safe for filesystem operations.
        Args:
            filename: The filename to sanitize
        Returns:
            Sanitized filename
        """
        return _sanitize_string(filename)

    def _sanitize_content(self, content: str) -> str:
        """
        Sanitize XML content to be ASCII-only and well-formed.
        Args:
            content: The content to sanitize
        Returns:
            Sanitized content
        """
        return _sanitize_xml_content(content)

    def get_context_path(self, context_name: str) -> Path:
        """
        Get the path for a context's directory.
        Args:
            context_name: Name of the context
        Returns:
            Path to the context directory
        """
        sanitized_name = self._sanitize_filename(context_name)
        return self.base_dir / sanitized_name

    def get_context_dir_path(self, context_name: str) -> Optional[Path]:
        """
        Get the directory path for a context if it exists.
        Args:
            context_name: Name of the context
        Returns:
            Path to the context directory, or None if it doesn't exist
        """
        try:
            context_dir = self._get_context_dir(context_name)
            return context_dir if context_dir.exists() else None
        except Exception as context_error:
            raise ContextFileError(f"Failed to get context path: {context_error}")

    def save_contexts(self) -> list[CtxModel]:
        """
        Save all contexts by loading them from disk into CtxModel instances.
        Returns:
            List of saved CtxModel instances
        """
        context_models: list[CtxModel] = []
        for context_directory in self.base_dir.iterdir():
            if context_directory.is_dir():
                context_name = context_directory.name
                try:
                    context_path = self.get_context_dir_path(context_name)
                    if context_path:
                        context_models.append(self.get_context_model(context_name))
                except Exception as context_error:
                    logger.error(f"Failed to save context {context_name}: {context_error}")
        return context_models

    def delete_context(self, context_name: str) -> None:
        """
        Delete a context and all its files.
        Args:
            context_name: Name of the context to delete
        Raises:
            ContextFileError: If deletion fails
        """
        try:
            context_dir = self._get_context_dir(context_name)
            if not context_dir.exists():
                raise ContextFileError(f"Context does not exist: {context_name}")
            for file_path in context_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()
            context_dir.rmdir()
            logger.info(f"Deleted context: {context_name}")
        except Exception as context_error:
            raise ContextFileError(f"Failed to delete context: {context_error}")

    def display_context(self, context_name: str) -> None:
        """
        Display a context's information, including file sizes and paths.
        Args:
            context_name: Name of the context to display
        Raises:
            ContextFileError: If context doesn't exist
        """
        try:
            context_dir = self.get_context_dir_path(context_name)
            if not context_dir:
                raise ContextFileError(f"Context does not exist: {context_name}")
            print(f"Context: {context_name}")
            print(f"Path: {context_dir}")
            print(
                f"Architecture: {len(self.read_file(context_name, 'architecture')) if self.read_file(context_name, 'architecture') else 'N/A'}"
            )
            print(
                f"Progress: {len(self.read_file(context_name, 'progress')) if self.read_file(context_name, 'progress') else 'N/A'}"
            )
            print(
                f"Tasks: {len(self.read_file(context_name, 'tasks')) if self.read_file(context_name, 'tasks') else 'N/A'}"
            )
            print(
                f"Protocol: {len(self.read_file(context_name, 'protocol')) if self.read_file(context_name, 'protocol') else 'N/A'}"
            )
        except Exception as context_error:
            raise ContextFileError(f"Failed to display context: {context_error}")

    def list_contexts(self) -> list[str]:
        """
        List all development contexts by name.
        Returns:
            A list of context names.
        Raises:
            ContextFileError: If contexts cannot be listed.
        """
        try:
            return [
                context_directory.name
                for context_directory in self.base_dir.iterdir()
                if context_directory.is_dir()
            ]
        except Exception as context_error:
            raise ContextFileError(f"Failed to list contexts: {context_error}")

    def select_context(self) -> CtxModel:
        """
        Interactively select a context, loading it into memory and saving the current context if needed.
        Returns:
            The selected CtxModel instance
        Raises:
            ContextFileError: If no contexts exist
        """
        context_models = self.save_contexts()
        if not context_models:
            raise ContextFileError("No contexts exist")
        print("Available contexts:")
        for context_index, context_model in enumerate(context_models):
            print(f"{context_index + 1}. {context_model.path}")
        while True:
            try:
                user_choice = int(input("Select a context (number): "))
                if 1 <= user_choice <= len(context_models):
                    selected_context = context_models[user_choice - 1]
                    # Write current in-memory context to files before switching
                    if self.context:
                        self._write_context_to_files()
                    self.context = selected_context
                    self._load_context_to_memory(selected_context)
                    return selected_context
                print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")

    def _write_context_to_files(self) -> None:
        """
        Write the in-memory context content to the working files.
        """
        if self.context:
            if self.architecture_content is not None:
                self.architecture_path.write_text(self.architecture_content)
            if self.progress_content is not None:
                self.progress_path.write_text(self.progress_content)
            if self.tasks_content is not None:
                self.tasks_path.write_text(self.tasks_content)
            if self.protocol_content is not None:
                self.protocol_path.write_text(self.protocol_content)

    def _load_context_to_memory(self, context_model: CtxModel) -> None:
        """
        Load the content of a CtxModel into the in-memory fields.
        Args:
            context_model: The CtxModel to load
        """
        self.architecture_content = context_model.architecture
        self.progress_content = context_model.progress
        self.tasks_content = context_model.tasks

    def update_architecture(self, context_name: str, architecture_content: str) -> CtxModel:
        """
        Update a context's architecture file and in-memory content.
        Args:
            context_name: Name of the context
            architecture_content: New architecture content
        Returns:
            Updated CtxModel instance
        Raises:
            ContextFileError: If update fails
        """
        try:
            self.update_file(context_name, "architecture", architecture_content)
            if self.context and self.context.path.endswith(context_name):
                self.architecture_content = architecture_content
            return self.get_context_model(context_name)
        except Exception as error:
            raise ContextFileError(f"Failed to update architecture: {error}")

    def update_progress(self, context_name: str, progress_content: str) -> CtxModel:
        """
        Update a context's progress file and in-memory content.
        Args:
            context_name: Name of the context
            progress_content: New progress content
        Returns:
            Updated CtxModel instance
        Raises:
            ContextFileError: If update fails
        """
        try:
            self.update_file(context_name, "progress", progress_content)
            if self.context and self.context.path.endswith(context_name):
                self.progress_content = progress_content
            return self.get_context_model(context_name)
        except Exception as error:
            raise ContextFileError(f"Failed to update progress: {error}")

    def update_tasks(self, context_name: str, tasks_content: str) -> CtxModel:
        """
        Update a context's tasks file and in-memory content.
        Args:
            context_name: Name of the context
            tasks_content: New tasks content
        Returns:
            Updated CtxModel instance
        Raises:
            ContextFileError: If update fails
        """
        try:
            self.update_file(context_name, "tasks", tasks_content)
            if self.context and self.context.path.endswith(context_name):
                self.tasks_content = tasks_content
            return self.get_context_model(context_name)
        except Exception as error:
            raise ContextFileError(f"Failed to update tasks: {error}")

    def update_file(self, context_name: str, file_type: str, content: str) -> None:
        """
        Update a file in a development context.
        Args:
            context_name: The name of the context.
            file_type: The type of file to update (architecture, progress, tasks, protocol).
            content: The content to write to the file.
        Raises:
            ContextError: If the file cannot be updated.
        """
        context_dir = self.get_context_dir_path(context_name)
        if not context_dir:
            raise ContextError(f"Context does not exist: {context_name}")
        file_path = context_dir / f"ctx.{file_type}.xml"
        try:
            file_path.write_text(content)
        except Exception as error:
            raise ContextError(f"Failed to update file: {error}")

    def read_file(self, context_name: str, file_type: str) -> Optional[str]:
        """
        Read a file from a development context.
        Args:
            context_name: The name of the context.
            file_type: The type of file to read (architecture, progress, tasks, protocol).
        Returns:
            The file content, or None if the file does not exist.
        Raises:
            ContextError: If the file cannot be read.
        """
        context_dir = self.get_context_dir_path(context_name)
        if not context_dir:
            raise ContextError(f"Context does not exist: {context_name}")
        file_path = context_dir / f"ctx.{file_type}.xml"
        try:
            return file_path.read_text() if file_path.exists() else None
        except Exception as error:
            raise ContextError(f"Failed to read file: {error}")

    def edit_file(self, context_name: str, file_type: str, editor: Optional[str] = None) -> None:
        """
        Edit a file in a development context using the specified editor.
        Args:
            context_name: The name of the context.
            file_type: The type of file to edit (architecture, progress, tasks, protocol).
            editor: The editor to use. If None, the default editor is used.
        Raises:
            ContextError: If the file cannot be edited.
        """
        context_dir = self.get_context_dir_path(context_name)
        if not context_dir:
            raise ContextError(f"Context does not exist: {context_name}")
        file_path = context_dir / f"ctx.{file_type}.xml"
        if not file_path.exists():
            raise ContextError(f"File does not exist: {file_type}")
        try:
            editor_cmd = editor or os.environ.get("EDITOR", "nano")
            os.system(f"{editor_cmd} {file_path}")
        except Exception as error:
            raise ContextError(f"Failed to edit file: {error}")

    def store_context(self) -> str:
        """
        Store the current context by reading the architecture, progress, and tasks files into memory,
        then writing those values to the context directory files and updating the in-memory CtxModel.
        Returns:
            The name of the stored context
        Raises:
            ContextError: If storing the context fails
        """
        try:
            self.architecture_content = (
                self.architecture_path.read_text() if self.architecture_path.exists() else ""
            )
            self.progress_content = (
                self.progress_path.read_text() if self.progress_path.exists() else ""
            )
            self.tasks_content = self.tasks_path.read_text() if self.tasks_path.exists() else ""
            tree = ET.ElementTree(ET.fromstring(self.architecture_content))
            root = tree.getroot()
            title_elem = root.find(".//Title")
            if title_elem is None or not title_elem.text:
                raise ContextError("Title not found in architecture file")
            title = title_elem.text
            context_name = self._sanitize_name(title)
            context_dir = self._get_context_dir(context_name)
            context_dir.mkdir(parents=True, exist_ok=True)
            (context_dir / "ctx.architecture.xml").write_text(self.architecture_content)
            (context_dir / "ctx.progress.xml").write_text(self.progress_content)
            (context_dir / "ctx.tasks.xml").write_text(self.tasks_content)
            self.context = CtxModel(
                path=str(context_dir),
                architecture=self.architecture_content,
                progress=self.progress_content,
                tasks=self.tasks_content,
            )
            return context_name
        except Exception as error:
            raise ContextError(f"Failed to store context: {error}")

    def load_context(self, context_name: str) -> None:
        """
        Load a stored context by copying its XML files to the root-level .ctx.* XML files.

        Args:
            context_name: Name of the context to load

        Raises:
            ContextError: If the context does not exist or loading fails
        """
        # Locate the context directory
        context_dir = self._get_context_dir(context_name)
        if not context_dir.exists():
            raise ContextError(f"Context does not exist: {context_name}")
        # Copy each context file (XML only) to root-level .ctx files
        try:
            for file_type in ("architecture", "progress", "tasks"):
                src = context_dir / f"ctx.{file_type}.xml"
                if src.exists():
                    dst = getattr(self, f"{file_type}_path")
                    dst.write_text(src.read_text())
                else:
                    logger.warning(
                        f"No {file_type} file found for context '{context_name}' (expected ctx.{file_type}.xml)"
                    )
        except Exception as error:
            raise ContextError(f"Failed to load context '{context_name}': {error}")
        # After loading context files, update IDE rules and global rules
        try:
            from erasmus.file_monitor import _merge_rules_file

            _merge_rules_file()
        except Exception as merge_error:
            logger.error(
                f"Failed to update rules file after loading context '{context_name}': {merge_error}"
            )

    def get_context_model(self, context_name: str) -> CtxModel:
        """
        Get a CtxModel instance by context name.
        Args:
            context_name: Name of the context
        Returns:
            CtxModel instance
        Raises:
            ContextFileError: If context doesn't exist
        """
        try:
            context_dir = self._get_context_dir(context_name)
            if not context_dir.exists():
                raise ContextFileError(f"Context does not exist: {context_name}")
            architecture = self.read_file(context_name, "architecture") or ""
            progress = self.read_file(context_name, "progress") or ""
            tasks = self.read_file(context_name, "tasks") or ""
            return CtxModel(
                path=str(context_dir),
                architecture=architecture,
                progress=progress,
                tasks=tasks,
            )
        except Exception as context_error:
            raise ContextFileError(f"Failed to get context: {context_error}")

    def _sanitize_string(self, filename: str) -> str:
        """
        Sanitize a filename to be ASCII-only and safe for filesystem operations.

        Args:
            filename: The filename to sanitize

        Returns:
            Sanitized filename
        """
        return _sanitize_string(filename)

    def _sanitize_xml(self, content: str) -> str:
        """
        Sanitize XML content to be ASCII-only and safe for filesystem operations.
        """
        return _sanitize_xml_content(content)

ContextError = ContextError
ContextFileError = ContextFileError
ContextValidationError = ContextValidationError
CtxModel = CtxModel
CtxMngrModel = CtxMngrModel
ContextManager = ContextManager

# setup_commands.py
import typer
from pathlib import Path
from erasmus.utils.paths import get_path_manager
from erasmus.protocol import ProtocolManager
from erasmus.context import ContextManager
from erasmus.utils.rich_console import print_table

app = typer.Typer(help="Setup Erasmus: initialize project, environment, and context.")


@app.callback(invoke_without_command=True)
def setup_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is not None:
        return
    """Interactive setup for Erasmus: configure IDE, project, context, and protocol."""
    # Step 1: Use path manager for IDE detection and prompting
    path_manager = get_path_manager()
    print_table(["Info"], [[f"IDE detected: {path_manager.ide.name}"]], title="Setup")

    # Step 2: Prompt for project name
    project_name = typer.prompt("Enter the project name")
    if not project_name:
        print_table(["Error"], [["Project name is required."]], title="Setup Failed")
        raise typer.Exit(1)

    # Step 3: Create project directory and context using path manager
    project_dir = Path.cwd() / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    print_table(["Info"], [[f"Project directory created: {project_dir}"]], title="Setup")

    # Step 4: Use path manager for all Erasmus folders inside project
    erasmus_dir = path_manager.erasmus_dir
    context_dir = path_manager.context_dir
    protocol_dir = path_manager.protocol_dir
    template_dir = path_manager.template_dir
    for d in [erasmus_dir, context_dir, protocol_dir, template_dir]:
        d.mkdir(parents=True, exist_ok=True)
    print_table(["Info"], [[f"Erasmus folders created in: {erasmus_dir}"]], title="Setup")

    # Step 5: Create a template context in the context folder and update root .ctx.*.xml files
    context_manager = ContextManager(base_dir=str(context_dir))
    context_manager.create_context(project_name)
    print_table(["Info"], [[f"Template context created: {project_name}"]], title="Setup")
    # Load the new context to root .ctx.*.xml files
    context_manager.load_context(project_name)
    print_table(
        ["Info"],
        [[f"Root .ctx.*.xml files updated for: {project_name}"]],
        title="Setup",
    )

    # Step 6: Prompt for protocol selection
    protocol_manager = ProtocolManager()
    protocols = protocol_manager.list_protocols()
    if not protocols:
        print_table(["Error"], [["No protocols found."]], title="Setup Failed")
        raise typer.Exit(1)
    protocol_rows = [[str(i + 1), p] for i, p in enumerate(protocols)]
    print_table(["#", "Protocol Name"], protocol_rows, title="Available Protocols")
    while True:
        choice = typer.prompt("Select a protocol by number or name")
        selected = None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(protocols):
                selected = protocols[idx - 1]
        elif choice in protocols:
            selected = choice
        if selected:
            # Write the selected protocol to current_protocol.txt using path manager
            current_protocol_path = path_manager.erasmus_dir / "current_protocol.txt"
            current_protocol_path.write_text(selected)
            print_table(["Info"], [[f"Protocol set to: {selected}"]], title="Setup")
            # Immediately update the rules file to reflect the selected protocol
            try:
                from erasmus.file_monitor import _merge_rules_file

                _merge_rules_file()
                print_table(
                    ["Info"],
                    [[f"Rules file updated with protocol: {selected}"]],
                    title="Setup",
                )
            except Exception as e:
                print_table(
                    ["Error"],
                    [[f"Failed to update rules file: {e}"]],
                    title="Setup Warning",
                )
            break
        print(f"Invalid selection: {choice}")

    print_table(["Info"], [["Erasmus setup complete."]], title="Setup Success")
    raise typer.Exit(0)

setup_callback = setup_callback

# context_commands.py
"""
CLI commands for managing development contexts.
"""

import typer
from loguru import logger
from erasmus.context import ContextManager, ContextError
import xml.dom.minidom as minidom
from erasmus.utils.rich_console import print_table
import os

context_manager = ContextManager()
app = typer.Typer(help="Manage development contexts and their files.")


@app.command("get")
def get_context(name: str = typer.Argument(..., help="Name of the context to get")):
    """Get detailed information of a development context."""
    try:
        # Use display_context to print full details
        context_manager.display_context(name)
    except ContextError as e:
        # Extract underlying error if prefixed by display_context
        error_msg = str(e)
        prefix = "Failed to display context: "
        if error_msg.startswith(prefix):
            error_msg = error_msg[len(prefix) :]
        typer.echo(f"Error: Failed to get context: {error_msg}")
        raise typer.Exit(1)
    # Successful display
    raise typer.Exit(0)


def show_help_and_exit():
    """Show help menu and exit with error code."""
    command_rows = [
        ["erasmus context list", "List all contexts"],
        ["erasmus context create", "Create a new context"],
        ["erasmus context show", "Show context details"],
        ["erasmus context update", "Update context files"],
        ["erasmus context edit", "Edit context files"],
        ["erasmus context store", "Store the current context"],
        ["erasmus context select", "Select and load a context interactively"],
        ["erasmus context load", "Load a context by name to root .ctx XML files"],
    ]
    print_table(["Command", "Description"], command_rows, title="Available Commands")
    typer.echo("\nFor more information about a command, run:")
    typer.echo("  erasmus context <command> --help")
    raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def context_callback(ctx: typer.Context):
    """
    Manage development contexts and their files.
    """
    if ctx.invoked_subcommand is None:
        command_rows = [
            ["erasmus context list", "List all contexts"],
            ["erasmus context create", "Create a new context"],
            ["erasmus context show", "Show context details"],
            ["erasmus context update", "Update context files"],
            ["erasmus context edit", "Edit context files"],
            ["erasmus context store", "Store the current context"],
            ["erasmus context select", "Select and load a context interactively"],
            ["erasmus context load", "Load a context by name to root .ctx XML files"],
        ]
        print_table(["Command", "Description"], command_rows, title="Available Commands")
        typer.echo("\nFor more information about a command, run:")
        typer.echo("  erasmus context <command> --help")
        raise typer.Exit(0)


@app.command()
def create(name: str = typer.Argument(None, help="Name of the context to create")):
    """Create a new development context and display its path."""
    try:
        if not name:
            name = typer.prompt("Enter the context name")
        if not name:
            print_table(
                ["Error"],
                [["Context name is required."]],
                title="Context Creation Failed",
            )
            raise typer.Exit(1)
        context_manager.create_context(name)
        # Retrieve created context model for path
        context = context_manager.get_context(name)
        # Display created context in a table
        context_rows = [[context.path]]
        print_table(["Context Path"], context_rows, title=f"Created Context: {name}")
        raise typer.Exit(0)
    except ContextError as error:
        print_table(["Error"], [[str(error)]], title="Context Creation Failed")
        raise typer.Exit(1)


@app.command()
def delete(name: str = typer.Argument(None, help="Name of the context to delete")):
    """Delete a context.

    This command permanently removes a context folder and its files.
    Use with caution as this action cannot be undone.
    """
    try:
        if not name:
            contexts = context_manager.list_contexts()
            if not contexts:
                print_table(["Info"], [["No contexts found"]], title="Available Contexts")
                raise typer.Exit(1)
            context_rows = [
                [str(index + 1), context_name] for index, context_name in enumerate(contexts)
            ]
            print_table(["#", "Context Name"], context_rows, title="Available Contexts")
            choice = typer.prompt("Select a context by number or name")
            selected = None
            if choice.isdigit():
                index = int(choice)
                if 1 <= index <= len(contexts):
                    selected = contexts[index - 1]
            else:
                if choice in contexts:
                    selected = choice
            if not selected:
                print_table(
                    ["Error"],
                    [[f"Invalid selection: {choice}"]],
                    title="Context Deletion Failed",
                )
                raise typer.Exit(1)
            name = selected
        context_manager.delete_context(name)
        print_table(["Info"], [[f"Deleted context: {name}"]], title="Context Deleted")
        raise typer.Exit(0)
    except Exception as e:
        print_table(["Error"], [[str(e)]], title="Context Deletion Failed")
        raise typer.Exit(1)


@app.command()
def list():
    """List all development contexts.

    This command shows all available contexts and their basic information.
    Use 'show' to view detailed information about a specific context.
    """
    try:
        contexts = context_manager.list_contexts()
        if not contexts:
            print_table(["Info"], [["No contexts found"]], title="Available Contexts")
            return

        # Display contexts in a table
        context_rows = [[context] for context in contexts]
        print_table(["Context Name"], context_rows, title="Available Contexts")
    except ContextError as error:
        print_table(["Error"], [[str(error)]], title="Context Listing Failed")
        show_help_and_exit()


def preview(text, lines=10):
    if not text:
        return ""
    split = text.splitlines()
    if len(split) > lines:
        return "\n".join(split[:lines]) + "\n..."
    return text


@app.command()
def show(name: str = typer.Argument(None, help="Name of the context to show")):
    """Show details of a development context.

    This command displays detailed information about a specific context,
    including file sizes and paths. If no name is supplied, it will prompt the user to select one.
    """
    try:
        if not name:
            # List available contexts and prompt for selection
            contexts = context_manager.list_contexts()
            if not contexts:
                print_table(["Info"], [["No contexts found"]], title="Available Contexts")
                raise typer.Exit(1)
            context_rows = [
                [str(index + 1), context_name] for index, context_name in enumerate(contexts)
            ]
            print_table(["#", "Context Name"], context_rows, title="Available Contexts")
            choice = typer.prompt("Select a context by number or name")
            selected = None
            if choice.isdigit():
                index = int(choice)
                if 1 <= index <= len(contexts):
                    selected = contexts[index - 1]
            else:
                if choice in contexts:
                    selected = choice
            if not selected:
                print_table(
                    ["Error"],
                    [[f"Invalid selection: {choice}"]],
                    title="Context Show Failed",
                )
                raise typer.Exit(1)
            name = selected
        context_dir = context_manager.get_context_path(name)

        def read_context_file(context_dir, file_type):
            for ext in (".xml", ".md"):
                file_path = context_dir / f"ctx.{file_type}{ext}"
                if file_path.exists():
                    return file_path.read_text()
            return ""

        context_rows = [
            ["Path", str(context_dir)],
            ["Architecture", preview(read_context_file(context_dir, "architecture"))],
            ["Progress", preview(read_context_file(context_dir, "progress"))],
            ["Tasks", preview(read_context_file(context_dir, "tasks"))],
            ["Protocol", preview(read_context_file(context_dir, "protocol"))],
        ]
        print_table(
            ["Field", "Preview (first 10 lines)"],
            context_rows,
            title=f"Context: {name}",
        )
    except ContextError as error:
        print_table(["Error"], [[str(error)]], title="Context Show Failed")
        show_help_and_exit()


@app.command()
def update(
    name: str = typer.Argument(None, help="Name of the context to update"),
    file_type: str = typer.Argument(
        None, help="Type of file to update (architecture, progress, tasks, protocol)"
    ),
    content: str = typer.Argument(None, help="Content to write to the file"),
):
    """Update a file in a development context.

    This command updates the content of a specific file in a context.
    The file type must be one of: architecture, progress, tasks, or protocol.
    """
    try:
        if not name:
            # List available contexts and prompt for selection
            contexts = context_manager.list_contexts()
            if not contexts:
                print_table(["Info"], [["No contexts found"]], title="Available Contexts")
                raise typer.Exit(1)
            context_rows = [
                [str(index + 1), context_name] for index, context_name in enumerate(contexts)
            ]
            print_table(["#", "Context Name"], context_rows, title="Available Contexts")
            choice = typer.prompt("Select a context by number or name")
            selected = None
            if choice.isdigit():
                index = int(choice)
                if 1 <= index <= len(contexts):
                    selected = contexts[index - 1]
            else:
                if choice in contexts:
                    selected = choice
            if not selected:
                print_table(
                    ["Error"],
                    [[f"Invalid selection: {choice}"]],
                    title="Context Update Failed",
                )
                raise typer.Exit(1)
            name = selected
        if not file_type:
            file_type = typer.prompt(
                "Enter the file type to update (architecture, progress, tasks, protocol)"
            )
        if not file_type:
            print_table(
                ["Error"],
                [["File type is required for update."]],
                title="Context Update Failed",
            )
            raise typer.Exit(1)
        if content is None:
            content = typer.prompt(f"Enter the new content for {file_type}")
        if not content:
            print_table(
                ["Error"],
                [["Content is required for update."]],
                title="Context Update Failed",
            )
            raise typer.Exit(1)
        context_manager.update_file(name, file_type, content)
        print_table(
            ["Info"],
            [[f"Updated {file_type} in context: {name}"]],
            title="Context Updated",
        )
        raise typer.Exit(0)
    except ContextError as error:
        print_table(["Error"], [[str(error)]], title="Context Update Failed")
        show_help_and_exit()


@app.command()
def cat(
    name: str = typer.Argument(..., help="Name of the context"),
    file_type: str = typer.Argument(
        ..., help="Type of file to read (architecture, progress, tasks, protocol)"
    ),
):
    """Display the contents of a file in a development context.

    This command shows the raw contents of a specific file in a context.
    The file type must be one of: architecture, progress, tasks, or protocol.
    """
    try:
        content = context_manager.read_file(name, file_type)
        if content is None:
            print_table(
                ["Error"],
                [[f"File not found: {file_type}"]],
                title="Context Cat Failed",
            )
            logger.info("Available file types: architecture, progress, tasks, protocol")
            show_help_and_exit()

        # Pretty print XML for better readability
        try:
            # Parse the XML content
            dom = minidom.parseString(content)
            # Pretty print with indentation
            pretty_xml = dom.toprettyxml(indent="  ")
            print(pretty_xml)
        except Exception:
            # If XML parsing fails, print the raw content
            print(content)
    except ContextError as error:
        print_table(["Error"], [[str(error)]], title="Context Cat Failed")
        show_help_and_exit()


@app.command()
def edit(
    name: str = typer.Argument(None, help="Name of the context"),
    file_type: str = typer.Argument(
        None, help="Type of file to edit (architecture, progress, tasks, protocol)"
    ),
    editor: str = typer.Argument(None, help="Editor to use for editing"),
):
    """Edit a file in a development context.

    This command opens a file in your default editor (or specified editor).
    The file type must be one of: architecture, progress, tasks, or protocol.
    """
    if not name:
        # List available contexts and prompt for selection
        contexts = context_manager.list_contexts()
        if not contexts:
            print_table(["Info"], [["No contexts found"]], title="Available Contexts")
            raise typer.Exit(1)
        context_rows = [
            [str(index + 1), context_name] for index, context_name in enumerate(contexts)
        ]
        print_table(["#", "Context Name"], context_rows, title="Available Contexts")
        choice = typer.prompt("Select a context by number or name")
        selected = None
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(contexts):
                selected = contexts[index - 1]
        else:
            if choice in contexts:
                selected = choice
        if not selected:
            print_table(
                ["Error"],
                [[f"Invalid selection: {choice}"]],
                title="Context Edit Failed",
            )
            raise typer.Exit(1)
        name = selected
    if not file_type:
        file_type = typer.prompt(
            "Enter the file type to edit (architecture, progress, tasks, protocol)"
        )
    if not file_type:
        print_table(
            ["Error"],
            [["File type is required for edit."]],
            title="Context Edit Failed",
        )
        raise typer.Exit(1)
    context_dir = context_manager.get_context_path(name)
    file_path = None
    for ext in (".xml", ".md"):
        candidate = context_dir / f"ctx.{file_type}{ext}"
        if candidate.exists():
            file_path = candidate
            break
    if not file_path:
        print_table(
            ["Error"],
            [[f"File does not exist: {file_type}"]],
            title="Context Edit Failed",
        )
        raise typer.Exit(1)
    editor_cmd = editor or os.environ.get("EDITOR", "nano")
    os.system(f"{editor_cmd} {file_path}")
    print_table(
        ["Info"],
        [[f"Edited {file_type} in context: {name}"]],
        title="Context Edited",
    )
    raise typer.Exit(0)


@app.command()
def store():
    """Store the current context by reading the architecture file, parsing the title,
    sanitizing it, and saving the current context files to a new folder.

    This command will:
    1. Read the current architecture file
    2. Extract the title from it
    3. Create a new context folder with the sanitized title
    4. Copy the current architecture, progress, and tasks files to the new folder
    """
    try:
        context_name = context_manager.store_context()
        print_table(
            ["Info"],
            [[f"Successfully stored context as: {context_name}"]],
            title="Context Stored",
        )
        raise typer.Exit(0)
    except ContextError as error:
        print_table(["Error"], [[str(error)]], title="Context Store Failed")
        show_help_and_exit()


@app.command("load")
def load_context(name: str = typer.Argument(None, help="Name of the context to load")):
    """Load a stored context by name into the root .ctx XML files.

    If no name is supplied, you will be prompted to select one interactively.
    """
    try:
        if not name:
            # List available contexts and prompt for selection
            contexts = context_manager.list_contexts()
            if not contexts:
                print_table(["Info"], [["No contexts found"]], title="Available Contexts")
                raise typer.Exit(1)
            context_rows = [
                [str(index + 1), context_name] for index, context_name in enumerate(contexts)
            ]
            print_table(["#", "Context Name"], context_rows, title="Available Contexts")
            choice = typer.prompt("Select a context by number or name")
            selected = None
            if choice.isdigit():
                index = int(choice)
                if 1 <= index <= len(contexts):
                    selected = contexts[index - 1]
            else:
                if choice in contexts:
                    selected = choice
            if not selected:
                print_table(
                    ["Error"],
                    [[f"Invalid selection: {choice}"]],
                    title="Context Load Failed",
                )
                raise typer.Exit(1)
            name = selected
        context_manager.load_context(name)
        print_table(["Info"], [[f"Loaded context: {name}"]], title="Context Loaded")
        raise typer.Exit(0)
    except ContextError as error:
        print_table(["Error"], [[str(error)]], title="Context Load Failed")
        raise typer.Exit(1)


@app.command("select")
def select_context():
    """Interactively select a context and load its XML files."""
    base_dir = context_manager.base_path
    # Gather available contexts
    try:
        contexts = sorted(
            [
                context_directory.name
                for context_directory in base_dir.iterdir()
                if context_directory.is_dir()
            ]
        )
    except Exception as exception:
        typer.echo(f"Error: Unable to list contexts: {exception}")
        raise typer.Exit(1)
    if not contexts:
        typer.echo("No contexts found to select.")
        raise typer.Exit(1)
    # Display contexts in a table
    context_rows = [[str(index + 1), context_name] for index, context_name in enumerate(contexts)]
    print_table(["#", "Context Name"], context_rows, title="Available Contexts")
    choice = typer.prompt("Select a context by number or name")
    # Determine selected context name
    selected = None
    if choice.isdigit():
        index = int(choice)
        if 1 <= index <= len(contexts):
            selected = contexts[index - 1]
    else:
        if choice in contexts:
            selected = choice
    if not selected:
        typer.echo(f"Error: Invalid selection: {choice}")
        raise typer.Exit(1)
    # Load the selected context
    try:
        context_manager.load_context(selected)
        typer.echo(f"Loaded context: {selected}")
        raise typer.Exit(0)
    except ContextError as exception:
        typer.echo(f"Error: Failed to load context: {exception}")
        raise typer.Exit(1)

get_context = get_context
show_help_and_exit = show_help_and_exit
context_callback = context_callback
create = create
delete = delete
list = list
preview = preview
show = show
update = update
cat = cat
edit = edit
store = store
load_context = load_context
select_context = select_context

# protocol_commands.py
"""
CLI commands for managing protocols.
"""

import typer
from pathlib import Path
from loguru import logger
from erasmus.protocol import ProtocolManager, ProtocolError
from erasmus.utils.rich_console import print_table
import os
import re

protocol_manager = ProtocolManager()
app = typer.Typer(help="Manage development protocols.")


def show_help_and_exit():
    """Show help menu and exit with error code."""
    command_rows = [
        ["erasmus protocol list", "List all protocols"],
        ["erasmus protocol create", "Create a new protocol"],
        ["erasmus protocol show", "Show protocol details"],
        ["erasmus protocol update", "Update a protocol"],
        ["erasmus protocol edit", "Edit a protocol"],
        ["erasmus protocol delete", "Delete a protocol"],
        ["erasmus protocol select", "Select and display a protocol"],
        ["erasmus protocol load", "Load a protocol as active"],
    ]
    print_table(
        ["Command", "Description"], command_rows, title="Available Protocol Commands"
    )
    typer.echo("\nFor more information about a command, run:")
    typer.echo("  erasmus protocol <command> --help")
    raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def protocol_callback(ctx: typer.Context):
    """
    Manage development protocols.
    """
    if ctx.invoked_subcommand is None:
        command_rows = [
            ["erasmus protocol list", "List all protocols"],
            ["erasmus protocol create", "Create a new protocol"],
            ["erasmus protocol show", "Show protocol details"],
            ["erasmus protocol update", "Update a protocol"],
            ["erasmus protocol edit", "Edit a protocol"],
            ["erasmus protocol delete", "Delete a protocol"],
            ["erasmus protocol select", "Select and display a protocol"],
            ["erasmus protocol load", "Load a protocol as active"],
        ]
        print_table(
            ["Command", "Description"],
            command_rows,
            title="Available Protocol Commands",
        )
        typer.echo("\nFor more information about a command, run:")
        typer.echo("  erasmus protocol <command> --help")
        raise typer.Exit(0)


@app.command()
def create(
    name: str = typer.Argument(None, help="Name of the protocol to create"),
    content: str = typer.Argument(None, help="Content of the protocol"),
):
    """Create a new protocol.

    This command creates a new protocol file with optional content.
    The protocol name will be sanitized to ensure it's safe for filesystem operations.
    """
    try:
        if not name:
            name = typer.prompt("Enter the protocol name")
        if not name:
            print_table(
                ["Error"],
                [["Protocol name is required."]],
                title="Protocol Creation Failed",
            )
            raise typer.Exit(1)
        if content is None:
            content = typer.prompt(
                "Enter the protocol content (leave blank to use template)"
            )
        protocol_manager.create_protocol(name, content)
        logger.info(f"Created protocol: {name}")
        print_table(["Info"], [[f"Created protocol: {name}"]], title="Protocol Created")
        raise typer.Exit(0)
    except ProtocolError as e:
        logger.error(f"Failed to create protocol: {e}")
        show_help_and_exit()


@app.command()
def update(
    name: str = typer.Argument(None, help="Name of the protocol to update"),
    content: str = typer.Argument(None, help="New content for the protocol"),
):
    """Update an existing protocol.

    This command updates the content of an existing protocol.
    The protocol must exist before it can be updated.
    """
    try:
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_table(
                    ["Info"], [["No protocols found"]], title="Available Protocols"
                )
                raise typer.Exit(1)
            protocol_rows = [
                [str(index + 1), protocol_name]
                for index, protocol_name in enumerate(protocols)
            ]
            print_table(
                ["#", "Protocol Name"], protocol_rows, title="Available Protocols"
            )
            choice = typer.prompt("Select a protocol by number or name")
            selected = None
            if choice.isdigit():
                index = int(choice)
                if 1 <= index <= len(protocols):
                    selected = protocols[index - 1]
            else:
                if choice in protocols:
                    selected = choice
            if not selected:
                print_table(
                    ["Error"],
                    [[f"Invalid selection: {choice}"]],
                    title="Protocol Update Failed",
                )
                raise typer.Exit(1)
            name = selected
        if content is None:
            content = typer.prompt("Enter the new protocol content")
        if not content:
            print_table(
                ["Error"],
                [["Protocol content is required."]],
                title="Protocol Update Failed",
            )
            raise typer.Exit(1)
        protocol_manager.update_protocol(name, content)
        logger.info(f"Updated protocol: {name}")
        print_table(["Info"], [[f"Updated protocol: {name}"]], title="Protocol Updated")
        raise typer.Exit(0)
    except ProtocolError as e:
        logger.error(f"Failed to update protocol: {e}")
        show_help_and_exit()


@app.command()
def delete(name: str = typer.Argument(None, help="Name of the protocol to delete")):
    """Delete a protocol.

    This command permanently removes a protocol file.
    Use with caution as this action cannot be undone.
    """
    try:
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_table(
                    ["Info"], [["No protocols found"]], title="Available Protocols"
                )
                raise typer.Exit(1)
            protocol_rows = [
                [str(index + 1), protocol_name]
                for index, protocol_name in enumerate(protocols)
            ]
            print_table(
                ["#", "Protocol Name"], protocol_rows, title="Available Protocols"
            )
            choice = typer.prompt("Select a protocol by number or name")
            selected = None
            if choice.isdigit():
                index = int(choice)
                if 1 <= index <= len(protocols):
                    selected = protocols[index - 1]
            else:
                if choice in protocols:
                    selected = choice
            if not selected:
                print_table(
                    ["Error"],
                    [[f"Invalid selection: {choice}"]],
                    title="Protocol Deletion Failed",
                )
                raise typer.Exit(1)
            name = selected
        protocol_manager.delete_protocol(name)
        logger.info(f"Deleted protocol: {name}")
        print_table(["Info"], [[f"Deleted protocol: {name}"]], title="Protocol Deleted")
        raise typer.Exit(0)
    except (ProtocolError, PermissionError, FileNotFoundError) as e:
        print_table(["Error"], [[str(e)]], title="Protocol Deletion Failed")
        raise typer.Exit(1)


@app.command()
def list():
    """List all protocols.

    This command shows all available protocols and their basic information.
    Use 'show' to view detailed information about a specific protocol.
    """
    try:
        protocols = protocol_manager.list_protocols()
        if not protocols:
            typer.echo("No protocols found")
            return

        # Display protocols in a table
        protocol_rows = [[protocol] for protocol in protocols]
        print_table(["Protocol Name"], protocol_rows, title="Available Protocols")
    except ProtocolError as e:
        logger.error(f"Failed to list protocols: {e}")
        show_help_and_exit()


@app.command()
def show(name: str = typer.Argument(None, help="Name of the protocol to show")):
    """Show details of a protocol.

    This command displays detailed information about a specific protocol,
    including its content and metadata.
    """
    try:
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_table(
                    ["Info"], [["No protocols found"]], title="Available Protocols"
                )
                raise typer.Exit(1)
            protocol_rows = [
                [str(index + 1), protocol_name]
                for index, protocol_name in enumerate(protocols)
            ]
            print_table(
                ["#", "Protocol Name"], protocol_rows, title="Available Protocols"
            )
            choice = typer.prompt("Select a protocol by number or name")
            selected = None
            if choice.isdigit():
                index = int(choice)
                if 1 <= index <= len(protocols):
                    selected = protocols[index - 1]
            else:
                if choice in protocols:
                    selected = choice
            if not selected:
                print_table(
                    ["Error"],
                    [[f"Invalid selection: {choice}"]],
                    title="Protocol Show Failed",
                )
                raise typer.Exit(1)
            name = selected
        protocol = protocol_manager.get_protocol(name)
        if not protocol:
            print_table(
                ["Error"],
                [[f"Protocol not found: {name}"]],
                title="Protocol Show Failed",
            )
            raise typer.Exit(1)
        print_table(["Info"], [[f"Protocol: {name}"]], title="Protocol Details")
        typer.echo(f"Path: {protocol.path}")
        typer.echo(f"Content:\n{protocol.content}")
        raise typer.Exit(0)
    except ProtocolError as e:
        print_table(["Error"], [[str(e)]], title="Protocol Show Failed")
        raise typer.Exit(1)


@app.command("select")
def select_protocol():
    """Interactively select a protocol, display its details, and update the rules file with it."""
    try:
        protocols = protocol_manager.list_protocols()
        if not protocols:
            print_table(["Info"], [["No protocols found"]], title="Available Protocols")
            raise typer.Exit(1)
        protocol_rows = [
            [str(index + 1), protocol_name]
            for index, protocol_name in enumerate(protocols)
        ]
        print_table(["#", "Protocol Name"], protocol_rows, title="Available Protocols")
        choice = typer.prompt("Select a protocol by number or name")
        selected = None
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(protocols):
                selected = protocols[index - 1]
        else:
            if choice in protocols:
                selected = choice
        if not selected:
            print_table(
                ["Error"],
                [[f"Invalid selection: {choice}"]],
                title="Protocol Select Failed",
            )
            raise typer.Exit(1)
        protocol = protocol_manager.get_protocol(selected)
        if not protocol:
            print_table(
                ["Error"],
                [[f"Protocol not found: {selected}"]],
                title="Protocol Select Failed",
            )
            raise typer.Exit(1)
        print_table(
            ["Info"], [[f"Selected protocol: {selected}"]], title="Protocol Selected"
        )
        typer.echo(f"Path: {protocol.path}")
        typer.echo(f"Content:\n{protocol.content}")
        # Write the selected protocol name to .erasmus/current_protocol.txt
        from erasmus.utils.paths import get_path_manager

        path_manager = get_path_manager()
        current_protocol_path = Path(path_manager.erasmus_dir) / "current_protocol.txt"
        current_protocol_path.write_text(selected)
        # Also update the rules file as in load
        template_path = path_manager.template_dir / "meta_rules.xml"
        if not template_path.exists():
            print_table(
                ["Error"],
                [["meta_rules.xml template not found."]],
                title="Protocol Select Failed",
            )
            raise typer.Exit(1)
        meta_rules_content = template_path.read_text()
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
        meta_rules_content = meta_rules_content.replace(
            "<!--ARCHITECTURE-->\n  <!--/ARCHITECTURE-->", architecture
        )
        meta_rules_content = meta_rules_content.replace(
            "<!--PROGRESS-->\n  <!--/PROGRESS-->", progress
        )
        meta_rules_content = meta_rules_content.replace(
            "<!--TASKS-->\n  <!--/TASKS-->", tasks
        )
        meta_rules_content = meta_rules_content.replace(
            "<!--PROTOCOL-->\n  <!--/PROTOCOL-->", protocol.content
        )
        rules_file = path_manager.get_rules_file()
        if not rules_file:
            print_table(
                ["Error"],
                [["No rules file configured."]],
                title="Protocol Select Failed",
            )
            raise typer.Exit(1)
        rules_file.write_text(meta_rules_content)
        print_table(
            ["Info"],
            [[f"Updated rules file with protocol: {selected}"]],
            title="Rules File Updated",
        )
        raise typer.Exit(0)
    except ProtocolError as exception:
        print_table(["Error"], [[str(exception)]], title="Protocol Select Failed")
        raise typer.Exit(1)


@app.command("load")
def load_protocol(
    name: str = typer.Argument(None, help="Name of the protocol to load"),
):
    """Interactively select and load a protocol, merging it into the rules file with current context."""
    try:
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_table(
                    ["Info"], [["No protocols found"]], title="Available Protocols"
                )
                raise typer.Exit(1)
            protocol_rows = [
                [str(index + 1), protocol_name]
                for index, protocol_name in enumerate(protocols)
            ]
            print_table(
                ["#", "Protocol Name"], protocol_rows, title="Available Protocols"
            )
            choice = typer.prompt("Select a protocol by number or name")
            selected = None
            if choice.isdigit():
                index = int(choice)
                if 1 <= index <= len(protocols):
                    selected = protocols[index - 1]
            else:
                if choice in protocols:
                    selected = choice
            if not selected:
                print_table(
                    ["Error"],
                    [[f"Invalid selection: {choice}"]],
                    title="Protocol Load Failed",
                )
                raise typer.Exit(1)
            name = selected
        protocol = protocol_manager.get_protocol(name)
        if not protocol:
            print_table(
                ["Error"],
                [[f"Protocol not found: {name}"]],
                title="Protocol Load Failed",
            )
            raise typer.Exit(1)
        # Write the selected protocol name to .erasmus/current_protocol.txt
        from erasmus.utils.paths import get_path_manager

        path_manager = get_path_manager()
        current_protocol_path = Path(path_manager.erasmus_dir) / "current_protocol.txt"
        current_protocol_path.write_text(name)
        # Load meta_rules.xml template
        template_path = path_manager.template_dir / "meta_rules.xml"
        if not template_path.exists():
            print_table(
                ["Error"],
                [["meta_rules.xml template not found."]],
                title="Protocol Load Failed",
            )
            raise typer.Exit(1)
        meta_rules_content = template_path.read_text()
        # Read current context files
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
        # Replace context and protocol blocks using regex for robustness
        meta_rules_content = re.sub(
            r"<!--ARCHITECTURE-->[\s\S]*?<!--/ARCHITECTURE-->",
            architecture,
            meta_rules_content,
        )
        meta_rules_content = re.sub(
            r"<!--PROGRESS-->[\s\S]*?<!--/PROGRESS-->", progress, meta_rules_content
        )
        meta_rules_content = re.sub(
            r"<!--TASKS-->[\s\S]*?<!--/TASKS-->", tasks, meta_rules_content
        )
        meta_rules_content = re.sub(
            r"<!--PROTOCOL-->[\s\S]*?<!--/PROTOCOL-->",
            protocol.content,
            meta_rules_content,
        )
        # Write to rules file
        rules_file = path_manager.get_rules_file()
        if not rules_file:
            print_table(
                ["Error"], [["No rules file configured."]], title="Protocol Load Failed"
            )
            raise typer.Exit(1)
        rules_file.write_text(meta_rules_content)
        print_table(
            ["Info"],
            [[f"Loaded protocol: {name} into rules file"]],
            title="Protocol Loaded",
        )
        raise typer.Exit(0)
    except ProtocolError as exception:
        print_table(["Error"], [[str(exception)]], title="Protocol Load Failed")
        raise typer.Exit(1)


@app.command()
def edit(
    name: str = typer.Argument(None, help="Name of the protocol to edit"),
    editor: str = typer.Argument(None, help="Editor to use for editing"),
):
    """Edit a protocol file in your default editor (or specified editor)."""
    try:
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_table(
                    ["Info"], [["No protocols found"]], title="Available Protocols"
                )
                raise typer.Exit(1)
            protocol_rows = [
                [str(index + 1), protocol_name]
                for index, protocol_name in enumerate(protocols)
            ]
            print_table(
                ["#", "Protocol Name"], protocol_rows, title="Available Protocols"
            )
            choice = typer.prompt("Select a protocol by number or name")
            selected = None
            if choice.isdigit():
                index = int(choice)
                if 1 <= index <= len(protocols):
                    selected = protocols[index - 1]
            else:
                if choice in protocols:
                    selected = choice
            if not selected:
                print_table(
                    ["Error"],
                    [[f"Invalid selection: {choice}"]],
                    title="Protocol Edit Failed",
                )
                raise typer.Exit(1)
            name = selected
        protocol = protocol_manager.get_protocol(name)
        if not protocol:
            print_table(
                ["Error"],
                [[f"Protocol not found: {name}"]],
                title="Protocol Edit Failed",
            )
            raise typer.Exit(1)
        file_path = protocol.path
        editor_cmd = editor or os.environ.get("EDITOR", "nano")
        os.system(f"{editor_cmd} {file_path}")
        print_table(["Info"], [[f"Edited protocol: {name}"]], title="Protocol Edited")
        raise typer.Exit(0)
    except ProtocolError as error:
        print_table(["Error"], [[str(error)]], title="Protocol Edit Failed")
        raise typer.Exit(1)


@app.command("watch")
def watch_protocol():
    """Monitor .ctx.*.xml files for changes and update the rules file with the current protocol. Does NOT monitor the rules file itself."""
    import time
    from erasmus.utils.paths import get_path_manager
    from erasmus.protocol import ProtocolManager
    from erasmus.utils.rich_console import print_table

    path_manager = get_path_manager()
    protocol_manager = ProtocolManager()
    ctx_files = [
        path_manager.get_architecture_file(),
        path_manager.get_progress_file(),
        path_manager.get_tasks_file(),
    ]
    template_path = path_manager.template_dir / "meta_rules.xml"
    rules_file = path_manager.get_rules_file()
    current_protocol_path = Path(path_manager.erasmus_dir) / "current_protocol.txt"

    def get_protocol_name():
        if current_protocol_path.exists():
            return current_protocol_path.read_text().strip()
        protocols = protocol_manager.list_protocols()
        if not protocols:
            print_table(
                ["Error"], [["No protocols found."]], title="Protocol Watch Failed"
            )
            raise typer.Exit(1)
        protocol_rows = [[str(i + 1), p] for i, p in enumerate(protocols)]
        print_table(["#", "Protocol Name"], protocol_rows, title="Available Protocols")
        choice = typer.prompt("Select a protocol by number or name")
        selected = None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(protocols):
                selected = protocols[idx - 1]
        elif choice in protocols:
            selected = choice
        if not selected:
            print_table(
                ["Error"],
                [[f"Invalid selection: {choice}"]],
                title="Protocol Watch Failed",
            )
            raise typer.Exit(1)
        current_protocol_path.write_text(selected)
        return selected

    def merge_and_write():
        if not template_path.exists():
            print_table(
                ["Error"],
                [["meta_rules.xml template not found."]],
                title="Protocol Watch Failed",
            )
            return
        meta_rules_content = template_path.read_text()
        architecture = ctx_files[0].read_text() if ctx_files[0].exists() else ""
        progress = ctx_files[1].read_text() if ctx_files[1].exists() else ""
        tasks = ctx_files[2].read_text() if ctx_files[2].exists() else ""
        meta_rules_content = re.sub(
            r"<!--ARCHITECTURE-->[\s\S]*?<!--/ARCHITECTURE-->",
            architecture,
            meta_rules_content,
        )
        meta_rules_content = re.sub(
            r"<!--PROGRESS-->[\s\S]*?<!--/PROGRESS-->", progress, meta_rules_content
        )
        meta_rules_content = re.sub(
            r"<!--TASKS-->[\s\S]*?<!--/TASKS-->", tasks, meta_rules_content
        )
        protocol_name = get_protocol_name()
        protocol = protocol_manager.get_protocol(protocol_name)
        if not protocol:
            print_table(
                ["Error"],
                [[f"Protocol not found: {protocol_name}"]],
                title="Protocol Watch Failed",
            )
            return
        meta_rules_content = re.sub(
            r"<!--PROTOCOL-->[\s\S]*?<!--/PROTOCOL-->",
            protocol.content,
            meta_rules_content,
        )
        if not rules_file:
            print_table(
                ["Error"],
                [["No rules file configured."]],
                title="Protocol Watch Failed",
            )
            return
        rules_file.write_text(meta_rules_content)
        print_table(
            ["Info"],
            [[f"Rules file updated with protocol: {protocol_name}"]],
            title="Rules File Updated",
        )

    # Track last modification times for only the .ctx.*.xml files
    last_mtimes = [f.stat().st_mtime if f.exists() else 0 for f in ctx_files]
    print_table(
        ["Info"], [["Watching .ctx.*.xml files for changes..."]], title="Protocol Watch"
    )
    try:
        while True:
            changed = False
            for i, f in enumerate(ctx_files):
                if f.exists():
                    mtime = f.stat().st_mtime
                    if mtime != last_mtimes[i]:
                        changed = True
                        last_mtimes[i] = mtime
            if changed:
                merge_and_write()
            time.sleep(1)
    except KeyboardInterrupt:
        print_table(
            ["Info"], [["Stopped watching context files."]], title="Protocol Watch"
        )


if __name__ == "__main__":
    try:
        app()
    except Exception as error:
        print_table(["Error"], [[str(error)]], title="CLI Error")
        raise typer.Exit(1)

show_help_and_exit = show_help_and_exit
protocol_callback = protocol_callback
create = create
update = update
delete = delete
list = list
show = show
select_protocol = select_protocol
load_protocol = load_protocol
edit = edit
watch_protocol = watch_protocol

# mcp_commands.py
"""
MCP CLI commands for managing MCP servers and clients.
"""

import typer
from pathlib import Path
from loguru import logger
from erasmus.mcp.mcp import MCPClient, MCPServer, MCPRegistry, MCPError
from erasmus.utils.rich_console import print_table

mcp_registry = MCPRegistry()
app = typer.Typer(help="Manage MCP servers and clients.")


def show_help_and_exit():
    """Show help menu and exit with error code."""
    command_rows = [
        ["erasmus mcp server start", "Start an MCP server"],
        ["erasmus mcp server stop", "Stop an MCP server"],
        ["erasmus mcp server register", "Register a new MCP server"],
        ["erasmus mcp server unregister", "Unregister an MCP server"],
        ["erasmus mcp server list", "List all registered servers"],
        ["erasmus mcp client connect", "Connect to an MCP server"],
        ["erasmus mcp client disconnect", "Disconnect from an MCP server"],
        ["erasmus mcp client register", "Register a new MCP client"],
        ["erasmus mcp client unregister", "Unregister an MCP client"],
        ["erasmus mcp client list", "List all registered clients"],
    ]
    print_table(
        ["Command", "Description"], command_rows, title="Available MCP Commands"
    )
    typer.echo("\nFor more information about a command, run:")
    typer.echo("  erasmus mcp <command> --help")
    raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def mcp_callback(ctx: typer.Context):
    """
    Manage MCP servers and clients.
    """
    if ctx.invoked_subcommand is None:
        command_rows = [
            ["erasmus mcp server start", "Start an MCP server"],
            ["erasmus mcp server stop", "Stop an MCP server"],
            ["erasmus mcp server register", "Register a new MCP server"],
            ["erasmus mcp server unregister", "Unregister an MCP server"],
            ["erasmus mcp server list", "List all registered servers"],
            ["erasmus mcp client connect", "Connect to an MCP server"],
            ["erasmus mcp client disconnect", "Disconnect from an MCP server"],
            ["erasmus mcp client register", "Register a new MCP client"],
            ["erasmus mcp client unregister", "Unregister an MCP client"],
            ["erasmus mcp client list", "List all registered clients"],
        ]
        print_table(
            ["Command", "Description"], command_rows, title="Available MCP Commands"
        )
        typer.echo("\nFor more information about a command, run:")
        typer.echo("  erasmus mcp <command> --help")
        raise typer.Exit(0)


# Server commands
server_app = typer.Typer(help="Manage MCP servers.")
app.add_typer(server_app, name="server")


@server_app.command()
def start(
    name: str = typer.Argument(None, help="Name of the server to start"),
    host: str = typer.Option("localhost", help="Host to bind the server to"),
    port: int = typer.Option(8080, help="Port to bind the server to"),
):
    """Start an MCP server.

    This command starts an MCP server with the specified name, host, and port.
    If the server is not registered, it will be registered automatically.
    """
    try:
        if not name:
            name = typer.prompt("Enter the server name")
        if not name:
            typer.echo("Error: Server name is required.")
            raise typer.Exit(1)
        # Check if server is registered
        server_info = mcp_registry.get_server(name)
        if not server_info:
            # Register the server
            mcp_registry.register_server(name, host, port)
            logger.info(f"Registered server: {name}")

        # Start the server
        server = MCPServer(host, port)
        server.start()
        logger.info(f"Started server: {name} on {host}:{port}")
        show_help_and_exit()
    except MCPError as e:
        logger.error(f"Failed to start server: {e}")
        show_help_and_exit()


@server_app.command()
def stop(name: str = typer.Argument(None, help="Name of the server to stop")):
    """Stop an MCP server.

    This command stops an MCP server with the specified name.
    """
    try:
        if not name:
            name = typer.prompt("Enter the server name")
        if not name:
            typer.echo("Error: Server name is required.")
            raise typer.Exit(1)
        # Check if server is registered
        server_info = mcp_registry.get_server(name)
        if not server_info:
            raise MCPError(f"Server '{name}' not registered")

        # Stop the server
        server = MCPServer(server_info["host"], server_info["port"])
        server.stop()
        logger.info(f"Stopped server: {name}")
        show_help_and_exit()
    except MCPError as e:
        logger.error(f"Failed to stop server: {e}")
        show_help_and_exit()


@server_app.command()
def register(
    name: str = typer.Argument(None, help="Name of the server to register"),
    host: str = typer.Option("localhost", help="Host the server is running on"),
    port: int = typer.Option(8080, help="Port the server is running on"),
):
    """Register a new MCP server."""
    try:
        if not name:
            name = typer.prompt("Enter the server name")
        if not name:
            typer.echo("Error: Server name is required.")
            raise typer.Exit(1)
        mcp_registry.register_server(name, host, port)
        typer.echo(f"Registered server: {name}")
        raise typer.Exit(0)
    except MCPError as e:
        typer.echo(f"Error: Failed to register server: {e}")
        raise typer.Exit(1)


@server_app.command()
def unregister(
    name: str = typer.Argument(None, help="Name of the server to unregister"),
):
    """Unregister an MCP server."""
    try:
        if not name:
            name = typer.prompt("Enter the server name")
        if not name:
            typer.echo("Error: Server name is required.")
            raise typer.Exit(1)
        mcp_registry.unregister_server(name)
        typer.echo(f"Unregistered server: {name}")
        raise typer.Exit(0)
    except MCPError as e:
        typer.echo(f"Error: Failed to unregister server: {e}")
        raise typer.Exit(1)


@server_app.command()
def list():
    """List all registered MCP servers.

    This command lists all registered MCP servers and their information.
    """
    try:
        servers = mcp_registry.list_servers()
        if not servers:
            typer.echo("No servers registered")
            return

        # Display servers in a table
        server_rows = []
        for server_name in servers:
            server_info = mcp_registry.get_server(server_name)
            server_rows.append([server_name, server_info["host"], server_info["port"]])
        print_table(
            ["Server Name", "Host", "Port"], server_rows, title="Registered MCP Servers"
        )
    except MCPError as e:
        logger.error(f"Failed to list servers: {e}")
        show_help_and_exit()


# Client commands
client_app = typer.Typer(help="Manage MCP clients.")
app.add_typer(client_app, name="client")


@client_app.command()
def connect(
    name: str = typer.Argument(None, help="Name of the client to connect"),
    server_name: str = typer.Argument(None, help="Name of the server to connect to"),
):
    """Connect to an MCP server.

    This command connects a client to an MCP server.
    If the client is not registered, it will be registered automatically.
    """
    try:
        if not name:
            name = typer.prompt("Enter the client name")
        if not name:
            typer.echo("Error: Client name is required.")
            raise typer.Exit(1)
        if not server_name:
            server_name = typer.prompt("Enter the server name to connect to")
        if not server_name:
            typer.echo("Error: Server name is required.")
            raise typer.Exit(1)
        # Check if server is registered
        server_info = mcp_registry.get_server(server_name)
        if not server_info:
            raise MCPError(f"Server '{server_name}' not registered")

        # Check if client is registered
        client_info = mcp_registry.get_client(name)
        if not client_info:
            # Register the client
            mcp_registry.register_client(name, server_name)
            logger.info(f"Registered client: {name}")

        # Connect to the server
        server_url = f"http://{server_info['host']}:{server_info['port']}"
        client = MCPClient(server_url)
        client.connect()
        logger.info(f"Connected client: {name} to server: {server_name}")
        show_help_and_exit()
    except MCPError as e:
        logger.error(f"Failed to connect client: {e}")
        show_help_and_exit()


@client_app.command()
def disconnect(
    name: str = typer.Argument(..., help="Name of the client to disconnect"),
):
    """Disconnect from an MCP server.

    This command disconnects a client from an MCP server.
    """
    try:
        # Check if client is registered
        client_info = mcp_registry.get_client(name)
        if not client_info:
            raise MCPError(f"Client '{name}' not registered")

        # Get server information
        server_name = client_info["server"]
        server_info = mcp_registry.get_server(server_name)
        if not server_info:
            raise MCPError(f"Server '{server_name}' not registered")

        # Disconnect from the server
        server_url = f"http://{server_info['host']}:{server_info['port']}"
        client = MCPClient(server_url)
        client.disconnect()
        logger.info(f"Disconnected client: {name} from server: {server_name}")
        show_help_and_exit()
    except MCPError as e:
        logger.error(f"Failed to disconnect client: {e}")
        show_help_and_exit()


@client_app.command()
def register(
    name: str = typer.Argument(None, help="Name of the client to register"),
    server_name: str = typer.Argument(
        None, help="Name of the server the client is connected to"
    ),
):
    """Register a new MCP client.

    This command registers a new MCP client with the specified name and server.
    """
    try:
        if not name:
            name = typer.prompt("Enter the client name")
        if not name:
            typer.echo("Error: Client name is required.")
            raise typer.Exit(1)
        if not server_name:
            server_name = typer.prompt(
                "Enter the server name the client is connected to"
            )
        if not server_name:
            typer.echo("Error: Server name is required.")
            raise typer.Exit(1)
        mcp_registry.register_client(name, server_name)
        logger.info(f"Registered client: {name} to server: {server_name}")
        show_help_and_exit()
    except MCPError as e:
        logger.error(f"Failed to register client: {e}")
        show_help_and_exit()


@client_app.command()
def unregister(
    name: str = typer.Argument(None, help="Name of the client to unregister"),
):
    """Unregister an MCP client.

    This command unregisters an MCP client with the specified name.
    """
    try:
        if not name:
            name = typer.prompt("Enter the client name")
        if not name:
            typer.echo("Error: Client name is required.")
            raise typer.Exit(1)
        mcp_registry.unregister_client(name)
        logger.info(f"Unregistered client: {name}")
        show_help_and_exit()
    except MCPError as e:
        logger.error(f"Failed to unregister client: {e}")
        show_help_and_exit()


@client_app.command()
def list():
    """List all registered MCP clients.

    This command lists all registered MCP clients and their information.
    """
    try:
        clients = mcp_registry.list_clients()
        if not clients:
            typer.echo("No clients registered")
            return

        # Display clients in a table
        client_rows = []
        for client_name in clients:
            client_info = mcp_registry.get_client(client_name)
            client_rows.append([client_name, client_info["server"]])
        print_table(
            ["Client Name", "Connected Server"],
            client_rows,
            title="Registered MCP Clients",
        )
    except MCPError as e:
        logger.error(f"Failed to list clients: {e}")
        show_help_and_exit()


@app.command("select-server")
def select_server():
    """Interactively select an MCP server and display its details."""
    try:
        servers = mcp_registry.list_servers()
        if not servers:
            typer.echo("No servers found to select.")
            raise typer.Exit(1)
        # Display servers in a table
        server_rows = [
            [str(index + 1), server_name] for index, server_name in enumerate(servers)
        ]
        print_table(["#", "Server Name"], server_rows, title="Registered MCP Servers")
        choice = typer.prompt("Select a server by number or name")
        selected = None
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(servers):
                selected = servers[index - 1]
        else:
            if choice in servers:
                selected = choice
        if not selected:
            typer.echo(f"Error: Invalid selection: {choice}")
            raise typer.Exit(1)
        server_info = mcp_registry.get_server(selected)
        if not server_info:
            typer.echo(f"Error: Server not found: {selected}")
            raise typer.Exit(1)
        typer.echo(f"Selected server: {selected}")
        typer.echo(f"Host: {server_info['host']}")
        typer.echo(f"Port: {server_info['port']}")
        raise typer.Exit(0)
    except MCPError as exception:
        typer.echo(f"Error: Failed to select server: {exception}")
        raise typer.Exit(1)


@app.command("select-client")
def select_client():
    """Interactively select an MCP client and display its details."""
    try:
        clients = mcp_registry.list_clients()
        if not clients:
            typer.echo("No clients found to select.")
            raise typer.Exit(1)
        # Display clients in a table
        client_rows = [
            [str(index + 1), client_name] for index, client_name in enumerate(clients)
        ]
        print_table(["#", "Client Name"], client_rows, title="Registered MCP Clients")
        choice = typer.prompt("Select a client by number or name")
        selected = None
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(clients):
                selected = clients[index - 1]
        else:
            if choice in clients:
                selected = choice
        if not selected:
            typer.echo(f"Error: Invalid selection: {choice}")
            raise typer.Exit(1)
        client_info = mcp_registry.get_client(selected)
        if not client_info:
            typer.echo(f"Error: Client not found: {selected}")
            raise typer.Exit(1)
        typer.echo(f"Selected client: {selected}")
        typer.echo(f"Connected server: {client_info['server']}")
        raise typer.Exit(0)
    except MCPError as exception:
        typer.echo(f"Error: Failed to select client: {exception}")
        raise typer.Exit(1)


if __name__ == "__main__":
    try:
        app()
    except Exception as error:
        print_table(["Error"], [[str(error)]], title="CLI Error")
        raise typer.Exit(1)

show_help_and_exit = show_help_and_exit
mcp_callback = mcp_callback
start = start
stop = stop
register = register
unregister = unregister
list = list
connect = connect
disconnect = disconnect
register = register
unregister = unregister
list = list
select_server = select_server
select_client = select_client

# environment_commands.py
from erasmus.environment import EnvironmentConfig
import typer

app = typer.Typer(name="environment", help="Manage environment variables")


@app.command(name="list")
def list_environment_variables() -> None:
    """List all environment variables."""
    env_config = EnvironmentConfig()


if __name__ == "__main__":
    app()

list_environment_variables = list_environment_variables

# __init__.py
"""
CLI module for Erasmus.
"""

from erasmus.cli.main import app

def cli():
    """Entry point for the CLI."""
    app()

__all__ = ['app', 'cli'] 
cli = cli

# main.py
"""
Main CLI entry point for Erasmus.
"""

import typer
from erasmus.cli.context_commands import app as context_app
from erasmus.cli.protocol_commands import app as protocol_app
from erasmus.cli.setup_commands import app as setup_app
from erasmus.utils.rich_console import print_table

app = typer.Typer(
    help="Erasmus - Development Context Management System\n\nA tool for managing development contexts, protocols, and Model Context Protocol (MCP) interactions.\n\nFor more information, visit: https://github.com/hydra-dynamics/erasmus"
)

# Add sub-commands
app.add_typer(context_app, name="context", help="Manage development contexts")
app.add_typer(protocol_app, name="protocol", help="Manage protocols")
app.add_typer(setup_app, name="setup", help="Setup Erasmus")


# Custom error handler for unknown commands and argument errors
def print_main_help_and_exit():
    typer.echo("\nErasmus - Development Context Management System")
    command_rows = [
        ["erasmus context", "Manage development contexts"],
        ["erasmus protocol", "Manage protocols"],
        ["erasmus setup", "Setup Erasmus"],
    ]
    print_table(["Command", "Description"], command_rows, title="Available Erasmus Commands")
    typer.echo("\nFor more information about a command, run:")
    typer.echo("  erasmus <command> --help")
    raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Erasmus - Development Context Management System
    """
    if ctx.invoked_subcommand is None:
        print_main_help_and_exit()


# Patch Typer's error handling to show help on unknown command
from typer.main import get_command
from typer.core import TyperGroup
from click import UsageError

original_command = get_command(app)


class HelpOnErrorGroup(TyperGroup):
    def main(self, *args, **kwargs):
        try:
            return super().main(*args, **kwargs)
        except UsageError as e:
            typer.echo(str(e))
            print_main_help_and_exit()


app.command_class = HelpOnErrorGroup


@app.command()
def watch():  # pragma: no cover
    """Watch for changes to .ctx files and update the IDE rules file automatically.

    Press Ctrl+C to stop watching.
    """
    import time
    from erasmus.utils.paths import get_path_manager
    from erasmus.file_monitor import FileMonitor

    pm = get_path_manager()
    root = pm.get_root_dir()
    monitor = FileMonitor(str(root))
    monitor.start()
    typer.echo(f"Watching {root} for .ctx file changes (Ctrl+C to stop)...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
        typer.echo("Stopped watching.")


if __name__ == "__main__":
    from click import UsageError

    try:
        app(standalone_mode=False)
    except UsageError as e:
        typer.echo(str(e))
        print_main_help_and_exit()
    except Exception as error:
        print_table(["Error"], [[str(error)]], title="CLI Error")
        raise typer.Exit(1)
    except SystemExit as e:
        if e.code != 2:
            raise

print_main_help_and_exit = print_main_help_and_exit
main = main
HelpOnErrorGroup = HelpOnErrorGroup
watch = watch

# manager.py
"""Git operations management for Erasmus."""

import subprocess
from pathlib import Path
from loguru import logger

# Removed: from erasmus.utils.logging import LogContext, log_execution


class GitManager:
    """Manages Git operations for the project."""

    def __init__(self, repo_path: str | Path):
        """Initialize GitManager with a repository path."""
        logger.info("[init] Initializing GitManager")
        self.repo_path = Path(repo_path).resolve()
        logger.debug(f"Initializing GitManager with path: {self.repo_path}")
        if not self._is_git_repo():
            logger.info(f"No git repository found at {self.repo_path}, initializing new repo")
            self._init_git_repo()
        else:
            logger.debug(f"Found existing git repository at {self.repo_path}")

    def _is_git_repo(self) -> bool:
        """Check if the path is a git repository."""
        logger.info("[is_git_repo] Checking if path is a git repository")
        try:
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )
            logger.debug(f"Confirmed git repository at {self.repo_path}")
            return True
        except subprocess.CalledProcessError:
            logger.debug(f"No git repository found at {self.repo_path}")
            return False

    def _init_git_repo(self) -> None:
        """Initialize a new git repository."""
        logger.info("[init_git_repo] Initializing new git repository")
        try:
            logger.debug(f"Initializing new git repository at {self.repo_path}")
            subprocess.run(
                ["git", "init"],
                cwd=self.repo_path,
                check=True,
            )

            # Configure default user
            logger.debug("Configuring default git user")
            subprocess.run(
                ["git", "config", "user.name", "Context Watcher"],
                cwd=self.repo_path,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "context.watcher@local"],
                cwd=self.repo_path,
                check=True,
            )
            logger.info(f"Successfully initialized git repository at {self.repo_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to initialize git repository: {e}", exc_info=True)
            raise

    def _run_git_command(self, command: list[str]) -> tuple[str, str]:
        """Run a git command and return stdout and stderr."""
        logger.info(f"[run_git_command] Running git command: {' '.join(command)}")
        try:
            logger.debug(f"Running git command: {' '.join(command)}")
            result = subprocess.run(
                ["git", *command],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            stdout, stderr = result.stdout.strip(), result.stderr.strip()
            if stdout:
                logger.debug(f"Command output: {stdout}")
            if stderr:
                logger.warning(f"Command stderr: {stderr}")
            return stdout, stderr
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Git command failed: {' '.join(command)}",
                exc_info=True,
            )
            return "", e.stderr.strip()

    def stage_all_changes(self) -> bool:
        """Stage all changes in the repository."""
        logger.info("[stage_all_changes] Staging all changes")
        try:
            # Get status before staging
            status_before = self._run_git_command(["status", "--porcelain"])[0]
            logger.debug(f"Files to stage:\n{status_before}")

            # Stage changes
            self._run_git_command(["add", "-A"])

            # Verify staging
            status_after = self._run_git_command(["status", "--porcelain"])[0]
            staged_count = len([line for line in status_after.split("\n") if line.startswith("A ")])
            logger.info(f"Successfully staged {staged_count} changes")
            return True
        except Exception:
            logger.error("Failed to stage changes", exc_info=True)
            return False

    def commit_changes(self, message: str) -> bool:
        """Commit staged changes with a given message."""
        logger.info("[commit_changes] Attempting to commit changes")
        try:
            logger.debug(f"Attempting to commit with message: {message}")

            # First stage any changes
            if not self.stage_all_changes():
                logger.warning("No changes to commit")
                return False

            # Commit changes
            stdout, stderr = self._run_git_command(["commit", "-m", message])
            if stdout:
                logger.info(f"Successfully committed changes: {stdout}")
                return True
            logger.warning("Commit command succeeded but no output received")
            return False
        except Exception:
            logger.error("Failed to commit changes", exc_info=True)
            return False

    def get_repository_state(self) -> dict[str, list[str]]:
        """Get the current state of the repository."""
        logger.info("[get_repository_state] Getting repository state")
        try:
            # Get current branch
            branch = self.get_current_branch()
            logger.debug(f"Current branch: {branch}")

            # Get status
            status_output, _ = self._run_git_command(["status", "--porcelain"])
            status_lines = status_output.split("\n") if status_output else []
            logger.debug(f"Found {len(status_lines)} status lines")

            # Parse status
            staged = []
            unstaged = []
            untracked = []

            for line in status_lines:
                if not line:
                    continue
                status = line[:2]
                path = line[3:].strip()

                if status.startswith("??"):
                    untracked.append(path)
                    logger.debug(f"Untracked file: {path}")
                elif status[0] != " ":
                    staged.append(path)
                    logger.debug(f"Staged file: {path}")
                elif status[1] != " ":
                    unstaged.append(path)
                    logger.debug(f"Unstaged file: {path}")

            state = {
                "branch": branch,
                "staged": staged,
                "unstaged": unstaged,
                "untracked": untracked,
            }

            logger.info(
                f"Repository state - Branch: {branch}, "
                + f"Staged: {len(staged)}, "
                + f"Unstaged: {len(unstaged)}, "
                + f"Untracked: {len(untracked)}",
            )
            return state
        except Exception:
            logger.error("Failed to get repository state", exc_info=True)
            state = {
                "branch": "unknown",
                "staged": [],
                "unstaged": [],
                "untracked": [],
            }
            logger.debug("Returning empty repository state")
            return state

    def get_current_branch(self) -> str:
        """Get the name of the current branch."""
        logger.info("[get_current_branch] Getting current branch")
        try:
            branch_output, _ = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
            branch = branch_output.strip()
            logger.debug(f"Current branch: {branch}")
            return branch
        except Exception:
            logger.error("Failed to get current branch", exc_info=True)
            return "unknown"


# logging.py
from loguru import logger
import time
from functools import wraps

def timeit(func):  # pragma: no cover
    """
    Decorator that logs the execution time of the decorated function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__qualname__} executed in {elapsed:.6f}s")
        return result
    return wrapper

timeit = timeit

# paths.py
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from dotenv import load_dotenv
from enum import Enum
import os
from typing import NamedTuple
from erasmus.utils.logging import timeit

load_dotenv()


class IDEMetadata(NamedTuple):
    """Metadata for an IDE environment."""

    name: str
    rules_file: str
    global_rules_path: Path


class IDE(Enum):
    """IDE environment with associated metadata."""

    windsurf = IDEMetadata(
        name="windsurf",
        rules_file=".windsurfrules",
        global_rules_path=Path.home() / ".codeium" / "windsurf" / "memories" / "global_rules.md",
    )

    cursor = IDEMetadata(
        name="cursor",
        rules_file=".cursorrules",
        global_rules_path=Path.cwd() / ".cursor" / "global_rules.md",
    )

    codex = IDEMetadata(
        name="codex",
        # Local rules file for Codex IDE (prefixed with a dot)
        rules_file=".codex.md",
        global_rules_path=Path.home() / ".codex" / "instructions.md",
    )

    claude = IDEMetadata(
        name="claude",
        rules_file="CLAUDE.md",
        global_rules_path=Path.home() / ".claude" / "CLAUDE.md",
    )

    @property
    def metadata(self) -> IDEMetadata:
        """Get the metadata for this IDE."""
        return self.value

    @property
    def rules_file(self) -> str:
        """Get the rules file name for this IDE."""
        return self.metadata.rules_file

    @property
    def global_rules_path(self) -> Path:
        """Get the global rules path for this IDE."""
        return self.metadata.global_rules_path


def detect_ide_from_env() -> IDE | None:
    """
    Detect IDE from environment variables.
    Returns None if no IDE is detected.
    """
    ide_env = os.environ.get("IDE_ENV", "").lower()

    if not ide_env:
        return None

    # Check for IDE based on prefix
    if ide_env.startswith("w"):
        return IDE.windsurf
    elif ide_env.startswith("cu"):
        return IDE.cursor
    elif ide_env.startswith("co"):
        return IDE.codex
    elif ide_env.startswith("cl"):
        return IDE.claude

    return None


def prompt_for_ide() -> IDE:
    """
    Prompt the user to select an IDE.
    Returns the selected IDE.
    """
    print("No IDE environment detected. Please select an IDE:")
    print("1. Windsurf")
    print("2. Cursor")
    print("3. Codex")
    print("4. Claude")

    while True:
        try:
            choice = input("Enter your choice (1-4): ")
            if choice == "1":
                return IDE.windsurf
            elif choice == "2":
                return IDE.cursor
            elif choice == "3":
                return IDE.codex
            elif choice == "4":
                return IDE.claude
            else:
                print("Invalid choice. Please enter a number between 1 and 4.")
        except KeyboardInterrupt:
            print("\nOperation cancelled. Using default IDE (Cursor).")
            return IDE.cursor


def get_ide() -> IDE:
    """
    Get the IDE from environment variables or prompt the user.
    Returns the selected IDE.
    """
    ide = detect_ide_from_env()
    if ide is None:
        ide = prompt_for_ide()
        environment = Path.cwd() / ".env"
        if environment.exists():
            environment_content = environment.read_text()
            environment_content += f"\nIDE_ENV={ide.name}"
            environment.write_text(environment_content)
        else:
            environment.write_text(f"IDE_ENV={ide.name}")
    return ide


class PathMngrModel(BaseModel):
    """Manages paths for different IDE environments."""

    # Allow extra attributes for mocking and patching
    model_config = ConfigDict(extra="allow")

    ide: IDE | None = None
    # Directories
    root_dir: Path = Path.cwd()
    erasmus_dir: Path = Field(default_factory=lambda: Path.cwd() / ".erasmus")
    context_dir: Path = Field(default_factory=lambda: Path.cwd() / ".erasmus" / "context")
    protocol_dir: Path = Field(default_factory=lambda: Path.cwd() / ".erasmus" / "protocol")
    template_dir: Path = Field(default_factory=lambda: Path.cwd() / ".erasmus" / "templates")

    # Files
    architecture_file: Path = Field(default_factory=lambda: Path.cwd() / ".ctx.architecture.xml")
    progress_file: Path = Field(default_factory=lambda: Path.cwd() / ".ctx.progress.xml")
    tasks_file: Path = Field(default_factory=lambda: Path.cwd() / ".ctx.tasks.xml")
    rules_file: Path | None = None
    global_rules_file: Path | None = None

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize and time path setup
        self._setup_paths()

    @timeit
    def _setup_paths(self):
        """Set up paths based on the selected IDE."""
        if self.ide:
            # Set rules file based on IDE
            self.rules_file = self.root_dir / self.ide.rules_file
            self.global_rules_file = self.ide.global_rules_path

            # Create symlink for cursor if needed (special case for windsurf)
            if self.ide == IDE.windsurf:
                cursor_rules = self.root_dir / ".cursorrules"
                if self.rules_file.exists() and not cursor_rules.exists():
                    cursor_rules.symlink_to(self.rules_file)

    def get_ide_env(self) -> str | None:
        """Get the IDE environment name."""
        return self.ide.name if self.ide else None

    def get_context_dir(self) -> Path:
        """Get the context directory path."""
        return self.context_dir

    def get_protocol_dir(self) -> Path:
        """Get the protocol directory path."""
        return self.protocol_dir

    def get_architecture_file(self) -> Path:
        """Get the architecture file path."""
        return self.architecture_file

    def get_progress_file(self) -> Path:
        """Get the progress file path."""
        return self.progress_file

    def get_tasks_file(self) -> Path:
        """Get the tasks file path."""
        return self.tasks_file

    def get_rules_file(self) -> Path | None:
        """Get the rules file path."""
        return self.rules_file

    def get_global_rules_file(self) -> Path | None:
        """Get the global rules file path."""
        return self.global_rules_file

    def get_root_dir(self) -> Path:
        """Get the root directory path."""
        return self.root_dir

    def get_path(self, name: str) -> Path:
        """Get a path by name."""
        if hasattr(self, name):
            return getattr(self, name)
        raise ValueError(f"Path {name} not found")

    def set_path(self, name: str, path: Path) -> None:
        """Set a path by name."""
        if hasattr(self, name):
            setattr(self, name, path)
        else:
            raise ValueError(f"Path {name} not found")

    @timeit
    def ensure_dirs(self) -> None:
        """Ensure all directories exist."""
        self.context_dir.mkdir(parents=True, exist_ok=True)
        self.protocol_dir.mkdir(parents=True, exist_ok=True)
        self.erasmus_dir.mkdir(parents=True, exist_ok=True)
        self.template_dir.mkdir(parents=True, exist_ok=True)

    @timeit
    def ensure_files(self) -> None:
        """Ensure all files exist."""
        self.ensure_dirs()
        self.architecture_file.touch(exist_ok=True)
        self.progress_file.touch(exist_ok=True)
        self.tasks_file.touch(exist_ok=True)
        if self.rules_file:
            self.rules_file.touch(exist_ok=True)
        if self.global_rules_file:
            self.global_rules_file.touch(exist_ok=True)

    @timeit
    def setup_paths(self) -> None:
        """Set up all paths and ensure directories and files exist."""
        self._setup_paths()
        self.ensure_dirs()
        self.ensure_files()


# Singleton instance
_path_manager = None


def get_path_manager(ide: IDE | None = None) -> PathMngrModel:
    """Get the singleton path manager instance."""
    global _path_manager
    if _path_manager is None:
        # If no IDE is provided, try to detect it
        if ide is None:
            ide = get_ide()
        _path_manager = PathMngrModel(ide=ide)
    elif ide is not None and _path_manager.ide != ide:
        # Update the IDE if it's different
        _path_manager.ide = ide
        _path_manager._setup_paths()
    return _path_manager


# Legacy alias for backwards compatibility
PathManager = PathMngrModel

IDEMetadata = IDEMetadata
IDE = IDE
detect_ide_from_env = detect_ide_from_env
prompt_for_ide = prompt_for_ide
get_ide = get_ide
PathMngrModel = PathMngrModel
get_path_manager = get_path_manager

# sanatizer.py
import re
import xml.etree.ElementTree as ET
from typing import Any


def _sanitize_string(name: str) -> str:
    """Sanitize a string by removing emoji and non-ASCII characters while preserving valid markdown characters.
    Returns an ASCII-safe string suitable for filenames.
    """
    # First remove emoji using regex pattern
    no_emoji = re.sub(r"[\U0001F300-\U0001F9FF]", "", name)
    # Allow markdown special chars but remove other non-ASCII
    allowed_special = r"[#*_\-`~\[\](){}|<>.!]"
    sanitized = ""
    for character in no_emoji:
        # Skip non-ASCII characters entirely
        if not character.isascii():
            continue
        # Allow alphanumeric and certain special characters
        if character.isalnum() or re.match(allowed_special, character):
            sanitized += character
        else:
            sanitized += "_"
    # Collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    # Ensure it starts with a letter
    if not sanitized[0].isalpha():
        sanitized = "p_" + sanitized
    # Strip trailing underscores
    sanitized = sanitized.rstrip("_")
    return sanitized


def _sanitize_xml_content(xml_content: str) -> str:
    """Sanitize XML content by ensuring it's well-formed and safe.

    Args:
        xml_content: The XML content to sanitize

    Returns:
        Sanitized XML content
    """
    # Replace invalid XML characters
    # XML 1.0 specification allows: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    # We'll replace control characters and other invalid characters
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", xml_content)

    # Replace invalid XML entities
    sanitized = re.sub(
        r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", sanitized
    )

    # Ensure the XML is well-formed
    try:
        # Try to parse the XML to ensure it's well-formed
        ET.fromstring(sanitized)
        return sanitized
    except ET.ParseError:
        # If parsing fails, try to fix common issues
        # Add XML declaration if missing
        if not sanitized.strip().startswith("<?xml"):
            sanitized = '<?xml version="1.0" encoding="UTF-8"?>\n' + sanitized

        # Try to parse again
        try:
            ET.fromstring(sanitized)
            return sanitized
        except ET.ParseError:
            # If still failing, return a minimal valid XML
            return '<?xml version="1.0" encoding="UTF-8"?>\n<root></root>'


def _sanitize_xml_attribute(value: str) -> str:
    """Sanitize a string for use as an XML attribute value.

    Args:
        value: The attribute value to sanitize

    Returns:
        Sanitized attribute value
    """
    # Replace special XML characters with their entities
    sanitized = value.replace("&", "&amp;")
    sanitized = sanitized.replace("<", "&lt;")
    sanitized = sanitized.replace(">", "&gt;")
    sanitized = sanitized.replace('"', "&quot;")
    sanitized = sanitized.replace("'", "&apos;")

    # Remove invalid XML characters
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)

    return sanitized


def _sanitize_xml_tag(tag: str) -> str:
    """Sanitize a string for use as an XML tag name.

    Args:
        tag: The tag name to sanitize

    Returns:
        Sanitized tag name
    """
    # XML tag names must start with a letter or underscore
    if not tag or not (tag[0].isalpha() or tag[0] == "_"):
        tag = "x_" + tag

    # Replace invalid characters with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", tag)

    # Ensure it's a valid XML name
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\-\.]*$", sanitized):
        sanitized = "x_" + sanitized

    return sanitized


def sanitize_for_xml(value: Any) -> str:
    """Sanitize a value for use in XML.

    Args:
        value: The value to sanitize

    Returns:
        Sanitized value as a string
    """
    if value is None:
        return ""

    # Convert to string
    str_value = str(value)

    # Replace special XML characters with their entities
    sanitized = str_value.replace("&", "&amp;")
    sanitized = sanitized.replace("<", "&lt;")
    sanitized = sanitized.replace(">", "&gt;")
    sanitized = sanitized.replace('"', "&quot;")
    sanitized = sanitized.replace("'", "&apos;")

    # Remove invalid XML characters
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)

    return sanitized

sanitize_for_xml = sanitize_for_xml

# __init__.py
"""
Utility modules for Erasmus.
"""

from erasmus.utils.paths import get_path_manager

__all__ = ["get_path_manager"]


# xml_parser.py
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def parse_xml_file(file_path: Union[str, Path]) -> ET.Element:
    """
    Parse an XML file and return the root element.

    Args:
        file_path: Path to the XML file

    Returns:
        The root element of the XML document

    Raises:
        FileNotFoundError: If the file doesn't exist
        ET.ParseError: If the XML is not well-formed
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"XML file not found: {file_path}")

    try:
        tree = ET.parse(file_path)
        return tree.getroot()
    except ET.ParseError as parse_error:
        raise ET.ParseError(f"Error parsing XML file {file_path}: {parse_error}")


def parse_xml_string(xml_string: str) -> ET.Element:
    """
    Parse an XML string and return the root element.

    Args:
        xml_string: The XML content as a string

    Returns:
        The root element of the XML document

    Raises:
        ET.ParseError: If the XML is not well-formed
    """
    try:
        return ET.fromstring(xml_string)
    except ET.ParseError as parse_error:
        raise ET.ParseError(f"Error parsing XML string: {parse_error}")


def get_element_text(root: ET.Element, xpath: str, default: Any = None) -> Any:
    """
    Get the text content of an element using XPath.

    Args:
        root: The root element of the XML document
        xpath: XPath expression to find the element
        default: Default value to return if the element is not found

    Returns:
        The text content of the element, or the default value if not found
    """
    element = root.find(xpath)
    if element is None:
        return default
    return element.text


def get_element_attribute(root: ET.Element, xpath: str, attribute: str, default: Any = None) -> Any:
    """
    Get the value of an attribute using XPath.

    Args:
        root: The root element of the XML document
        xpath: XPath expression to find the element
        attribute: Name of the attribute
        default: Default value to return if the attribute is not found

    Returns:
        The value of the attribute, or the default value if not found
    """
    element = root.find(xpath)
    if element is None:
        return default
    return element.get(attribute, default)


def get_elements(root: ET.Element, xpath: str) -> list[ET.Element]:
    """
    Get all elements matching an XPath expression.

    Args:
        root: The root element of the XML document
        xpath: XPath expression to find the elements

    Returns:
        A list of elements matching the XPath expression
    """
    return root.findall(xpath)


def get_element_texts(root: ET.Element, xpath: str) -> list[str]:
    """
    Get the text content of all elements matching an XPath expression.

    Args:
        root: The root element of the XML document
        xpath: XPath expression to find the elements

    Returns:
        A list of text content from elements matching the XPath expression
    """
    elements = get_elements(root, xpath)
    return [element.text for element in elements if element.text]


def get_architecture_title(file_path: Union[str, Path]) -> Optional[str]:
    """
    Extract the title from an architecture XML document.

    Args:
        file_path: Path to the architecture XML file

    Returns:
        The title of the architecture, or None if not found
    """
    try:
        root = parse_xml_file(file_path)
        # Try different possible locations for the title
        title = get_element_text(root, ".//Title")
        if title:
            return title

        title = get_element_text(root, ".//MetaAgent/Title")
        if title:
            return title

        title = get_element_text(root, ".//Overview/Title")
        if title:
            return title

        return None
    except (FileNotFoundError, ET.ParseError):
        return None


def get_protocol_name(file_path: Union[str, Path]) -> Optional[str]:
    """
    Extract the protocol name from a protocol XML document.

    Args:
        file_path: Path to the protocol XML file

    Returns:
        The name of the protocol, or None if not found
    """
    try:
        root = parse_xml_file(file_path)
        # Try different possible locations for the protocol name
        name = get_element_text(root, ".//Name")
        if name:
            return name

        name = get_element_text(root, ".//Protocol/Name")
        if name:
            return name

        return None
    except (FileNotFoundError, ET.ParseError):
        return None


def xml_to_dict(element: ET.Element) -> dict[str, Any]:
    """
    Convert an XML element to a dictionary.

    Args:
        element: The XML element to convert

    Returns:
        A dictionary representation of the XML element
    """
    result = {}

    # Add attributes
    for attribute_key, attribute_value in element.attrib.items():
        result[f"@{attribute_key}"] = attribute_value

    # Add text content if it exists and is not just whitespace
    if element.text and element.text.strip():
        result["#text"] = element.text.strip()

    # Add child elements
    for child_element in element:
        child_dict = xml_to_dict(child_element)
        child_tag = child_element.tag

        # Handle multiple children with the same tag
        if child_tag in result:
            if isinstance(result[child_tag], list):
                result[child_tag].append(child_dict)
            else:
                result[child_tag] = [result[child_tag], child_dict]
        else:
            result[child_tag] = child_dict

    return result

parse_xml_file = parse_xml_file
parse_xml_string = parse_xml_string
get_element_text = get_element_text
get_element_attribute = get_element_attribute
get_elements = get_elements
get_element_texts = get_element_texts
get_architecture_title = get_architecture_title
get_protocol_name = get_protocol_name
xml_to_dict = xml_to_dict

# rich_console.py
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from typing import Any, Optional


# Singleton Console instance
def get_console() -> Console:
    if not hasattr(get_console, "_console"):
        get_console._console = Console()
    return get_console._console


def print_panel(content: str, title: Optional[str] = None, style: str = "bold blue"):
    console = get_console()
    panel = Panel(content, title=title, style=style)
    console.print(panel)


def print_table(headers: list[str], rows: list[list[Any]], title: Optional[str] = None):
    console = get_console()
    table = Table(title=title)
    for header in headers:
        table.add_column(header)
    for row in rows:
        table.add_row(*[str(cell) for cell in row])
    console.print(table)


def print_syntax(code: str, language: str = "python", title: Optional[str] = None):
    console = get_console()
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    if title:
        console.print(Panel(syntax, title=title))
    else:
        console.print(syntax)


def print_success(message: str):
    console = get_console()
    console.print(f"[bold green]✔ {message}")


def print_error(message: str):
    console = get_console()
    console.print(f"[bold red]✖ {message}")


def print_warning(message: str):
    console = get_console()
    console.print(f"[bold yellow]! {message}")


def print_info(message: str):
    console = get_console()
    console.print(f"[bold blue]ℹ {message}")

get_console = get_console
print_panel = print_panel
print_table = print_table
print_syntax = print_syntax
print_success = print_success
print_error = print_error
print_warning = print_warning
print_info = print_info

# mcp.py
"""
Model Context Protocol (MCP) functionality for Erasmus.
"""

import os
import json
from typing import Optional, Any
from loguru import logger


class MCPError(Exception):
    """Base exception for MCP-related errors."""

    pass


class MCPClient:
    """Client for interacting with MCP servers."""

    def __init__(self, server_url: str):
        """Initialize the MCP client.

        Args:
            server_url: URL of the MCP server to connect to
        """
        self.server_url = server_url
        self.connected = False

    def connect(self) -> None:
        """Connect to the MCP server.

        Raises:
            MCPError: If connection fails
        """
        try:
            # TODO: Implement actual connection logic
            logger.info(f"Connecting to MCP server at {self.server_url}")
            self.connected = True
        except Exception as e:
            raise MCPError(f"Failed to connect to MCP server: {e}")

    def disconnect(self) -> None:
        """Disconnect from the MCP server.

        Raises:
            MCPError: If disconnection fails
        """
        try:
            # TODO: Implement actual disconnection logic
            logger.info(f"Disconnecting from MCP server at {self.server_url}")
            self.connected = False
        except Exception as e:
            raise MCPError(f"Failed to disconnect from MCP server: {e}")

    def send_request(self, request_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Send a request to the MCP server.

        Args:
            request_type: Type of request to send
            data: Request data

        Returns:
            Response from the server

        Raises:
            MCPError: If request fails
        """
        if not self.connected:
            raise MCPError("Not connected to MCP server")

        try:
            # TODO: Implement actual request logic
            logger.info(f"Sending {request_type} request to MCP server")
            return {"status": "success", "data": {}}
        except Exception as e:
            raise MCPError(f"Failed to send request to MCP server: {e}")


class MCPServer:
    """Server for handling MCP requests."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        """Initialize the MCP server.

        Args:
            host: Host to bind the server to
            port: Port to bind the server to
        """
        self.host = host
        self.port = port
        self.running = False

    def start(self) -> None:
        """Start the MCP server.

        Raises:
            MCPError: If server start fails
        """
        try:
            # TODO: Implement actual server start logic
            logger.info(f"Starting MCP server on {self.host}:{self.port}")
            self.running = True
        except Exception as e:
            raise MCPError(f"Failed to start MCP server: {e}")

    def stop(self) -> None:
        """Stop the MCP server.

        Raises:
            MCPError: If server stop fails
        """
        try:
            # TODO: Implement actual server stop logic
            logger.info(f"Stopping MCP server on {self.host}:{self.port}")
            self.running = False
        except Exception as e:
            raise MCPError(f"Failed to stop MCP server: {e}")

    def process_request(self, request_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Process a request from an MCP client.

        Args:
            request_type: Type of request to process
            data: Request data

        Returns:
            Response to send to the client

        Raises:
            MCPError: If request processing fails
        """
        if not self.running:
            raise MCPError("MCP server is not running")

        try:
            # TODO: Implement actual request processing logic
            logger.info(f"Processing {request_type} request")
            return {"status": "success", "data": {}}
        except Exception as e:
            raise MCPError(f"Failed to process request: {e}")


class MCPRegistry:
    """
    Registry for MCP servers and clients.

    This class manages the registration and retrieval of MCP servers and clients.
    It provides functionality to register, unregister, and list servers and clients.
    The registry data is persisted to a JSON file.
    """

    def __init__(self, registry_file: str = None):
        """
        Initialize the MCP registry.

        Args:
            registry_file: Path to the registry file. If None, a default path is used.
        """
        if registry_file is None:
            # Use a default path in the user's home directory
            home_dir = os.path.expanduser("~")
            self.registry_file = os.path.join(home_dir, ".erasmus", "mcp_registry.json")
        else:
            self.registry_file = registry_file

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)

        # Initialize the registry data (start fresh in-memory)
        self._load_registry()
        # Ensure clean state for servers and clients (ignore persisted file)
        self.registry = {"servers": {}, "clients": {}}

    def _load_registry(self) -> None:
        """Load the registry data from the registry file."""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r") as f:
                    self.registry = json.load(f)
            except json.JSONDecodeError:
                # If the file is corrupted, start with an empty registry
                self.registry = {"servers": {}, "clients": {}}
        else:
            # If the file doesn't exist, start with an empty registry
            self.registry = {"servers": {}, "clients": {}}

    def _save_registry(self) -> None:
        """Save the registry data to the registry file."""
        with open(self.registry_file, "w") as f:
            json.dump(self.registry, f, indent=2)

    def register_server(self, name: str, host: str, port: int) -> None:
        """
        Register a new MCP server.

        Args:
            name: The name of the server.
            host: The host address of the server.
            port: The port number of the server.

        Raises:
            MCPError: If a server with the same name is already registered.
        """
        if name in self.registry["servers"]:
            raise MCPError(f"Server '{name}' already registered")

        self.registry["servers"][name] = {"host": host, "port": port}
        self._save_registry()

    def unregister_server(self, name: str) -> None:
        """
        Unregister an MCP server.

        Args:
            name: The name of the server to unregister.

        Raises:
            MCPError: If the server is not found.
        """
        if name not in self.registry["servers"]:
            raise MCPError(f"Server '{name}' not registered")

        # Remove any clients that were connected to this server
        clients_to_remove = []
        for client_name, client_data in self.registry["clients"].items():
            if client_data["server"] == name:
                clients_to_remove.append(client_name)

        for client_name in clients_to_remove:
            del self.registry["clients"][client_name]

        # Remove the server
        del self.registry["servers"][name]
        self._save_registry()

    def get_server(self, name: str) -> Optional[dict[str, Any]]:
        """
        Get the details of a registered MCP server.

        Args:
            name: The name of the server.

        Returns:
            A dictionary containing the server details, or None if not found.
        """
        return self.registry.get("servers", {}).get(name)

    def list_servers(self) -> list[str]:
        """
        List all registered MCP servers.

        Returns:
            A list of server names.
        """
        return list(self.registry["servers"].keys())

    def register_client(self, name: str, server: str) -> None:
        """
        Register a new MCP client.

        Args:
            name: The name of the client.
            server: The name of the server the client connects to.

        Raises:
            MCPError: If a client with the same name is already registered,
                     or if the specified server is not found.
        """
        if name in self.registry["clients"]:
            raise MCPError(f"Client '{name}' already registered")

        if server not in self.registry["servers"]:
            raise MCPError(f"Server '{server}' not registered")

        self.registry["clients"][name] = {"server": server}
        self._save_registry()

    def unregister_client(self, name: str) -> None:
        """
        Unregister an MCP client.

        Args:
            name: The name of the client to unregister.

        Raises:
            MCPError: If the client is not found.
        """
        if name not in self.registry["clients"]:
            raise MCPError(f"Client '{name}' not registered")

        del self.registry["clients"][name]
        self._save_registry()

    def get_client(self, name: str) -> Optional[dict[str, Any]]:
        """
        Get the details of a registered MCP client.

        Args:
            name: The name of the client.

        Returns:
            A dictionary containing the client details, or None if not found.
        """
        return self.registry.get("clients", {}).get(name)

    def list_clients(self) -> list[str]:
        """
        List all registered MCP clients.

        Returns:
            A list of client names.
        """
        return list(self.registry["clients"].keys())

    @property
    def servers(self) -> dict[str, Any]:
        """Dictionary of registered MCP servers."""
        return self.registry.get("servers", {})

    @property
    def clients(self) -> dict[str, Any]:
        """Dictionary of registered MCP clients."""
        return self.registry.get("clients", {})

MCPError = MCPError

# test_mcp_registry.py
"""
Tests for the MCP registry functionality.
"""

import os
import json
import tempfile
import pytest
from erasmus.mcp.mcp import MCPRegistry, MCPError


@pytest.fixture
def temp_registry_file():
    """Create a temporary registry file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        yield temp_file.name
    # Clean up the temporary file after tests
    os.unlink(temp_file.name)


@pytest.fixture
def registry(temp_registry_file):
    """Create a registry instance with a temporary file."""
    return MCPRegistry(registry_file=temp_registry_file)


def test_register_server(registry):
    """Test registering a server."""
    registry.register_server("test-server", "localhost", 8000)
    server = registry.get_server("test-server")
    assert server["host"] == "localhost"
    assert server["port"] == 8000


def test_register_duplicate_server(registry):
    """Test registering a duplicate server."""
    registry.register_server("test-server", "localhost", 8000)
    with pytest.raises(MCPError, match="Server 'test-server' already registered"):
        registry.register_server("test-server", "localhost", 8001)


def test_unregister_server(registry):
    """Test unregistering a server."""
    registry.register_server("test-server", "localhost", 8000)
    registry.unregister_server("test-server")
    with pytest.raises(MCPError, match="Server 'test-server' not found"):
        registry.get_server("test-server")


def test_unregister_nonexistent_server(registry):
    """Test unregistering a nonexistent server."""
    with pytest.raises(MCPError, match="Server 'nonexistent-server' not found"):
        registry.unregister_server("nonexistent-server")


def test_list_servers(registry):
    """Test listing servers."""
    registry.register_server("server1", "localhost", 8000)
    registry.register_server("server2", "localhost", 8001)
    servers = registry.list_servers()
    assert "server1" in servers
    assert "server2" in servers
    assert len(servers) == 2


def test_register_client(registry):
    """Test registering a client."""
    registry.register_server("test-server", "localhost", 8000)
    registry.register_client("test-client", "test-server")
    client = registry.get_client("test-client")
    assert client["server"] == "test-server"


def test_register_client_nonexistent_server(registry):
    """Test registering a client to a nonexistent server."""
    with pytest.raises(MCPError, match="Server 'nonexistent-server' not found"):
        registry.register_client("test-client", "nonexistent-server")


def test_register_duplicate_client(registry):
    """Test registering a duplicate client."""
    registry.register_server("test-server", "localhost", 8000)
    registry.register_client("test-client", "test-server")
    with pytest.raises(MCPError, match="Client 'test-client' already registered"):
        registry.register_client("test-client", "test-server")


def test_unregister_client(registry):
    """Test unregistering a client."""
    registry.register_server("test-server", "localhost", 8000)
    registry.register_client("test-client", "test-server")
    registry.unregister_client("test-client")
    with pytest.raises(MCPError, match="Client 'test-client' not found"):
        registry.get_client("test-client")


def test_unregister_nonexistent_client(registry):
    """Test unregistering a nonexistent client."""
    with pytest.raises(MCPError, match="Client 'nonexistent-client' not found"):
        registry.unregister_client("nonexistent-client")


def test_list_clients(registry):
    """Test listing clients."""
    registry.register_server("test-server", "localhost", 8000)
    registry.register_client("client1", "test-server")
    registry.register_client("client2", "test-server")
    clients = registry.list_clients()
    assert "client1" in clients
    assert "client2" in clients
    assert len(clients) == 2


def test_persistence(registry, temp_registry_file):
    """Test that registry data persists between instances."""
    registry.register_server("test-server", "localhost", 8000)
    registry.register_client("test-client", "test-server")

    # Create a new registry instance with the same file
    new_registry = MCPRegistry(registry_file=temp_registry_file)

    # Check that the data was loaded correctly
    server = new_registry.get_server("test-server")
    assert server["host"] == "localhost"
    assert server["port"] == 8000

    client = new_registry.get_client("test-client")
    assert client["server"] == "test-server"

temp_registry_file = temp_registry_file
registry = registry
test_register_server = test_register_server
test_register_duplicate_server = test_register_duplicate_server
test_unregister_server = test_unregister_server
test_unregister_nonexistent_server = test_unregister_nonexistent_server
test_list_servers = test_list_servers
test_register_client = test_register_client
test_register_client_nonexistent_server = test_register_client_nonexistent_server
test_register_duplicate_client = test_register_duplicate_client
test_unregister_client = test_unregister_client
test_unregister_nonexistent_client = test_unregister_nonexistent_client
test_list_clients = test_list_clients
test_persistence = test_persistence

# test_file_monitor.py
"""Tests for file monitoring functionality."""
import os
import pytest
import tempfile
import time
from watchdog.observers import Observer
from erasmus.file_monitor import FileMonitor, FileEventHandler

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname

@pytest.fixture
def file_monitor(temp_dir):
    """Create a FileMonitor instance for testing."""
    monitor = FileMonitor(temp_dir)
    monitor.start()
    yield monitor
    monitor.stop()

def test_file_monitor_init(temp_dir):
    """Test FileMonitor initialization."""
    monitor = FileMonitor(temp_dir)
    monitor.start()
    try:
        assert monitor.watch_path == temp_dir
        assert isinstance(monitor.observer, Observer)
        assert monitor.observer.is_alive()
        assert monitor._is_running
    finally:
        monitor.stop()

def test_file_pattern_matching(temp_dir):
    """Test file pattern matching."""
    monitor = FileMonitor(temp_dir)
    
    # Create test files
    rules_file = os.path.join(temp_dir, ".windsurfrules")
    with open(rules_file, 'w') as f:
        f.write("test")
    
    context_file = os.path.join(temp_dir, "architecture.md")
    with open(context_file, 'w') as f:
        f.write("test")
    
    # Test pattern matching
    assert monitor._matches_rules_file(rules_file)
    assert not monitor._matches_rules_file(context_file)

def test_event_handling(temp_dir):
    """Test file event handling."""
    monitor = FileMonitor(temp_dir)
    monitor.start()
    try:
        # Create a test file
        test_file = os.path.join(temp_dir, ".windsurfrules")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Wait for event processing
        time.sleep(0.2)
        
        # Verify event was processed
        assert test_file in monitor.event_handler.processed_events
    finally:
        monitor.stop()

def test_debouncing(temp_dir):
    """Test event debouncing."""
    monitor = FileMonitor(temp_dir)
    monitor.start()
    try:
        # Create and modify a test file rapidly
        test_file = os.path.join(temp_dir, ".windsurfrules")
        
        # Multiple rapid modifications
        for i in range(5):
            with open(test_file, 'w') as f:
                f.write(f"content {i}")
            time.sleep(0.01)  # Very short delay
        
        # Wait for debounce period
        time.sleep(0.2)
        
        # Verify only one event was processed
        assert len(monitor.event_handler.processed_events) == 1
        assert test_file in monitor.event_handler.processed_events
    finally:
        monitor.stop()

def test_error_handling(temp_dir):
    """Test error handling."""
    nonexistent_path = os.path.join(temp_dir, "nonexistent")
    
    # Try to monitor non-existent directory
    with pytest.raises(FileNotFoundError):
        FileMonitor(nonexistent_path)

def test_lifecycle_management(temp_dir):
    """Test monitor lifecycle."""
    monitor = FileMonitor(temp_dir)
    
    # Test initial state
    assert not monitor._is_running
    assert monitor.observer is None
    
    # Test start
    monitor.start()
    assert monitor._is_running
    assert monitor.observer.is_alive()
    
    # Test stop
    monitor.stop()
    assert not monitor._is_running
    assert monitor.observer is None
    
    # Test restart
    monitor.start()
    assert monitor._is_running
    assert monitor.observer.is_alive()
    monitor.stop() 
temp_dir = temp_dir
file_monitor = file_monitor
test_file_monitor_init = test_file_monitor_init
test_file_pattern_matching = test_file_pattern_matching
test_event_handling = test_event_handling
test_debouncing = test_debouncing
test_error_handling = test_error_handling
test_lifecycle_management = test_lifecycle_management