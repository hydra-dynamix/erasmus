"""Path management for Erasmus project files."""

import os
from pathlib import Path

from pydantic import BaseModel, Field


class FilePaths(BaseModel):
    @classmethod
    def set_attribute(cls, name, value):
        if hasattr(cls, name):
            setattr(cls, name, value)
        else:
            raise AttributeError(f"{name} is not a valid attribute")

    @classmethod
    def model_dump(cls):
        """Base model_dump method to be overridden by subclasses."""
        return {}

    def items(self):
        """Return an items view of the model fields.

        This allows the class to be used like a dictionary in for loops.

        Returns:
            An items view of (key, value) pairs
        """
        return self.model_dump().items()

    def __str__(self):
        return str(self.model_dump())


class MarkdownPaths(FilePaths):
    architecture: Path = Field(
        default=Path().cwd() / "architecture.md",
        description="Architecture design document",
    )
    progress: Path = Field(
        default=Path().cwd() / "progress.md",
        description="Progress tracker for the project",
    )
    tasks: Path = Field(
        default=Path().cwd() / "tasks.md",
        description="Task tracker for the project",
    )

    def model_dump(self):
        base_dump = super().model_dump()
        return {
            **base_dump,
            "architecture": self.architecture,
            "progress": self.progress,
            "tasks": self.tasks,
        }


class RulesPaths(FilePaths):
    cursor: Path = Field(
        default=Path().cwd() / ".cursorrules",
        description="Cursor rules file",
    )
    cursor_global: Path = Field(
        default=Path().cwd() / "global_rules.md",
        description="Cursor global rules file",
    )
    windsurf: Path = Field(
        default=Path().cwd() / ".windsurfrules",
        description="Windsurf rules file",
    )
    windsurf_global: Path = Field(
        default=Path.home() / ".codeium" / "windsurf" / "memories" / "global_rules.md",
        description="Windsurf global rules file",
    )

    def get_rule_file(self) -> Path:
        from dotenv import load_dotenv

        load_dotenv()
        ide_env = os.getenv("IDE_ENV", "").lower()
        if ide_env.startswith("w"):
            return self.windsurf
        if ide_env.startswith("c"):
            return self.cursor
        return self.windsurf

    def get_global_rules_file(self) -> Path:
        from dotenv import load_dotenv

        load_dotenv()
        ide_env = os.getenv("IDE_ENV", "").lower()
        if ide_env.startswith("w"):
            return self.windsurf_global
        if ide_env.startswith("c"):
            return self.cursor_global
        return self.windsurf_global

    def model_dump(self):
        base_dump = super().model_dump()
        return {
            **base_dump,
            "cursor": self.cursor,
            "cursor_global": self.cursor_global,
            "windsurf": self.windsurf,
            "windsurf_global": self.windsurf_global,
        }


class ScriptPaths(FilePaths):
    script: Path = Field(
        default=Path().cwd() / "erasmus.py",
        description="Script file to watch",
    )

    def model_dump(self):
        base_dump = super().model_dump()
        return {
            **base_dump,
            "script": self.script,
        }


class SetupPaths(FilePaths):
    """Paths for project setup and configuration."""

    project_root: Path = Field(
        default=Path.cwd(),
        description="Root directory of the project",
    )
    config_dir: Path = Field(
        default=Path.cwd() / ".erasmus",
        description="Configuration directory",
    )
    cache_dir: Path = Field(
        default=Path.cwd() / ".erasmus" / "cache",
        description="Cache directory",
    )
    logs_dir: Path = Field(
        default=Path.cwd() / ".erasmus" / "logs",
        description="Logs directory",
    )
    protocols_dir: Path = Field(
        default=Path.cwd() / "erasmus" / "utils" / "protocols",
        description="Protocols directory",
    )
    env_file: Path = Field(
        default=Path.cwd() / ".env",
        description="Environment variables file",
    )
    markdown_files: MarkdownPaths = Field(
        default_factory=MarkdownPaths,
        description="Markdown file paths",
    )
    script_files: ScriptPaths = Field(
        default_factory=ScriptPaths,
        description="Script file paths",
    )
    stored_context: Path = Field(
        default=Path.cwd() / ".context",
        description="Path to the stored context file",
    )
    _rules_files: RulesPaths | None = None
    _rules_file: Path | None = None
    _global_rules_file: Path | None = None

    @classmethod
    def with_project_root(cls, project_root: Path | str) -> "SetupPaths":
        """Create a SetupPaths instance with a specific project root.

        Args:
            project_root: Path to the project root directory

        Returns:
            SetupPaths: Configured with the specified project root
        """
        instance = cls()
        instance.project_root = Path(project_root)
        return instance

    @property
    def rules_files(self) -> RulesPaths:
        """Get or initialize RulesPaths instance."""
        if self._rules_files is None:
            self._rules_files = RulesPaths()
        return self._rules_files

    @property
    def rules_file(self) -> Path:
        """Get the rules file path based on IDE environment."""
        if self._rules_file is None:
            self._rules_file = self.rules_files.get_rule_file()
        return self._rules_file

    @property
    def global_rules_file(self) -> Path:
        """Get the global rules file path based on IDE environment."""
        if self._global_rules_file is None:
            self._global_rules_file = self.rules_files.get_global_rules_file()
        return self._global_rules_file

    @property
    def all_watch_paths(self) -> dict[str, Path]:
        """Get all paths that should be watched."""
        return {
            **self.markdown_files.model_dump(),
            **self.script_files.model_dump(),
        }

    def model_dump(self):
        return {
            "rules_file": self.rules_file_path,
            "global_rules_file": self.global_rules_file_path,
            "project_root": self.project_root,
            "markdown_files": self.markdown_files.model_dump(),
            "script_files": self.script_files.model_dump(),
            "stored_context": self.stored_context,
        }
