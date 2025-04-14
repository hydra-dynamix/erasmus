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
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self._ide_env = self._detect_ide_environment()
        self._setup_paths = None  # Will be initialized in _migrate_files
        self._migrate_files()

    def _migrate_files(self) -> None:
        """Migrate existing files to the new .erasmus directory structure."""
        try:
            # Create .erasmus directory if it doesn't exist
            erasmus_dir = self.project_root / ".erasmus"
            erasmus_dir.mkdir(exist_ok=True)

            # Create protocol directories in .erasmus (but don't copy files)
            new_protocols_dir = erasmus_dir / "protocols"
            new_protocols_dir.mkdir(exist_ok=True)
            (new_protocols_dir / "stored").mkdir(exist_ok=True)

            # Create a symlink to the original protocols directory
            original_protocols_dir = self.project_root / "erasmus/utils/protocols"
            if original_protocols_dir.exists():
                # Create symlink for stored protocols
                stored_link = new_protocols_dir / "stored"
                if not stored_link.exists():
                    stored_link.symlink_to(
                        original_protocols_dir / "stored", target_is_directory=True
                    )

                # Copy only the registry file (since it might be modified)
                registry_file = original_protocols_dir / "agent_registry.json"
                if registry_file.exists():
                    shutil.copy2(registry_file, new_protocols_dir / "agent_registry.json")

            # Migrate markdown files
            for file_name in MARKDOWN_FILES.values():
                old_file = self.project_root / file_name
                if old_file.exists():
                    # Create the target directory if it doesn't exist
                    target_file = erasmus_dir / file_name

                    # Ensure the parent directory exists
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    # Copy the file
                    shutil.copy2(old_file, target_file)
                    logger.info(f"Migrated {file_name} to {target_file}")

            # Initialize SetupPaths after migration
            self._setup_paths = SetupPaths.with_project_root(self.project_root)

            logger.info("Successfully migrated files to .erasmus directory")
        except Exception as e:
            logger.error(f"Error migrating files: {e}")
            raise

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        try:
            # Create .erasmus directory
            erasmus_dir = self.project_root / ".erasmus"
            erasmus_dir.mkdir(exist_ok=True)

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
                return "windsurf"

        # Check cursor markers
        for marker in cursor_markers:
            if marker.exists():
                return "cursor"

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
        return self._setup_paths.global_rules_file

    @property
    def protocols_dir(self) -> Path:
        """Get the protocols directory path."""
        return self._setup_paths.protocols_dir

    @property
    def stored_protocols_dir(self) -> Path:
        """Get the stored protocols directory path."""
        return self.protocols_dir / "stored"

    @property
    def registry_file(self) -> Path:
        """Get the agent registry file path."""
        return self.protocols_dir / "agent_registry.json"

    @property
    def markdown_files(self) -> Dict[str, Path]:
        """Get all markdown file paths."""
        return self._setup_paths.markdown_files.model_dump()

    @property
    def config_dir(self) -> Path:
        """Get the configuration directory path."""
        return self._setup_paths.config_dir

    @property
    def cache_dir(self) -> Path:
        """Get the cache directory path."""
        return self._setup_paths.cache_dir

    @property
    def logs_dir(self) -> Path:
        """Get the logs directory path."""
        return self._setup_paths.logs_dir

    @property
    def env_file(self) -> Path:
        """Get the environment file path."""
        return self._setup_paths.env_file

    @property
    def stored_context(self) -> Path:
        """Get the stored context directory path."""
        return self._setup_paths.stored_context

    def get_protocol_file(self, protocol_name: str) -> Path:
        """Get the path to a protocol file.

        Args:
            protocol_name: Name of the protocol

        Returns:
            Path: Path to the protocol file
        """
        return self.stored_protocols_dir / f"{protocol_name}.md"

    def get_protocol_json(self, protocol_name: str) -> Path:
        """Get the path to a protocol JSON file.

        Args:
            protocol_name: Name of the protocol

        Returns:
            Path: Path to the protocol JSON file
        """
        return self.stored_protocols_dir / f"{protocol_name}.json"

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
    config_dir: Path
    cache_dir: Path
    logs_dir: Path
    rules_file: Path
    global_rules_file: Path
    architecture_file: Path
    progress_file: Path
    tasks_file: Path
    context_dir: Path
    _initialized: bool = False

    @classmethod
    def with_project_root(cls, project_root: Path) -> "SetupPaths":
        """Create a new SetupPaths instance with the given project root."""
        config_dir = project_root / DIRECTORIES["config"]
        cache_dir = project_root / DIRECTORIES["cache"]
        logs_dir = project_root / DIRECTORIES["logs"]
        context_dir = project_root / DIRECTORIES["stored_context"]

        # Ensure directories exist
        for directory in [config_dir, cache_dir, logs_dir, context_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Create script files if they don't exist
        for script_name, script_path in SCRIPT_FILES.items():
            script_file = project_root / script_path
            if not script_file.exists():
                script_file.touch()
                # Make the script executable
                script_file.chmod(0o755)

        # Get the rules file path based on IDE environment
        env_manager = EnvironmentManager()
        ide_env = env_manager.ide_env

        # Map to the correct key for RULES_FILES dictionary
        if ide_env == "windsurf" or ide_env.startswith("w"):
            ide_key = "windsurf"
        elif ide_env == "cursor" or ide_env.startswith("c"):
            ide_key = "cursor"
        else:
            ide_key = DEFAULT_IDE_ENV  # Default to cursor

        rules_file = RULES_FILES[ide_key]
        rules_file_path = project_root / rules_file
        global_rules_path = GLOBAL_RULES_PATHS[ide_key]

        # Create the rules file if it doesn't exist
        if not rules_file_path.exists():
            rules_file_path.touch()

        # Get the actual markdown files from the project root
        architecture_file = project_root / MARKDOWN_FILES["architecture"]
        progress_file = project_root / MARKDOWN_FILES["progress"]
        tasks_file = project_root / MARKDOWN_FILES["tasks"]

        return cls(
            project_root=project_root,
            config_dir=config_dir,
            cache_dir=cache_dir,
            logs_dir=logs_dir,
            rules_file=rules_file_path,
            global_rules_file=global_rules_path,
            architecture_file=architecture_file,
            progress_file=progress_file,
            tasks_file=tasks_file,
            context_dir=context_dir,
        )

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
