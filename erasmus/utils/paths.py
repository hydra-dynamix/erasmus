"""Path management for Erasmus project files."""

import os
from pathlib import Path
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

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


class PathManager(BaseModel):
    """Manages paths for the Erasmus project."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    project_root: Path
    env_manager: EnvironmentManager = Field(default_factory=EnvironmentManager)

    # Core directories with public names
    erasmus_dir: Optional[Path] = None
    config_dir: Optional[Path] = None
    cache_dir: Optional[Path] = None
    logs_dir: Optional[Path] = None
    context_dir: Optional[Path] = None
    protocols_dir: Optional[Path] = None
    stored_protocols_dir: Optional[Path] = None
    registry_file: Optional[Path] = None
    rules_file: Optional[Path] = None
    global_rules_file: Optional[Path] = None
    env_file: Optional[Path] = None

    def __init__(self, project_root: Path, **kwargs):
        """Initialize the PathManager.

        Args:
            project_root: Path to the project root directory
            **kwargs: Additional path overrides
        """
        super().__init__(project_root=project_root, **kwargs)
        self.ensure_directories()

    @property
    def default_erasmus_dir(self) -> Path:
        """Get the default erasmus directory."""
        return self.project_root / ".erasmus"

    @property
    def default_config_dir(self) -> Path:
        """Get the default config directory."""
        return self.erasmus_dir or self.default_erasmus_dir / "config"

    @property
    def default_cache_dir(self) -> Path:
        """Get the default cache directory."""
        return self.erasmus_dir or self.default_erasmus_dir / "cache"

    @property
    def default_logs_dir(self) -> Path:
        """Get the default logs directory."""
        return self.erasmus_dir or self.default_erasmus_dir / "logs"

    @property
    def default_context_dir(self) -> Path:
        """Get the default context directory."""
        return self.erasmus_dir or self.default_erasmus_dir / "context"

    @property
    def default_protocols_dir(self) -> Path:
        """Get the default protocols directory."""
        return self.erasmus_dir or self.default_erasmus_dir / "protocols"

    @property
    def default_stored_protocols_dir(self) -> Path:
        """Get the default stored protocols directory."""
        return self.protocols_dir or self.default_protocols_dir / "stored"

    @property
    def default_registry_file(self) -> Path:
        """Get the default registry file."""
        return self.protocols_dir or self.default_protocols_dir / "agent_registry.json"

    @property
    def default_rules_file(self) -> Path:
        """Get the default rules file."""
        return self.project_root / f".{self.env_manager.ide_env}rules"

    @property
    def default_global_rules_file(self) -> Path:
        """Get the default global rules file."""
        return self.project_root / f".{self.env_manager.ide_env}rules.global"

    @property
    def default_env_file(self) -> Path:
        """Get the default environment file."""
        return self.project_root / ".env"

    @property
    def markdown_files(self) -> Dict[str, Path]:
        """Get root-level markdown file paths."""
        return {
            "architecture": self.project_root / ".architecture.md",
            "progress": self.project_root / ".progress.md",
            "tasks": self.project_root / ".tasks.md",
        }

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.erasmus_dir or self.default_erasmus_dir,
            self.config_dir or self.default_config_dir,
            self.cache_dir or self.default_cache_dir,
            self.logs_dir or self.default_logs_dir,
            self.context_dir or self.default_context_dir,
            self.protocols_dir or self.default_protocols_dir,
            self.stored_protocols_dir or self.default_stored_protocols_dir,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def create_context_files(self) -> None:
        """Create the context directory and files if they don't exist."""
        try:
            # Create context directory
            context_dir = self.context_dir or self.default_context_dir
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

    def get_protocol_file(self, protocol_name: str) -> Path:
        """Get the path to a protocol file.

        Args:
            protocol_name: Name of the protocol

        Returns:
            Path: Path to the protocol file
        """
        return (
            self.stored_protocols_dir or self.default_stored_protocols_dir
        ) / f"{protocol_name}.md"

    def get_protocol_json(self, protocol_name: str) -> Path:
        """Get the path to a protocol JSON file.

        Args:
            protocol_name: Name of the protocol

        Returns:
            Path: Path to the protocol JSON file
        """
        return (
            self.stored_protocols_dir or self.default_stored_protocols_dir
        ) / f"{protocol_name}.json"

    def model_dump(self) -> Dict[str, Any]:
        """Get a dictionary representation of all paths."""
        return {
            "project_root": self.project_root,
            "erasmus_dir": self.erasmus_dir or self.default_erasmus_dir,
            "config_dir": self.config_dir or self.default_config_dir,
            "cache_dir": self.cache_dir or self.default_cache_dir,
            "logs_dir": self.logs_dir or self.default_logs_dir,
            "context_dir": self.context_dir or self.default_context_dir,
            "protocols_dir": self.protocols_dir or self.default_protocols_dir,
            "stored_protocols_dir": self.stored_protocols_dir or self.default_stored_protocols_dir,
            "registry_file": self.registry_file or self.default_registry_file,
            "rules_file": self.rules_file or self.default_rules_file,
            "global_rules_file": self.global_rules_file or self.default_global_rules_file,
            "env_file": self.env_file or self.default_env_file,
            "markdown_files": self.markdown_files,
        }
