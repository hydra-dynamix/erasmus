"""
Context Manager for handling development context files.

This module provides functionality for managing context files in the .erasmus/context
directory, including saving, loading, and sanitizing content.
"""

import os
import re
import shutil
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import uuid
from pathlib import Path
from pydantic import BaseModel, Field
from loguru import logger
from erasmus.utils.paths import get_path_manager
from erasmus.utils.sanatizer import _sanitize_string, _sanitize_xml_content
from erasmus.utils.rich_console import get_console
from typing import Optional, List, Dict, Any

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

    def list_contexts(self) -> List[str]:
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
