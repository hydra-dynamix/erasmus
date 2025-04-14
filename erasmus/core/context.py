"""
Context Management System
======================

This module provides classes for managing context files and rules
in the Erasmus project.
"""

import json
import shutil
from pathlib import Path
from typing import Any

from erasmus.utils.paths import SetupPaths
from erasmus.utils.logging import get_logger

# Configure logging
logger = get_logger(__name__)


class ContextValidationError(Exception):
    """Raised when context file validation fails."""


class ContextFileHandler:
    """Handles reading, writing, and validation of context files."""

    def __init__(self, workspace_root: str | Path):
        """Initialize the context file handler.

        Args:
            workspace_root: Path to the workspace root directory
        """
        self.setup_paths = SetupPaths.with_project_root(workspace_root)
        self.workspace_root = Path(workspace_root)
        self.context_dir = self.workspace_root / ".erasmus" / "context"
        self.rules_file = self.setup_paths.rules_file
        self.global_rules_file = self.setup_paths.global_rules_file
        self.context_file = self.setup_paths.rules_file

        # Create context directory if it doesn't exist
        self.context_dir.mkdir(exist_ok=True)

    def _parse_markdown_rules(self, content: str) -> dict[str, list[str] | dict[str, list[str]]]:
        """Parse markdown content into a rules dictionary.

        Args:
            content: Markdown content to parse

        Returns:
            Dict containing parsed rules
        """
        rules: dict[str, list[str] | dict[str, list[str]]] = {}
        current_section = None
        current_subsection = None

        try:
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Title (#)
                if line.startswith("# "):
                    continue

                # Main section (##)
                if line.startswith("## "):
                    current_section = line[3:].strip()
                    current_subsection = None
                    rules[current_section] = []

                # Subsection (###)
                elif line.startswith("### "):
                    if current_section is not None:
                        current_subsection = line[4:].strip()
                        if isinstance(rules[current_section], list):
                            rules[current_section] = {}
                        rules[current_section][current_subsection] = []  # type: ignore

                # List item
                elif line.startswith("- "):
                    if current_section is not None:
                        item = line[2:].strip()
                        if current_subsection is None:
                            if isinstance(rules[current_section], list):
                                rules[current_section].append(item)  # type: ignore
                        else:
                            if isinstance(rules[current_section], dict):
                                rules[current_section][current_subsection].append(item)  # type: ignore

            return rules

        except Exception as e:
            logger.error(f"Failed to parse rules: {e}")
            return {}

    def read_rules(self) -> dict[str, list[str] | dict[str, list[str]]]:
        """Read and parse the project rules file.

        Returns:
            Dict containing parsed rules
        """
        try:
            content = self.rules_file.read_text()
            return self._parse_markdown_rules(content)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Failed to read rules file: {e}")
            return {}

    def read_global_rules(self) -> dict[str, list[str] | dict[str, list[str]]]:
        """Read and parse the global rules file.

        Returns:
            Dict containing parsed global rules
        """
        try:
            content = self.global_rules_file.read_text()
            return self._parse_markdown_rules(content)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Failed to read global rules file: {e}")
            return {}

    def read_context(self) -> dict[str, Any]:
        """Read and parse the context file.

        Returns:
            Dict containing context configuration
        """
        try:
            if not self.context_file.exists():
                return {
                    "project_root": str(self.workspace_root),
                    "active_rules": [],
                    "global_rules": [],
                    "file_patterns": ["*.py", "*.md"],
                    "excluded_paths": ["venv/", "__pycache__/"],
                }

            content = self.context_file.read_text()
            context = json.loads(content)
            return context

        except json.JSONDecodeError:
            # If JSON is invalid, return default context
            return {
                "project_root": str(self.workspace_root),
                "active_rules": [],
                "global_rules": [],
                "file_patterns": ["*.py", "*.md"],
                "excluded_paths": ["venv/", "__pycache__/"],
            }
        except Exception as e:
            logger.error(f"Failed to read context file: {e}")
            return {
                "project_root": str(self.workspace_root),
                "active_rules": [],
                "global_rules": [],
                "file_patterns": ["*.py", "*.md"],
                "excluded_paths": ["venv/", "__pycache__/"],
            }

    def update_context(self, new_context: dict[str, Any], partial: bool = False) -> None:
        """Update the context file.

        Args:
            new_context: New context configuration
            partial: If True, only update specified fields
        """
        try:
            if partial:
                current_context = self.read_context()
                current_context.update(new_context)
                new_context = current_context

            # Write the updated context
            self.context_file.write_text(json.dumps(new_context, indent=2))
        except Exception as e:
            logger.error(f"Failed to update context: {e}")

    def backup_rules(self) -> None:
        """Create backups of rules files.

        Creates .bak files for both rules.md and global_rules.md if they exist.
        """
        try:
            if self.rules_file.exists():
                shutil.copy2(self.rules_file, self.rules_file.with_suffix(".md.bak"))

            if self.global_rules_file.exists():
                shutil.copy2(self.global_rules_file, self.global_rules_file.with_suffix(".md.bak"))

        except Exception as e:
            raise ContextValidationError(f"Failed to create backups: {e!s}")
