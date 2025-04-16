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

    def backup_rules(self):
        """Backup the current rules and global rules files to .bak files in the context directory."""
        if self.rules_file.exists():
            backup_path = self.context_dir / "rules.md.bak"
            shutil.copy2(self.rules_file, backup_path)
        if self.global_rules_file.exists():
            backup_path = self.context_dir / "global_rules.md.bak"
            shutil.copy2(self.global_rules_file, backup_path)

    def __init__(self, workspace_root: str | Path):
        """Initialize the context file handler.

        Args:
            workspace_root: Path to the workspace root directory
        """
        self.setup_paths = SetupPaths.with_project_root(workspace_root)
        self.workspace_root = Path(workspace_root)
        self.context_dir = self.workspace_root / ".erasmus"
        self.rules_file = self.context_dir / "rules.md"
        self.global_rules_file = self.context_dir / "global_rules.md"
        self.context_file = self.context_dir / "context.json"

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
        Raises:
            ContextValidationError: If the rules file is invalid or cannot be parsed
        """
        try:
            content = self.rules_file.read_text()
            rules = self._parse_markdown_rules(content)
            if not rules or not any(isinstance(v, (list, dict)) and v for v in rules.values()):
                raise ContextValidationError("Rules file is invalid or contains no valid sections.")
            return rules
        except FileNotFoundError:
            return {}
        except ContextValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to read rules file: {e}")
            raise ContextValidationError(f"Rules file parsing failed: {e}")

    def read_global_rules(self) -> dict[str, list[str] | dict[str, list[str]]]:
        """Read and parse the global rules file.

        Returns:
            Dict containing parsed global rules
        Raises:
            ContextValidationError: If the global rules file is invalid or cannot be parsed
        """
        try:
            content = self.global_rules_file.read_text()
            rules = self._parse_markdown_rules(content)
            if not rules or not any(isinstance(v, (list, dict)) and v for v in rules.values()):
                raise ContextValidationError("Global rules file is invalid or contains no valid sections.")
            return rules
        except FileNotFoundError:
            return {}
        except ContextValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to read global rules file: {e}")
            raise ContextValidationError(f"Global rules file parsing failed: {e}")

    def read_context(self) -> dict[str, Any]:
        """Read and parse the context file.

        Returns:
            Dict containing context configuration
        Raises:
            ContextValidationError: If the context file is invalid or cannot be parsed
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
            # Validate required fields
            required_fields = [
                "project_root",
                "active_rules",
                "global_rules",
                "file_patterns",
                "excluded_paths",
            ]
            missing = [field for field in required_fields if field not in context]
            if missing:
                raise ContextValidationError(f"Context file missing required fields: {missing}")
            return context

        except json.JSONDecodeError as e:
            raise ContextValidationError(f"Context file is invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to read context file: {e}")
            raise ContextValidationError(f"Context file parsing failed: {e}")

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
