"""Constants and configuration for path management."""

from pathlib import Path
from typing import Dict, Final

# File names
RULES_FILES: Final[Dict[str, str]] = {
    "windsurf": ".windsurfrules",
    "cursor": ".cursorrules",
}

# Directory names
DIRECTORIES: Final[Dict[str, str]] = {
    "config": ".erasmus",
    "cache": ".erasmus/cache",
    "logs": ".erasmus/logs",
    "protocols": ".erasmus/protocols",
    "stored_protocols": ".erasmus/protocols/stored",
    "stored_context": ".erasmus/context",
}

# Markdown files
MARKDOWN_FILES: Final[Dict[str, str]] = {
    "architecture": ".erasmus/architecture.md",
    "progress": ".erasmus/progress.md",
    "tasks": ".erasmus/tasks.md",
}

# Script files
SCRIPT_FILES: Final[Dict[str, str]] = {
    "erasmus": "erasmus.py",
}

# Global rules paths
GLOBAL_RULES_PATHS: Final[Dict[str, Path]] = {
    "windsurf": Path.home() / ".codeium" / "windsurf" / "memories" / "global_rules.md",
    "cursor": Path.cwd() / "global_rules.md",
}

# IDE markers
IDE_MARKERS: Final[Dict[str, list[Path]]] = {
    "windsurf": [
        Path.home() / ".codeium" / "windsurf",
    ],
    "cursor": [
        Path.home() / ".cursor",
    ],
}

# Default IDE environment
DEFAULT_IDE_ENV: Final[str] = "cursor"
