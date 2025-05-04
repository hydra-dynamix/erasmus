from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from dotenv import load_dotenv
from enum import Enum
import os
from typing import NamedTuple, List, Optional, Tuple
from loguru import logger
from erasmus.utils.warp_integration import WarpIntegration, WarpRule

load_dotenv()


class IDEMetadata(NamedTuple):
    """Metadata for an IDE environment."""
    name: str
    rules_file: str
    global_rules_path: Path
    mcp_config_path: Path


class IDE(Enum):
    """IDE environment with associated metadata."""

    windsurf = IDEMetadata(
        name="windsurf",
        rules_file=".windsurfrules",
        global_rules_path=Path.home() / ".codeium" / "windsurf" / "memories" / "global_rules.md",
        mcp_config_path= Path.home() / '.codeium' / 'windsurf' / 'mcp_config.json',
    )

    cursor = IDEMetadata(
        name="cursor",
        rules_file=".cursorrules",
        global_rules_path=Path.cwd() / ".cursor" / "global_rules.md",
        mcp_config_path= Path.home() / '.cursor' / 'mcp.json',
    )

    codex = IDEMetadata(
        name="codex",
        rules_file=".codex.md",
        global_rules_path=Path.home() / ".codex" / "instructions.md",
        mcp_config_path= Path.home() / '.codex' / 'mcp.json',
    )

    claude = IDEMetadata(
        name="claude",
        rules_file="CLAUDE.md",
        global_rules_path=Path.home() / ".claude" / "CLAUDE.md",
        mcp_config_path= Path.home() / '.claude' / 'mcp.json',
    )

    warp = IDEMetadata(
        name="warp",
        rules_file="warp.sqlite",
        global_rules_path=Path(os.environ["LOCALAPPDATA"]) / "Warp/Warp/data/warp.sqlite" if os.name == "nt"
        else Path("/mnt/c/Users/richa/AppData/Local/Warp/Warp/data/warp.sqlite"),
        mcp_config_path= Path.home() / '.warp' / 'mcp.json',
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

    @property
    def mcp_config_path(self) -> Path:
        """Get the MCP configuration path for this IDE."""
        return self.metadata.mcp_config_path


def detect_ide_from_env() -> IDE | None:
    """Detect IDE from environment variables."""
    if "VSCODE_REMOTE" in os.environ or "REMOTE_CONTAINERS" in os.environ:
        return prompt_for_ide()

    load_dotenv()
    ide_env = os.environ.get("IDE_ENV")

    if not ide_env:
        ide_env = prompt_for_ide().name

    # Updated to include Warp
    if ide_env.startswith("wa"):
        return IDE.warp
    elif ide_env.startswith("w"):
        return IDE.windsurf
    elif ide_env.startswith("cu"):
        return IDE.cursor
    elif ide_env.startswith("co"):
        return IDE.codex
    elif ide_env.startswith("cl"):
        return IDE.claude

    return prompt_for_ide()


def prompt_for_ide() -> IDE:
    """Prompt the user to select an IDE."""
    load_dotenv()
    if os.getenv("IDE_ENV"):
        return IDE[os.getenv("IDE_ENV")]
    print("No IDE environment detected. Please select an IDE:")
    print("1. Windsurf")
    print("2. Cursor")
    print("3. Codex")
    print("4. Claude")
    print("5. Warp")

    while True:
        try:
            choice = input("Enter your choice (1-5): ")
            if choice == "1":
                ide_env = IDE.windsurf
            elif choice == "2":
                ide_env = IDE.cursor
            elif choice == "3":
                ide_env = IDE.codex
            elif choice == "4":
                ide_env = IDE.claude
            elif choice == "5":
                ide_env = IDE.warp
            else:
                print("Invalid choice. Please enter a number between 1 and 5.")
            if ide_env:
                ide_path = Path.cwd() / ".env"
                ide_path.write_text(f"IDE_ENV={ide_env.name}")
                return ide_env
                
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled or input closed. Using default IDE (Cursor).")
            return prompt_for_ide()


def get_ide() -> IDE:
    """Get the IDE from environment variables or prompt the user."""
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

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    ide: IDE | None = None
    warp_integration: WarpIntegration | None = None
    
    # [Previous attributes remain unchanged]
    root_dir: Path = Field(default_factory=lambda: Path.cwd())
    context_file: Path = Field(default_factory=lambda: Path.cwd() / ".ctx")
    erasmus_dir: Path = Field(default_factory=lambda: Path.cwd() / ".erasmus")
    context_dir: Path = Field(default_factory=lambda: Path.cwd() / ".erasmus" / "context")
    protocol_dir: Path = Field(default_factory=lambda: Path.cwd() / ".erasmus" / "protocol")
    template_dir: Path = Field(default_factory=lambda: Path.cwd() / ".erasmus" / "templates")
    log_dir: Path = Field(default_factory=lambda: Path.cwd() / ".erasmus" / "logs")

    # Files
    architecture_file: Path = Field(default_factory=lambda: Path.cwd() / ".ctx.architecture.md")
    progress_file: Path = Field(default_factory=lambda: Path.cwd() / ".ctx.progress.md")
    tasks_file: Path = Field(default_factory=lambda: Path.cwd() / ".ctx.tasks.md")
    rules_file: Path | None = None
    global_rules_file: Path | None = None

    # Templates
    architecture_template: Path = Field(
        default_factory=lambda: Path.cwd() / ".erasmus" / "templates" / "architecture.md"
    )
    progress_template: Path = Field(
        default_factory=lambda: Path.cwd() / ".erasmus" / "templates" / "progress.md"
    )
    tasks_template: Path = Field(
        default_factory=lambda: Path.cwd() / ".erasmus" / "templates" / "tasks.md"
    )
    protocol_template: Path = Field(
        default_factory=lambda: Path.cwd() / ".erasmus" / "templates" / "protocol.md"
    )
    meta_agent_template: Path = Field(
        default_factory=lambda: Path.cwd() / ".erasmus" / "templates" / "meta_agent.md"
    )
    meta_rules_template: Path = Field(
        default_factory=lambda: Path.cwd() / ".erasmus" / "templates" / "meta_rules.md"
    )
    check_binary_script: Path = Field(
        default_factory=lambda: Path.cwd() / '.erasmus' / 'servers' / 'github' / 'check_binary.sh'
    )

    def __init__(self, **data):
        """Initialize the PathMngrModel with optional configuration data."""
        super().__init__(**data)
        if self.ide == IDE.warp:
            self.warp_integration = WarpIntegration()
        self._setup_paths()

    def _setup_paths(self):
        """Set up paths based on the selected IDE."""
        if self.ide:
            self.rules_file = self.root_dir / self.ide.rules_file
            self.global_rules_file = self.ide.global_rules_path

            if self.ide == IDE.windsurf:
                cursor_rules = self.root_dir / ".cursorrules"
                if self.rules_file.exists() and not cursor_rules.exists():
                    cursor_rules.symlink_to(self.rules_file)

    def update_warp_rules(self, document_type: str, document_id: str, rule: str) -> bool:
        """Update rules in Warp's database if IDE is set to Warp."""
        if self.ide != IDE.warp or not self.warp_integration:
            return False

        try:
            rule_obj = WarpRule(
                document_type=document_type,
                document_id=document_id,
                rule=rule
            )
            self.warp_integration.update_rule(rule_obj)
            return True
        except Exception as e:
            logger.error(f"Failed to update Warp rules: {e}")
            return False

    def get_warp_rules(self) -> List[Tuple[str, str, str]] | None:
        """Retrieve rules from Warp's database if IDE is set to Warp."""
        if self.ide != IDE.warp or not self.warp_integration:
            return None

        try:
            rules = self.warp_integration.get_rules()
            return [(rule.document_type, rule.document_id, rule.rule) for rule in rules]
        except Exception as e:
            logger.error(f"Failed to retrieve Warp rules: {e}")
            return None

    # [Previous methods remain unchanged]
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

    def get_context_file(self) -> Path:
        """Get the context file path."""
        return self.context_file

    def link_rules_file(self) -> None:
        """Detect IDE and link .ctx to rules file"""
        self.rules_file.symlink_to(self.context_file)

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

    def get_log_dir(self) -> Path:
        """Get the log directory path."""
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True, exist_ok=True)
        return self.log_dir


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
