"""Context Management System for Erasmus Development Workflow.

This module provides a comprehensive context management system that enables:
- Dynamic tracking of project development context
- XML-based file management for architecture, progress, and tasks
- Sanitization and validation of context files
- Cross-platform compatibility for context storage

Key Features:
- Centralized context file management in .erasmus/context directory
- Supports multiple context files with XML-based templates
- Robust error handling for context-related operations
- Preservation of rich content while ensuring system stability

The context management system is designed to:
1. Track project architecture and progress
2. Manage development tasks and protocols
3. Provide a flexible, extensible context storage mechanism

Note: Non-ASCII characters are preserved in context files but sanitized
      when writing to system rules files to ensure cross-platform compatibility.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
import re
import shutil
import typer
import sys

from loguru import logger
from pydantic import BaseModel

from erasmus.utils.paths import get_path_manager
from erasmus.utils.rich_console import get_console
from erasmus.utils.sanatizer import _sanitize_string, _sanitize_xml_content
from erasmus.protocol import ProtocolManager
from erasmus.environment import get_env_config

console = get_console()


class ContextError(Exception):
    """Base exception for all context management errors.

    This exception is raised when there are general issues with context
    management that do not fit into more specific error categories.
    Serves as a base class for more specific context-related exceptions.
    """


class ContextFileError(ContextError):
    """Exception raised when file-related operations in context management fail.

    This exception is used when there are issues such as:
    - Unable to read context files
    - Permission issues accessing context files
    - Context file not found
    - Corrupted or unreadable context files
    """


class ContextValidationError(ContextError):
    """Exception raised when context content fails validation requirements.

    This exception is used when context files do not meet expected
    structural or content requirements, such as:
    - Malformed XML
    - Missing required XML elements
    - Invalid data types or values
    - Incompatible context configurations
    """


path_manager = get_path_manager()


class CtxModel(BaseModel):
    """Represents a single development context with its associated file contents.

    This model encapsulates the core files that define a project's development context,
    providing a structured representation of project metadata and configuration.

    Attributes:
        path (str): The base path or identifier for this context.
        architecture (str): XML content representing the project's architectural design.
        progress (str): XML content tracking the current progress of development components.
        tasks (str): XML content listing and tracking project tasks.
        protocol (str, optional): XML content defining development protocols. Defaults to an empty
            string.

    The model ensures that each context is a self-contained unit with all necessary
    metadata for tracking and managing a development project.
    """

    path: str
    architecture: str
    progress: str
    tasks: str
    protocol: str = ""


class CtxMngrModel(BaseModel):
    """Manages a collection of development contexts and their associated file paths.

    This model serves as a comprehensive registry for multiple development contexts,
    providing centralized management of context-related paths and contents.

    Attributes:
        contexts (list[CtxModel]): A list of all managed context models. Defaults to an empty list.
        context_dir (Path): Base directory for storing context files. Uses path_manager to determine
            location.
        base_dir (Path): Alias for context_dir, ensuring consistent path management.
        context (CtxModel | None): Currently active context model. Defaults to None.

        # Paths for core context files
        architecture_path (str | Path): Path to the architecture context file.
        progress_path (str | Path): Path to the progress context file.
        tasks_path (str | Path): Path to the tasks context file.

        # Content storage for core context files
        architecture_content (str): Raw content of the architecture file.
        progress_content (str): Raw content of the progress file.
        tasks_content (str): Raw content of the tasks file.
        protocol_content (str): Raw content of the protocol file.

    The model provides a flexible and extensible approach to managing
    multiple development contexts with centralized path and content tracking.
    """


class ContextManager:
    """Manages context storage and loading."""

    def __init__(self, base_path: str | Path | None = None) -> None:
        """Initialize the context manager.

        Args:
            base_path: Optional base path for context storage
        """
        # Configure logging based on environment
        env_config = get_env_config()
        logger.remove()  # Remove default handler
        log_level = "DEBUG" if env_config.ERASMUS_DEBUG else env_config.ERASMUS_LOG_LEVEL
        logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        )

        self.path_manager = get_path_manager()
        self._base_path = (
            Path(base_path) if base_path else Path(self.path_manager.erasmus_dir) / "context"
        )
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._architecture = None
        self._progress = None
        self._tasks = None
        self._current_context = None
        logger.info(f"Initialized ContextManager with base path: {self._base_path}")

    @property
    def architecture(self) -> str | None:
        """Get the current architecture content."""
        return self._architecture

    @property
    def progress(self) -> str | None:
        """Get the current progress content."""
        return self._progress

    @property
    def tasks(self) -> str | None:
        """Get the current tasks content."""
        return self._tasks

    @property
    def current_context(self) -> str | None:
        """Get the name of the currently loaded context."""
        return self._current_context

    def store_context(self, name: str | None = None) -> None:
        """Store the current context under a given name.

        Args:
            name: Optional name to store the context under. If not provided,
                 will try to get from architecture title or prompt user.
        """
        try:
            name = self._get_context_name(name)
            self._store_context_files(name)
            print(f"Stored context '{name}' in {self._base_path / name}")

        except Exception as e:
            print(f"Failed to store context: {e}")
            raise

    def _get_context_name(self, name: str | None) -> str:
        """Get a valid context name, either from args, architecture, or user prompt."""
        if name:
            return name

        arch_file = self.path_manager.get_architecture_file()
        if not arch_file.exists():
            return typer.prompt("Enter a name for the context")

        try:
            name = self._extract_title_from_architecture(arch_file)
            if name:
                return name
        except ET.ParseError as e:
            print(f"Failed to parse architecture file: {e}")

        return typer.prompt("Enter a name for the context")

    def _extract_title_from_architecture(self, arch_file: Path) -> str | None:
        """Extract title from architecture XML file."""
        content = arch_file.read_text().strip().replace("\n", "").replace("\r", "")
        tree = ET.ElementTree(ET.fromstring(content))
        root = tree.getroot()

        # Try direct path first
        overview = root.find("Overview")
        if overview is not None:
            title = overview.find("Title")
            if title is not None and title.text:
                return title.text.strip()

        # Try alternative paths
        title_paths = [
            ".//Title",
            ".//Architecture/Title",
            ".//Overview/Title",
            ".//Architecture/Overview/Title",
        ]

        for path in title_paths:
            title_elem = root.find(path)
            if title_elem is not None and title_elem.text:
                return title_elem.text.strip()

        # If no title found, prompt user and update architecture
        name = typer.prompt("Enter a name for the context")
        self._update_architecture_title(root, name, arch_file, tree)
        return name

    def _update_architecture_title(
        self, root: ET.Element, name: str, arch_file: Path, tree: ET.ElementTree
    ) -> None:
        """Update the architecture XML with the new title."""
        overview = root.find(".//Overview")
        if overview is None:
            overview = ET.SubElement(root, "Overview")
        title_elem = overview.find("Title")
        if title_elem is None:
            title_elem = ET.SubElement(overview, "Title")
        title_elem.text = name
        tree.write(arch_file, encoding="utf-8", xml_declaration=True)

    def _store_context_files(self, name: str) -> None:
        """Store context files in the named directory."""
        if not name:
            raise ValueError("Context name is required")

        context_dir = self._base_path / name
        context_dir.mkdir(parents=True, exist_ok=True)

        for src_file in [
            self.path_manager.get_architecture_file(),
            self.path_manager.get_progress_file(),
            self.path_manager.get_tasks_file(),
        ]:
            if src_file.exists():
                dst_file = context_dir / src_file.name
                shutil.copy2(src_file, dst_file)
                print(f"Copied {src_file} to {dst_file}")

    def load_context(self, name: str) -> None:
        """Load a stored context by name.

        Args:
            name: Name of the context to load
        """
        try:
            context_dir = self._base_path / name
            if not context_dir.exists():
                raise ValueError(f"Context '{name}' not found")

            # Copy context files back
            for src_file in context_dir.glob("*.xml"):
                if src_file.name.startswith(".ctx."):
                    dst_file = self.path_manager.get_architecture_file().parent / src_file.name
                    shutil.copy2(src_file, dst_file)
                    logger.debug(f"Copied {src_file} to {dst_file}")

            # Load the content into memory
            self._current_context = name
            arch_file = context_dir / ".ctx.architecture.xml"
            progress_file = context_dir / ".ctx.progress.xml"
            tasks_file = context_dir / ".ctx.tasks.xml"

            if arch_file.exists():
                self._architecture = arch_file.read_text()
            if progress_file.exists():
                self._progress = progress_file.read_text()
            if tasks_file.exists():
                self._tasks = tasks_file.read_text()

            logger.info(f"Loaded context '{name}' from {context_dir}")

        except Exception as e:
            logger.error(f"Failed to load context: {e}")
            raise

    def list_contexts(self) -> list[str]:
        """List all stored contexts.

        Returns:
            List of context names
        """
        try:
            return [d.name for d in self._base_path.iterdir() if d.is_dir()]
        except Exception as e:
            logger.error(f"Failed to list contexts: {e}")
            raise

    def delete_context(self, name: str) -> None:
        """Delete a stored context.

        Args:
            name: Name of the context to delete
        """
        try:
            context_dir = self._base_path / name
            shutil.rmtree(context_dir)
            logger.info(f"Deleted context '{name}'")

        except Exception as e:
            logger.error(f"Failed to delete context: {e}")
            raise

    def update_architecture(self, context_name: str, content: str) -> None:
        """Update the architecture file content for a context."""
        self.save_context_file(context_name, ".ctx.architecture.xml", content)

    def update_progress(self, context_name: str, content: str) -> None:
        """Update the progress file content for a context."""
        self.save_context_file(context_name, ".ctx.progress.xml", content)

    def update_tasks(self, context_name: str, content: str) -> None:
        """Update the tasks file content for a context."""
        self.save_context_file(context_name, ".ctx.tasks.xml", content)

    def get_default_content(self, file_type: str) -> str:
        template_map = {
            "architecture": self.path_manager.architecture_template,
            "progress": self.path_manager.progress_template,
            "tasks": self.path_manager.tasks_template,
            "protocol": self.path_manager.protocol_template,
            "meta_agent": self.path_manager.meta_agent_template,
            "meta_rules": self.path_manager.meta_rules_template,
        }
        if file_type not in template_map:
            raise ValueError(f"Unsupported file type: {file_type}")
        return template_map[file_type].read_text()

    def create_context(
        self,
        context_name: str,
        architecture_content: str | None = None,
        progress_content: str | None = None,
        tasks_content: str | None = None,
    ) -> None:
        """Create a new development context with optional custom content.

        This method establishes a new context directory and populates it with
        core XML files using either provided content or default templates.

        Args:
            context_name (str): A unique identifier for the new context.
                Will be sanitized to ensure file system compatibility.
            architecture_content (str, optional): Custom XML content for the
                architecture file. If None, uses the default template.
            progress_content (str, optional): Custom XML content for the
                progress tracking file. If None, uses the default template.
            tasks_content (str, optional): Custom XML content for the
                tasks file. If None, uses the default template.

        Raises:
            ContextError: If a context with the same name already exists.
            ValueError: If provided XML content is malformed.

        Notes:
            - Uses path_manager to locate template files
            - Sanitizes the context name for safe directory creation
            - Automatically creates a context directory
            - Supports partial or full custom content for context files
        """
        sanitized_name = self._sanitize_name(context_name)
        context_dir = self._base_path / sanitized_name
        if context_dir.exists():
            raise ContextError(f"Context already exists: {context_name}")

        # Create context directory
        context_dir.mkdir(parents=True, exist_ok=False)

        # Prepare architecture content
        architecture_content = architecture_content or self.get_default_content("architecture")
        named_architecture_content = architecture_content.replace(
            "  <Title>Project Title</Title>",
            f"  <Title>{context_name}</Title>",
        )

        # Define file mappings
        file_mappings = {
            ".ctx.architecture.xml": (
                self.path_manager.architecture_template,
                named_architecture_content,
                "Architecture",
            ),
            ".ctx.progress.xml": (
                self.path_manager.progress_template,
                progress_content or self.get_default_content("progress"),
                "Progress",
            ),
            ".ctx.tasks.xml": (
                self.path_manager.tasks_template,
                tasks_content or self.get_default_content("tasks"),
                "Tasks",
            ),
        }

        # Create each file
        for filename, (template_path, content, root_tag) in file_mappings.items():
            file_path = context_dir / filename
            try:
                # Validate XML content
                ET.fromstring(content)
                file_path.write_text(content)
            except ET.ParseError:
                # If content is not valid XML, wrap it in the appropriate root tag
                wrapped_content = f"<{root_tag}>{content}</{root_tag}>"
                file_path.write_text(wrapped_content)
            except Exception as e:
                raise ContextError(f"Failed to create {filename}: {str(e)}")

        # Create a CtxModel instance for the new context
        self.context = CtxModel(
            path=str(context_dir),
            architecture=named_architecture_content,
            progress=progress_content or self.get_default_content("progress"),
            tasks=tasks_content or self.get_default_content("tasks"),
        )

    def get_context(self, context_name: str) -> CtxModel:
        """Retrieve a specific context model by its name.

        This method searches for and returns a CtxModel instance
        corresponding to the given context name.

        Args:
            context_name (str): The name of the context to retrieve.

        Returns:
            CtxModel: The context model with the specified name.

        Raises:
            ContextError: If no context with the given name is found.

        Notes:
            - Uses get_context_model internally to fetch the context
            - Supports case-insensitive and sanitized context name matching
        """
        return self.get_context_model(context_name)

    @property
    def base_path(self) -> Path:
        """Get the base path for context storage."""
        return self._base_path

    def save_context_file(self, context_name: str, filename: str, content: str) -> None:
        """Save raw content to a file within a specific context directory.

        This method writes the provided content to a file in the context
        directory, creating the directory if it doesn't exist.

        Args:
            context_name (str): The name of the context to save the file in.
            filename (str): The name of the file to be saved.
            content (str): The raw content to write to the file.

        Raises:
            ContextError: If the context directory cannot be created or accessed.
            OSError: If there are file system permission issues.

        Notes:
            - Automatically creates the context directory if it doesn't exist
            - Overwrites the file if it already exists
            - Does not perform any content validation or sanitization
        """
        context_dir = self.get_context_path(context_name)
        context_dir.mkdir(parents=True, exist_ok=True)
        file_path = context_dir / filename
        file_path.write_text(content)

    def load_context_file(self, context_name: str, filename: str) -> str:
        """Load and sanitize content from a file within a specific context directory.

        This method reads a file from the specified context directory,
        returning an empty string if the file does not exist.

        Args:
            context_name (str): The name of the context to load the file from.
            filename (str): The name of the file to load.

        Returns:
            str: The sanitized content of the file. Returns an empty string
                 if the file does not exist.

        Notes:
            - Uses _sanitize_content to clean the loaded file content
            - Silently handles non-existent files by returning an empty string
            - Ensures that loaded content is safe for further processing

        Raises:
            ContextError: If there are issues accessing the context directory.
            OSError: If there are file system permission issues.
        """
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

    def _sanitize_name(self, context_name: str) -> str:
        """
        Sanitize a context name for filesystem use.

        Args:
            context_name: The context name to sanitize.

        Returns:
            The sanitized name.
        """
        # Replace any non-alphanumeric characters with underscores
        sanitized = re.sub(r"[^a-zA-Z0-9]", "_", context_name)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        return sanitized

    def _get_context_dir(self, context_name: str) -> Path:
        """
        Get the directory for a context.
        Args:
            context_name: The context name.
        Returns:
            The context directory path.
        """
        return self._base_path / self._sanitize_name(context_name)

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
        return self._base_path / sanitized_name

    def get_context_dir_path(self, context_name: str) -> Path | None:
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
            raise ContextFileError(
                f"Failed to get context path: {context_error}",
            ) from context_error

    def save_contexts(self) -> list[CtxModel]:
        """
        Save all contexts by loading them from disk into CtxModel instances.
        Returns:
            List of saved CtxModel instances
        """
        context_models: list[CtxModel] = []
        # Always use path_manager.get_context_dir()
        for context_directory in self.path_manager.get_context_dir().iterdir():
            if context_directory.is_dir():
                context_name = context_directory.name
                try:
                    context_path = self.get_context_dir_path(context_name)
                    if context_path:
                        context_models.append(self.get_context_model(context_name))
                except Exception as context_error:
                    logger.error(f"Failed to save context {context_name}: {context_error}")
        return context_models

    def display_context(self, context_name: str) -> None:
        """Display the contents of a context."""
        context_dir = self._get_context_dir(context_name)
        if not context_dir.exists():
            raise ContextError(f"Context not found: {context_name}")

        arch_file = context_dir / ".ctx.architecture.xml"
        progress_file = context_dir / ".ctx.progress.xml"
        tasks_file = context_dir / ".ctx.tasks.xml"

        if not all(f.exists() for f in [arch_file, progress_file, tasks_file]):
            raise ContextError(f"Missing required files in context: {context_name}")

        print(f"\nContext: {context_name}")
        print("\nArchitecture:")
        print(arch_file.read_text())
        print("\nProgress:")
        print(progress_file.read_text())
        print("\nTasks:")
        print(tasks_file.read_text())

    def select_context(self, context_name: str | None = None) -> None:
        """Select a context to work with."""
        if context_name is None:
            contexts = self.list_contexts()
            if not contexts:
                raise ContextError("No contexts available")
            print("\nAvailable contexts:")
            for i, ctx in enumerate(contexts, 1):
                print(f"{i}. {ctx}")
            while True:
                try:
                    choice = int(input("\nSelect a context (number): "))
                    if 1 <= choice <= len(contexts):
                        context_name = contexts[choice - 1]
                        break
                    print("Invalid choice. Please try again.")
                except ValueError:
                    print("Please enter a number.")

        if self.get_context(context_name):
            self.save_contexts()

        self._load_context(context_name)
        print(f"Selected context: {context_name}")

    def _load_context(self, context_name: str) -> None:
        """Load a context into memory."""
        context_dir = self._get_context_dir(context_name)
        arch_file = context_dir / ".ctx.architecture.xml"
        progress_file = context_dir / ".ctx.progress.xml"
        tasks_file = context_dir / ".ctx.tasks.xml"

        if not all(f.exists() for f in [arch_file, progress_file, tasks_file]):
            raise ContextError(f"Missing required files in context: {context_name}")

        self.current_context = context_name
        self.architecture = arch_file.read_text()
        self.progress = progress_file.read_text()
        self.tasks = tasks_file.read_text()

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
            raise ContextError(f"Failed to update file: {error}") from error

    def read_file(self, context_name: str, file_type: str) -> str | None:
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
            raise ContextError(f"Failed to read file: {error}") from error

    def edit_file(self, context_name: str, file_type: str, editor: str | None = None) -> None:
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
            raise ContextError(f"Failed to edit file: {error}") from error

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
            raise ContextFileError(f"Failed to get context: {context_error}") from context_error

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
