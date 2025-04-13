"""Path management for Erasmus project files."""

import os
from pathlib import Path
import logging
from typing import Dict, Any, Optional, ClassVar
import shutil

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
        self._setup_paths = SetupPaths.with_project_root(self.project_root)
        self._ide_env = self._detect_ide_environment()

    def _detect_ide_environment(self) -> str:
        """Detect the current IDE environment.

        Returns:
            str: The detected IDE environment ('windsurf' or 'cursor')
        """
        # Check environment variable first
        ide_env = os.getenv("IDE_ENV", "").lower()
        if ide_env:
            if ide_env.startswith("w"):
                return "windsurf"
            if ide_env.startswith("c"):
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

        # Simple direct mapping based on IDE_ENV
        if ide_env == "windsurf" or ide_env.startswith("w"):
            return Path.cwd() / ".windsurfrules"
        if ide_env == "cursor" or ide_env.startswith("c"):
            return Path.cwd() / ".cursorrules"

        # Default to cursor if IDE_ENV is not set or is empty
        return Path.cwd() / ".cursorrules"

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
        return Path("erasmus/utils/protocols/agent_registry.json")

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


class FilePaths(BaseModel):
    """Base class for file paths."""

    architecture: Path = Field(default_factory=lambda: Path(MARKDOWN_FILES["architecture"]))
    progress: Path = Field(default_factory=lambda: Path(MARKDOWN_FILES["progress"]))
    tasks: Path = Field(default_factory=lambda: Path(MARKDOWN_FILES["tasks"]))


class SetupPaths(BaseModel):
    """Paths for project setup and configuration."""

    project_root: Path
    config_dir: Path
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
        context_dir = project_root / ".context"

        # Ensure context directory exists
        context_dir.mkdir(parents=True, exist_ok=True)

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
        rules_file = RULES_FILES[ide_env]
        rules_file_path = project_root / rules_file
        global_rules_path = GLOBAL_RULES_PATHS[ide_env]

        return cls(
            project_root=project_root,
            config_dir=context_dir,
            rules_file=rules_file_path,
            global_rules_file=global_rules_path,
            architecture_file=project_root / MARKDOWN_FILES["architecture"],
            progress_file=project_root / MARKDOWN_FILES["progress"],
            tasks_file=project_root / MARKDOWN_FILES["tasks"],
            context_dir=context_dir,
            _initialized=True,
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
        return Path("erasmus/utils/protocols/agent_registry.json")

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
