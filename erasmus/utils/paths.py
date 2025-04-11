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
    """Manages paths for project files and watchers."""

    @classmethod
    def with_project_root(cls, project_root: Path | str) -> 'SetupPaths':
        """Create a SetupPaths instance with a specific project root.

        Args:
            project_root: Path to the project root directory

        Returns:
            SetupPaths: Configured with the specified project root
        """
        instance = cls()
        instance.project_root = Path(project_root)
        return instance

    rules_file_path: Path = Field(
        default=Path().cwd() / ".windsurfrules",
        description="Rules file path",
    )
    project_root: Path = Field(
        default=Path().cwd(),
        description="Root of the directory",
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

    @property
    def rules_file(self) -> Path:
        """Get the rules file path based on IDE environment."""
        from erasmus.utils.logging import get_logger
        logger = get_logger(__name__)

        # Load .env file directly to ensure environment variables are up to date
        from dotenv import load_dotenv
        load_dotenv()

        ide_env = os.getenv("IDE_ENV", "").lower()
        logger.info(f"Detected IDE environment: '{ide_env}'")

        windsurf_rules = self.project_root / ".windsurfrules"
        cursor_rules = self.project_root / ".cursorrules"
        # First check if .windsurfrules exists - if it does, use it regardless of IDE_ENV
        if windsurf_rules.exists():
            logger.info(".windsurfrules exists, using Windsurf rules")
            self.rules_file_path = windsurf_rules
        # Then check IDE_ENV if .windsurfrules doesn't exist
        elif ide_env.startswith("w"):
            logger.info("Using Windsurf rules file at %s based on IDE_ENV", windsurf_rules)
            self.rules_file_path = windsurf_rules
        elif ide_env.startswith("c"):
            logger.info("Using Cursor rules file at %s based on IDE_ENV", cursor_rules)
            self.rules_file_path = cursor_rules
        else:
            logger.info("Using default Cursor rules file at %s", cursor_rules)
            self.rules_file_path = cursor_rules  # Default

        return self.rules_file_path

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
            "project_root": self.project_root,
            "markdown_files": self.markdown_files.model_dump(),
            "script_files": self.script_files.model_dump(),
        }

    def validate_paths(self) -> None:
        """Validate that required files exist.

        Raises:
            FileNotFoundError: If a required file is missing
        """
        for name, path in self.markdown_files.items():
            if not path.exists():
                raise FileNotFoundError(f"Required file {name} not found at {path}")

        for name, path in self.script_files.items():
            if not path.exists():
                raise FileNotFoundError(f"Required file {name} not found at {path}")
