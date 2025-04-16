"""Rules management module."""

import json
import logging
import ast
from pathlib import Path
from typing import Set, Dict, Any

from erasmus.utils.paths import SetupPaths

logger = logging.getLogger(__name__)


class RuleValidationError(Exception):
    """Exception raised for rule validation errors."""

    pass


class Rule:
    """Represents a single rule."""

    def __init__(self, description: str, category: str, subcategory: str | None = None, is_global: bool = False):
        if not category or not category.strip():
            raise RuleValidationError("Rule category must not be empty.")
        self.description = description
        # If category contains a subcategory, split it unless subcategory is provided
        if subcategory is None and "/" in category:
            main_cat, subcat = category.split("/", 1)
            self.category = main_cat.strip()
            self.subcategory = subcat.strip()
        else:
            self.category = category
            self.subcategory = subcategory
        self.is_global = is_global

    def __eq__(self, other):
        if not isinstance(other, Rule):
            return False
        return (
            self.description == other.description and
            self.category == other.category and
            self.subcategory == other.subcategory and
            self.is_global == other.is_global
        )

    def __hash__(self):
        return hash((self.description, self.category, self.subcategory, self.is_global))


class RulesManager:
    """Manages project and global rules."""

    def __init__(self, workspace_root: Path):
        """Initialize the rules manager.

        Args:
            workspace_root: Path to the project workspace root
        """
        self.workspace_root = Path(workspace_root)
        self.setup_paths = SetupPaths.with_project_root(workspace_root)
        self.rules_dir = self.workspace_root / ".erasmus"
        self.project_rules_file = self.rules_dir / "rules.md"
        self.global_rules_file = self.rules_dir / "global_rules.md"
        self.active_rules: set[Rule] = set()
        self._seen_rules: set[str] = set()  # Track rules by their unique key
        self._conflicting_patterns = [
            (r"use\s+spaces\s+for\s+indentation", r"use\s+tabs\s+for\s+indentation"),
            # Add more conflicting patterns as needed
        ]

    def _rule_key(self, rule: Rule) -> str:
        """Generate a unique key for a rule."""
        return f"{rule.category.lower()}:{rule.description.lower()}"

    def add_rule(self, rule: Rule) -> bool:
        """Add a rule if it doesn't conflict with existing rules."""
        key = self._rule_key(rule)
        if key in self._seen_rules:
            return False

        # Check for conflicts
        for pattern1, pattern2 in self._conflicting_patterns:
            if pattern1 in rule.description.lower() and any(
                pattern2 in r.description.lower() for r in self.active_rules
            ):
                return False
            if pattern2 in rule.description.lower() and any(
                pattern1 in r.description.lower() for r in self.active_rules
            ):
                return False

        self.active_rules.add(rule)
        self._seen_rules.add(key)
        return True

    def _check_conflicting_rules(self, rules: list[Rule]) -> None:
        """Check for duplicate and conflicting rules in a list. Raises if conflicts found."""
        seen = set()
        for rule in rules:
            key = (rule.category.lower(), rule.description.lower())
            if key in seen:
                raise RuleValidationError(f"Duplicate rule in category '{rule.category}': {rule.description}")
            seen.add(key)
        # Check for known conflicting patterns (e.g., indentation)
        descriptions = [r.description.lower() for r in rules]
        if any("spaces for indentation" in d for d in descriptions) and any("tabs for indentation" in d for d in descriptions):
            raise RuleValidationError("Conflicting rules: 'spaces for indentation' and 'tabs for indentation'")

    def remove_rule(self, rule: Rule) -> bool:
        """Remove a rule if it exists."""
        key = self._rule_key(rule)
        if key in self._seen_rules:
            self.active_rules.remove(rule)
            self._seen_rules.remove(key)
            return True
        return False

    def get_rules(self) -> Set[Rule]:
        """Get all active rules."""
        return self.active_rules.copy()

    def save_rules(self) -> None:
        """Save rules to the appropriate files."""
        try:
            # Save to project rules file
            rules_data = {
                "rules": [
                    {"category": r.category, "description": r.description}
                    for r in self.active_rules
                ]
            }
            with open(self.project_rules_file, "w") as f:
                json.dump(rules_data, f, indent=2)
            logger.info(f"Saved rules to {self.project_rules_file}")

            # Save to global rules file
            with open(self.global_rules_file, "w") as f:
                json.dump(rules_data, f, indent=2)
            logger.info(f"Saved rules to {self.global_rules_file}")

        except Exception as e:
            logger.exception(f"Failed to save rules: {e}")
            raise

    def load_rules(self) -> None:
        """Load rules from the appropriate files."""
        self.active_rules.clear()
        self._seen_rules.clear()
        try:
            loaded_any = False
            # Load project rules first
            if self.project_rules_file.exists():
                with open(self.project_rules_file) as f:
                    content = f.read()
                    if not content.strip():
                        data = {"rules": []}
                        self._load_rules_from_data(data)
                        loaded_any = True
                    elif content.lstrip().startswith("{"):
                        data = json.loads(content)
                        self._load_rules_from_data(data)
                        loaded_any = True
                    elif content.lstrip().startswith("#"):
                        rules = self.parse_rules(self.project_rules_file)
                        for rule in rules:
                            self.add_rule(rule)
                        loaded_any = True
                    else:
                        raise RuleValidationError("Unknown rules file format.")

            # Always try to merge in global rules if present
            if self.global_rules_file.exists():
                with open(self.global_rules_file) as f:
                    content = f.read()
                    if not content.strip():
                        pass  # No global rules
                    elif content.lstrip().startswith("{"):
                        data = json.loads(content)
                        for rule_data in data.get("rules", []):
                            rule = Rule(category=rule_data["category"], description=rule_data["description"], is_global=True)
                            # Only add if not already present as a project rule
                            if not any(r.category == rule.category and r.description == rule.description and not r.is_global for r in self.active_rules):
                                self.add_rule(rule)
                    elif content.lstrip().startswith("#"):
                        rules = self.parse_rules(self.global_rules_file, is_global=True)
                        for rule in rules:
                            if not any(r.category == rule.category and r.description == rule.description and not r.is_global for r in self.active_rules):
                                self.add_rule(rule)
                    else:
                        raise RuleValidationError("Unknown rules file format.")

            if not loaded_any and not self.global_rules_file.exists():
                logger.warning("No rules files found")

            # Post-process: for each (category, description), keep only the project rule if present
            unique = {}
            for rule in self.active_rules:
                key = (rule.category, rule.description)
                if key not in unique or (unique[key].is_global and not rule.is_global):
                    unique[key] = rule
            filtered = set(unique.values())

            # Remove global conflicting rules if a project rule for the other side exists
            # Currently only handles indentation conflict
            def is_spaces(rule):
                return "spaces for indentation" in rule.description.lower()
            def is_tabs(rule):
                return "tabs for indentation" in rule.description.lower()
            by_cat = {}
            for rule in filtered:
                by_cat.setdefault(rule.category, []).append(rule)
            final = set(filtered)
            for cat, rules in by_cat.items():
                project_spaces = any(is_spaces(r) and not r.is_global for r in rules)
                project_tabs = any(is_tabs(r) and not r.is_global for r in rules)
                # If project rule for one side exists, remove global rule for the other
                for r in rules:
                    if r.is_global:
                        if (is_spaces(r) and project_tabs) or (is_tabs(r) and project_spaces):
                            final.discard(r)
            self.active_rules = final
        except Exception as e:
            logger.exception(f"Failed to load rules: {e}")
            raise

    def _load_rules_from_data(self, data: Dict[str, Any]) -> None:
        """Load rules from a data dictionary."""
        self.active_rules.clear()
        self._seen_rules.clear()

        for rule_data in data.get("rules", []):
            rule = Rule(category=rule_data["category"], description=rule_data["description"])
            self.add_rule(rule)

    def parse_rules(self, rules_path: Path, is_global: bool = False) -> list[Rule]:
        """Parse rules from a markdown file."""
        if not rules_path.exists():
            return []

        content = rules_path.read_text()
        lines = content.strip().split("\n")

        if not lines or not lines[0].startswith("# "):
            raise RuleValidationError("Rules file must start with a title (# Rules)")

        rules: list[Rule] = []
        current_category = ""
        current_subcategory = None
        seen_rules = set()  # Track rules within this file

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            if line.startswith("## "):
                # New category
                cat_line = line[3:].strip()
                if "/" in cat_line:
                    current_category, current_subcategory = cat_line.split("/", 1)
                    current_category = current_category.strip()
                    current_subcategory = current_subcategory.strip()
                else:
                    current_category = cat_line
                    current_subcategory = None
                continue

            if line.startswith("- "):
                # New rule
                description = line[2:].strip()
                # Remove any trailing comments
                if "#" in description:
                    description = description.split("#")[0].strip()
                if not current_category:
                    raise RuleValidationError("Rule defined before any category heading.")
                rule = Rule(description, current_category, current_subcategory, is_global)
                rule_key = self._rule_key(rule)

                # Check for duplicates
                if rule_key in seen_rules:
                    raise RuleValidationError(f"Duplicate rule: {description}")

                seen_rules.add(rule_key)
                rules.append(rule)

        # Check for conflicts
        try:
            self._check_conflicting_rules(rules)
        except RuleValidationError as e:
            raise RuleValidationError(f"Conflicting rules: {e}")

        return rules

    def validate_code(self, code: str, rules: list[Rule] | None = None) -> list[str]:
        """Validate code against a set of rules.

        Args:
            code: The code to validate
            rules: Optional list of rules to validate against. If None, uses active_rules.

        Returns:
            List of validation errors, empty if code is valid
        """
        if rules is None:
            rules = list(self.active_rules)

        errors = []
        tree = ast.parse(code)

        for rule in rules:
            if rule.category.lower() == "code style":
                if "type hints" in rule.description.lower():
                    # Check for type hints
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if not node.returns or not any(
                                isinstance(arg.annotation, ast.Name) for arg in node.args.args
                            ):
                                errors.append(f"Missing type hints in function {node.name}")

            elif rule.category.lower() == "documentation":
                if "document all functions" in rule.description.lower():
                    # Check for docstrings
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef) and not ast.get_docstring(node):
                            errors.append(f"Missing docstring in function {node.name}")

            elif rule.category.lower() == "code quality":
                if "no print statements" in rule.description.lower():
                    # Check for print statements
                    for node in ast.walk(tree):
                        if (
                            isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Name)
                            and node.func.id == "print"
                        ):
                            errors.append("Print statement found")

        return errors

    def export_rules(self, project_rules_path: Path, global_rules_path: Path) -> None:
        """Export current rules to files.

        Args:
            project_rules_path: Path to export project rules
            global_rules_path: Path to export global rules
        """
        # Separate rules by type
        project_rules = [r for r in self.active_rules if not r.is_global]
        global_rules = [r for r in self.active_rules if r.is_global]

        # Export project rules
        self._write_rules_file(project_rules, project_rules_path, "Project Rules")

        # Export global rules
        self._write_rules_file(global_rules, global_rules_path, "Global Rules")

    def import_rules(self, project_rules_path: Path, global_rules_path: Path) -> None:
        """Import rules from files.

        Args:
            project_rules_path: Path to import project rules from
            global_rules_path: Path to import global rules from
        """
        # Clear existing rules
        self.active_rules.clear()
        self._seen_rules.clear()

        # Import project rules
        if project_rules_path.exists():
            project_rules = self.parse_rules(project_rules_path)
            for rule in project_rules:
                key = self._rule_key(rule)
                self.active_rules.add(rule)
                self._seen_rules.add(key)

        # Import global rules
        if global_rules_path.exists():
            global_rules = self.parse_rules(global_rules_path, is_global=True)
            for rule in global_rules:
                key = self._rule_key(rule)
                if key not in self._seen_rules:
                    self.active_rules.add(rule)
                    self._seen_rules.add(key)

    def _write_rules_file(self, rules: list[Rule], path: Path, title: str) -> None:
        """Write rules to a file.

        Args:
            rules: List of rules to write
            path: Path to write rules to
            title: Title for the rules file
        """
        # Read existing content if file exists
        existing_content = ""
        if path.exists():
            with path.open("r") as f:
                existing_content = f.read().strip()

        # If existing content is a complete JSON object, preserve it
        if existing_content.startswith("{") and existing_content.endswith("}"):
            return

        # Group rules by category
        rules_by_category: dict[str, list[Rule]] = {}
        for rule in rules:
            category = rule.category
            if category not in rules_by_category:
                rules_by_category[category] = []
            rules_by_category[category].append(rule)

        # Write rules to file
        with path.open("w") as f:
            # Write title if not already present
            if not existing_content.startswith(f"# {title}"):
                f.write(f"# {title}\n\n")
            
            for category in sorted(rules_by_category.keys()):
                f.write(f"## {category}\n")
                for rule in sorted(rules_by_category[category], key=lambda r: r.description):
                    f.write(f"- {rule.description}\n")
                f.write("\n")

    def get_rules_for_file(self, file_path: Path) -> list[Rule]:
        """Get applicable rules for a file.

        Args:
            file_path: Path to the file to get rules for

        Returns:
            List of applicable rules
        """
        # For now, return all active rules
        # In the future, this could be enhanced to filter rules based on file type, path, etc.
        return list(self.active_rules)
