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

from loguru import logger
from pydantic import BaseModel

from erasmus.utils.paths import get_path_manager
from erasmus.utils.rich_console import get_console
from erasmus.utils.sanatizer import _sanitize_string, _sanitize_xml_content

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
    """
    Manages development context files in the .erasmus/context directory.
    Uses CtxModel as the in-memory storage for context data.
    Handles context selection, loading, saving, and file operations for architecture, progress, and
        tasks only.
    Protocol handling is managed by erasmus/protocol.py.
    """

    def __init__(self, base_dir: str | None = None, base_path: str | None = None) -> None:
        """Initialize the context manager with flexible base directory configuration.

        This method sets up the context management system by:
        1. Determining the base directory for context storage
        2. Creating the directory if it doesn't exist
        3. Initializing paths for core context files
        4. Preparing for context model management

        Args:
            base_dir (str | None, optional): Base directory for storing context files.
                If not provided, uses the default path from path_manager.
            base_path (str | None, optional): Alias for base_dir, provided for
                backwards compatibility. Takes precedence over base_dir if both are set.

        Raises:
            OSError: If there are permission issues creating the base directory

        Notes:
            - Uses path_manager to determine default context directory
            - Creates the base directory if it doesn't exist
            - Initializes core context file paths
            - Logs the initialization for traceability
        """
        # Determine base directory parameter (base_path overrides base_dir)
        chosen_dir = base_path if base_path is not None else base_dir
        # Remove self.base_dir assignment, always use path_manager.get_context_dir()
        logger.info(
            f"Initialized ContextManager with base path: {
                chosen_dir if chosen_dir else path_manager.get_context_dir()
            }",
        )
        # Initialize context tracking attributes
        self.context: CtxModel | None = None
        # Set paths for core context files using path_manager
        self.architecture_path: Path = path_manager.get_architecture_file()
        self.progress_path: Path = path_manager.get_progress_file()
        self.tasks_path: Path = path_manager.get_tasks_file()
        # Initialize content storage for core context files
        self.architecture_content: str | None = None
        self.progress_content: str | None = None
        self.tasks_content: str | None = None

    def get_default_content(self, file_type: str) -> str:
        content = None
        if file_type == "architecture":
            content = path_manager.architecture_template.read_text()
        if file_type == "progress":
            content = path_manager.progress_template.read_text()
        if file_type == "tasks":
            content = path_manager.tasks_template.read_text()
        if file_type == "protocol":
            content = path_manager.protocol_template.read_text()
        if file_type == "meta_agent":
            content = path_manager.meta_agent_template.read_text()
        if file_type == "meta_rules":
            content = path_manager.meta_rules_template.read_text()
        return content

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
        context_dir = path_manager.get_context_dir() / sanitized_name
        if context_dir.exists():
            raise ContextError(f"Context already exists: {context_name}")
        # Create context directory
        context_dir.mkdir(parents=True, exist_ok=False)
        # Use the correct template directory from the path manager
        template_map = {
            "ctx.architecture.xml": (
                path_manager.architecture_template,
                architecture_content or self.get_default_content("architecture"),
                "Architecture",
            ),
            "ctx.progress.xml": (
                path_manager.progress_template,
                progress_content or self.get_default_content("progress"),
                "Progress",
            ),
            "ctx.tasks.xml": (
                path_manager.tasks_template,
                tasks_content or self.get_default_content("tasks"),
                "Tasks",
            ),
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
                    content = f"<{root_tag}>{user_content}</{root_tag}>"
            elif template_path.exists():
                content = template_path.read_text()
            else:
                content = f"<{root_tag}></{root_tag}>"
            (context_dir / target_name).write_text(content)

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
        """Retrieve the base directory path for context storage.

        This property provides an alias for base_dir, maintaining backwards
        compatibility and offering a consistent interface for accessing
        the root directory of context files.

        Returns:
            Path: The base directory path where context files are stored.

        Notes:
            - Ensures consistent access to the context storage location
            - Supports both base_dir and base_path naming conventions
            - Immutable property that returns the current base directory
        """
        # Always use path_manager.get_context_dir()
        return path_manager.get_context_dir()

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
        # Always use path_manager.get_context_dir()
        return path_manager.get_context_dir() / self._sanitize_name(context_name)

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
        return self.base_path / sanitized_name

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
        for context_directory in path_manager.get_context_dir().iterdir():
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
            for file_path in context_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()
            context_dir.rmdir()
            logger.info(f"Deleted context: {context_name}")
        except Exception as context_error:
            raise ContextFileError(f"Failed to delete context: {context_error}") from context_error

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
            console.print(f"Context: {context_name}")
            console.print(f"Path: {context_dir}")
            console.print(
                f"Architecture: {
                    len(self.read_file(context_name, 'architecture'))
                    if self.read_file(context_name, 'architecture')
                    else 'N/A'
                }",
            )
            console.print(
                f"Progress: {
                    len(self.read_file(context_name, 'progress'))
                    if self.read_file(context_name, 'progress')
                    else 'N/A'
                }",
            )
            console.print(
                f"Tasks: {
                    len(self.read_file(context_name, 'tasks'))
                    if self.read_file(context_name, 'tasks')
                    else 'N/A'
                }",
            )
            console.print(
                f"Protocol: {
                    len(self.read_file(context_name, 'protocol'))
                    if self.read_file(context_name, 'protocol')
                    else 'N/A'
                }",
            )
        except Exception as context_error:
            raise ContextFileError(f"Failed to display context: {context_error}") from context_error

    def list_contexts(self) -> list[str]:
        """
        List all development contexts by name.
        Returns:
            A list of context names.
        Raises:
            ContextFileError: If contexts cannot be listed.
        """
        try:
            # Always use path_manager.get_context_dir()
            return [
                context_directory.name
                for context_directory in path_manager.get_context_dir().iterdir()
                if context_directory.is_dir()
            ]
        except Exception as context_error:
            raise ContextFileError(f"Failed to list contexts: {context_error}") from context_error

    def select_context(self) -> CtxModel:
        """
        Interactively select a context, loading it into memory and saving the current context if
            needed.
        Returns:
            The selected CtxModel instance
        Raises:
            ContextFileError: If no contexts exist
        """
        context_models = self.save_contexts()
        if not context_models:
            raise ContextFileError("No contexts exist")
        console.print("Available contexts:")
        for context_index, context_model in enumerate(context_models):
            console.print(f"{context_index + 1}. {context_model.path}")
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
                console.print("Invalid choice. Please try again.")
            except ValueError:
                console.print("Please enter a number.")

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

    def store_context(self) -> str:
        """
        Store the current context by reading the architecture, progress, and tasks files into
            memory, then writing those values to the context directory files and updating the
            in-memory CtxModel.
        Returns:
            The name of the stored context
        Raises:
            ContextError: If storing the context fails
        """
        try:
            self.architecture_content = (
                self.architecture_path.read_text()
                if self.architecture_path.exists()
                else self.get_default_content("architecture")
            )
            self.progress_content = (
                self.progress_path.read_text()
                if self.progress_path.exists()
                else self.get_default_content("progress")
            )
            self.tasks_content = (
                self.tasks_path.read_text()
                if self.tasks_path.exists()
                else self.get_default_content("tasks")
            )
            tree = ET.ElementTree(ET.fromstring(self.architecture_content))
            root = tree.getroot()
            title_elem = root.find(".//Title")
            if title_elem is not None and title_elem.text:
                title = title_elem.text
            else:
                # If no Title element, use the first line of architecture content as fallback
                first_line = self.architecture_content.strip().split("\n", 1)[0].strip()
                # Sanitize the first line to ASCII only
                title = self._sanitize_string(first_line) if first_line else "untitled"
            # Always sanitize the title to remove non-ASCII characters
            context_name_sanitized = self._sanitize_string(title)
            context_dir = self._get_context_dir(context_name_sanitized)
            context_dir.mkdir(parents=True, exist_ok=True)
            # Sanitize the architecture, progress, and tasks content to ASCII before writing
            architecture_ascii = self._sanitize_xml(self.architecture_content)
            progress_ascii = self._sanitize_xml(self.progress_content)
            tasks_ascii = self._sanitize_xml(self.tasks_content)
            (context_dir / "ctx.architecture.xml").write_text(architecture_ascii)
            (context_dir / "ctx.progress.xml").write_text(progress_ascii)
            (context_dir / "ctx.tasks.xml").write_text(tasks_ascii)
            self.context = CtxModel(
                path=str(context_dir),
                architecture=architecture_ascii,
                progress=progress_ascii,
                tasks=tasks_ascii,
            )
        except Exception as error:
            raise ContextError(f"Failed to store context: {error}") from error
        return context_name_sanitized

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
                        f"No {file_type} file found for context '{context_name}' \
                            (expected ctx.{file_type}.xml)",
                    )
        except Exception as error:
            raise ContextError(f"Failed to load context '{context_name}': {error}") from error
        # After loading context files, update IDE rules and global rules
        try:
            from erasmus.file_monitor import _merge_rules_file

            _merge_rules_file()
        except Exception as merge_error:
            logger.error(
                f"Failed to update rules file after loading context \
                    '{context_name}': {merge_error}",
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
