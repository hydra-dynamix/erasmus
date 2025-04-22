from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from dotenv import load_dotenv
from enum import Enum
import os
from typing import NamedTuple

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

    # Templates
    architecture_template: Path = Field(
        default_factory=lambda: Path.cwd() / ".erasmus" / "templates" / "architecture.xml"
    )
    progress_template: Path = Field(
        default_factory=lambda: Path.cwd() / ".erasmus" / "templates" / "progress.xml"
    )
    tasks_template: Path = Field(
        default_factory=lambda: Path.cwd() / ".erasmus" / "templates" / "tasks.xml"
    )
    protocol_template: Path = Field(
        default_factory=lambda: Path.cwd() / ".erasmus" / "templates" / "protocol.xml"
    )
    meta_agent_template: Path = Field(
        default_factory=lambda: Path.cwd() / ".erasmus" / "templates" / "meta_agent.xml"
    )
    meta_rules_template: Path = Field(
        default_factory=lambda: Path.cwd() / ".erasmus" / "templates" / "meta_rules.xml"
    )

    def __init__(self, **data):
        """Initialize the PathMngrModel with optional configuration data.

        Args:
            **data: Keyword arguments for configuring path management.
                    Supports IDE-specific and custom path configurations.
        """
        super().__init__(**data)
        # Initialize and time path setup
        self._setup_paths()

    def _setup_paths(self):
        """Set up and configure paths for the current development environment.

        This method handles:
        - Detecting the current IDE
        - Creating necessary directories
        - Setting up symlinks
        - Ensuring cross-platform path compatibility
        """
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

    def ensure_dirs(self) -> None:
        """Ensure all directories exist."""
        self.context_dir.mkdir(parents=True, exist_ok=True)
        self.protocol_dir.mkdir(parents=True, exist_ok=True)
        self.erasmus_dir.mkdir(parents=True, exist_ok=True)
        self.template_dir.mkdir(parents=True, exist_ok=True)

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
