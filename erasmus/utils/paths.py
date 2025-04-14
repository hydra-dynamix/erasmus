"""Path management for Erasmus project files."""

import os
from pathlib import Path
import logging
from typing import Dict, Any, Optional, ClassVar
import shutil
from datetime import datetime

from pydantic import BaseModel, Field

from .path_constants import (
    RULES_FILES,
    DIRECTORIES,
    MARKDOWN_FILES,
    SCRIPT_FILES,
    GLOBAL_RULES_PATHS,
    IDE_MARKERS,
    DEFAULT_IDE_ENV,
)
from .env_manager import EnvironmentManager

logger = logging.getLogger(__name__)


class PathManager:
    """Centralized path management for the Erasmus project."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the path manager.

        Args:
            project_root: Optional project root path. If not provided, uses current directory.
        """
        self.project_root = project_root or Path.cwd()
        self._ide_env = self._detect_ide_environment()
        self._env_manager = EnvironmentManager()

        # Initialize paths
        self._erasmus_dir = self.project_root / ".erasmus"
        self._config_dir = self._erasmus_dir / "config"
        self._cache_dir = self._erasmus_dir / "cache"
        self._logs_dir = self._erasmus_dir / "logs"
        self._context_dir = self._erasmus_dir / "context"
        self._protocols_dir = self._erasmus_dir / "protocols"
        self._stored_protocols_dir = self._protocols_dir / "stored"
        self._registry_file = self._protocols_dir / "registry.json"
        self._env_file = self.project_root / ".env"

        # Create directories
        for directory in [self._config_dir, self._cache_dir, self._logs_dir, self._context_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        try:
            # Create .erasmus directory
            self._erasmus_dir.mkdir(exist_ok=True)

            # Create all subdirectories
            for dir_name, dir_path in DIRECTORIES.items():
                if dir_name != "config":  # Skip .erasmus itself
                    full_path = self.project_root / dir_path
                    full_path.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Ensured directory exists: {full_path}")

            logger.info("Successfully created all required directories")
        except Exception as e:
            logger.error(f"Error creating directories: {e}")
            raise

    def prompt_for_ide_env(self) -> str:
        """Prompt the user for the IDE environment."""
        import click

        while True:
            user_input = click.prompt("Enter the IDE environment (windsurf/cursor)")
            if user_input.lower().startswith("w"):
                ide_env = "windsurf"
                os.environ["IDE_ENV"] = ide_env
                return ide_env
            if user_input.lower().startswith("c"):
                ide_env = "cursor"
                os.environ["IDE_ENV"] = ide_env
                return ide_env
            print("Invalid IDE environment. Please enter 'windsurf' or 'cursor'")

    def _detect_ide_environment(self) -> str:
        """Detect the current IDE environment.

        Returns:
            str: The detected IDE environment ('windsurf' or 'cursor')
        """
        # Check environment variable first
        ide_env = os.getenv("IDE_ENV", "").lower()
        if ide_env:
            if ide_env == "windsurf" or ide_env.startswith("w"):
                return "windsurf"
            if ide_env == "cursor" or ide_env.startswith("c"):
                return "cursor"

        # Try to detect based on current working directory or known IDE paths
        cwd = self.project_root
        is_windsurf = False
        is_cursor = False

        # windsurf-specific detection
        windsurf_markers = [
            Path.home() / ".codeium" / "windsurf",
            cwd / ".windsurfrules",
        ]

        # cursor-specific detection
        cursor_markers = [
            cwd / ".cursorrules",
            Path.home() / ".cursor",
        ]

        # Check windsurf markers
        for marker in windsurf_markers:
            if marker.exists():
                is_windsurf = True

        # Check cursor markers
        for marker in cursor_markers:
            if marker.exists():
                is_cursor = True

        if is_windsurf and is_cursor:
            # If both are detected, prefer windsurf
            return "windsurf"

        # Default to cursor
        return "cursor"

    @property
    def ide_env(self) -> str:
        """Get the current IDE environment."""
        return self._ide_env

    @property
    def rules_file(self) -> Path:
        """Get the rules file path based on IDE environment."""
        from dotenv import load_dotenv
        import os

        load_dotenv()
        ide_env = os.getenv("IDE_ENV", "").lower()

        # Map to the correct key for RULES_FILES dictionary
        if ide_env == "windsurf" or ide_env.startswith("w"):
            ide_key = "windsurf"
        elif ide_env == "cursor" or ide_env.startswith("c"):
            ide_key = "cursor"
        else:
            ide_key = DEFAULT_IDE_ENV  # Default to cursor

        return Path.cwd() / RULES_FILES[ide_key]

    @property
    def global_rules_file(self) -> Path:
        """Get the global rules file path based on IDE environment."""
        return self._erasmus_dir / GLOBAL_RULES_PATHS[self._ide_env]

    @property
    def erasmus_dir(self) -> Path:
        """Get the erasmus directory path."""
        return self._erasmus_dir

    @property
    def config_dir(self) -> Path:
        """Get the configuration directory path."""
        return self._config_dir

    @property
    def cache_dir(self) -> Path:
        """Get the cache directory path."""
        return self._cache_dir

    @property
    def logs_dir(self) -> Path:
        """Get the logs directory path."""
        return self._logs_dir

    @property
    def context_dir(self) -> Path:
        """Get the context directory path."""
        return self._context_dir

    @property
    def protocols_dir(self) -> Path:
        """Get the protocols directory path."""
        return self._protocols_dir

    @property
    def stored_protocols_dir(self) -> Path:
        """Get the stored protocols directory path."""
        return self._stored_protocols_dir

    @property
    def registry_file(self) -> Path:
        """Get the registry file path."""
        return self._registry_file

    @property
    def env_file(self) -> Path:
        """Get the environment file path."""
        return self._env_file

    @property
    def stored_context(self) -> Path:
        """Get the stored context directory path."""
        return self._context_dir

    @property
    def markdown_files(self) -> Dict[str, Path]:
        """Get all markdown file paths."""
        return {
            "architecture": self._erasmus_dir / MARKDOWN_FILES["architecture"],
            "progress": self._erasmus_dir / MARKDOWN_FILES["progress"],
            "tasks": self._erasmus_dir / MARKDOWN_FILES["tasks"],
        }

    def get_protocol_file(self, protocol_name: str) -> Path:
        """Get the path to a protocol file.

        Args:
            protocol_name: Name of the protocol

        Returns:
            Path: Path to the protocol file
        """
        return self._stored_protocols_dir / f"{protocol_name}.md"

    def get_protocol_json(self, protocol_name: str) -> Path:
        """Get the path to a protocol JSON file.

        Args:
            protocol_name: Name of the protocol

        Returns:
            Path: Path to the protocol JSON file
        """
        return self._stored_protocols_dir / f"{protocol_name}.json"

    def model_dump(self) -> Dict[str, Any]:
        """Get a dictionary representation of all paths."""
        return {
            "project_root": self.project_root,
            "ide_env": self.ide_env,
            "rules_file": self.rules_file,
            "global_rules_file": self.global_rules_file,
            "protocols_dir": self.protocols_dir,
            "stored_protocols_dir": self.stored_protocols_dir,
            "registry_file": self.registry_file,
            "markdown_files": self.markdown_files,
            "config_dir": self.config_dir,
            "cache_dir": self.cache_dir,
            "logs_dir": self.logs_dir,
            "env_file": self.env_file,
            "stored_context": self.stored_context,
        }

    def create_context_files(self) -> None:
        """Create the context directory and files if they don't exist."""
        try:
            # Create context directory
            context_dir = self.context_dir
            context_dir.mkdir(parents=True, exist_ok=True)

            # Create timestamp-based context directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            context_subdir = context_dir / f"context_{timestamp}"
            context_subdir.mkdir(parents=True, exist_ok=True)

            # Create the context files
            for file_name in [".architecture.md", ".progress.md", ".tasks.md"]:
                file_path = context_subdir / file_name
                if not file_path.exists():
                    file_path.touch()

            logger.debug("Created context files in %s", context_subdir)
        except Exception as e:
            logger.error("Failed to create context files: %s", e)
            raise


class FilePaths(BaseModel):
    """Base class for file paths."""

    architecture: Path = Field(default_factory=lambda: Path(MARKDOWN_FILES["architecture"]))
    progress: Path = Field(default_factory=lambda: Path(MARKDOWN_FILES["progress"]))
    tasks: Path = Field(default_factory=lambda: Path(MARKDOWN_FILES["tasks"]))


class SetupPaths(BaseModel):
    """Paths for project setup and configuration."""

    project_root: Path
    erasmus_dir: Path
    config_dir: Path
    cache_dir: Path
    logs_dir: Path
    rules_file: Path
    global_rules_file: Path
    architecture_file: Path
    progress_file: Path
    tasks_file: Path
    context_dir: Path
    protocols_dir: Path
    stored_protocols_dir: Path
    registry_file: Path
    markdown_files: Dict[str, Path]
    script_files: Dict[str, Path]
    env_file: Path
    _initialized: bool = False
    _env_manager: Optional[EnvironmentManager] = None

    @classmethod
    def with_project_root(cls, project_root: Path) -> "SetupPaths":
        """Create a SetupPaths instance with the given project root.

        Args:
            project_root: Path to the project root directory

        Returns:
            SetupPaths instance
        """
        # Initialize environment manager
        from erasmus.utils.env_manager import EnvironmentManager

        env_manager = EnvironmentManager()

        # Create instance
        instance = cls(
            project_root=project_root,
            erasmus_dir=project_root / ".erasmus",
            config_dir=project_root / ".erasmus" / "config",
            cache_dir=project_root / ".erasmus" / "cache",
            logs_dir=project_root / ".erasmus" / "logs",
            rules_file=project_root / RULES_FILES[env_manager.ide_env],
            global_rules_file=project_root / GLOBAL_RULES_PATHS[env_manager.ide_env],
            architecture_file=project_root / MARKDOWN_FILES["architecture"],
            progress_file=project_root / MARKDOWN_FILES["progress"],
            tasks_file=project_root / MARKDOWN_FILES["tasks"],
            context_dir=project_root / ".erasmus" / "context",
            protocols_dir=project_root / ".erasmus" / "protocols",
            stored_protocols_dir=project_root / ".erasmus" / "protocols" / "stored",
            registry_file=project_root / ".erasmus" / "protocols" / "registry.json",
            markdown_files=MARKDOWN_FILES,
            script_files=SCRIPT_FILES,
            env_file=project_root / ".env",
            _env_manager=env_manager,
        )

        return instance

    def __init__(self, **data):
        """Initialize the SetupPaths instance."""
        super().__init__(**data)
        if not self._initialized:
            self._initialized = True
            # Ensure context directory exists
            self.context_dir.mkdir(parents=True, exist_ok=True)

    @property
    def protocols_dir(self) -> Path:
        """Get the protocols directory path."""
        return self.project_root / DIRECTORIES["protocols"]

    @property
    def stored_protocols_dir(self) -> Path:
        """Get the stored protocols directory path."""
        return self.project_root / DIRECTORIES["stored_protocols"]

    @property
    def stored_context(self) -> Path:
        """Get the stored context directory path."""
        return self.context_dir

    @property
    def active_context(self) -> Path:
        """Get the active context directory path."""
        return self.context_dir

    @property
    def registry_file(self) -> Path:
        """Get the agent registry file path."""
        return self.protocols_dir / "agent_registry.json"

    @property
    def markdown_files(self) -> Dict[str, Path]:
        """Get all markdown file paths."""
        return {
            "architecture": self.architecture_file,
            "progress": self.progress_file,
            "tasks": self.tasks_file,
        }

    @property
    def script_files(self) -> Dict[str, Path]:
        """Get all script file paths."""
        return {
            "erasmus": self.project_root / SCRIPT_FILES["erasmus"],
        }

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.config_dir,
            self.cache_dir,
            self.logs_dir,
            self.protocols_dir,
            self.stored_protocols_dir,
            self.stored_context,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")

    def model_dump(self) -> Dict[str, Any]:
        """Get a dictionary representation of all paths."""
        return {
            "project_root": self.project_root,
            "rules_file": self.rules_file,
            "global_rules_file": self.global_rules_file,
            "config_dir": self.config_dir,
            "cache_dir": self.cache_dir,
            "logs_dir": self.logs_dir,
            "protocols_dir": self.protocols_dir,
            "stored_protocols_dir": self.stored_protocols_dir,
            "registry_file": self.registry_file,
            "markdown_files": self.markdown_files,
            "stored_context": self.stored_context,
        }
