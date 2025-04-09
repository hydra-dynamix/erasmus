"""
Rules Management System
=====================

This module provides classes and utilities for managing project rules.
Rules are stored in markdown files and can be global or project-specific.
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class RuleValidationError(Exception):
    """Raised when a rule validation fails."""
    pass

@dataclass
class Rule:
    """Represents a single rule with its metadata."""
    description: str
    category: str
    subcategory: Optional[str] = None
    is_global: bool = False
    
    def __post_init__(self):
        """Validate rule attributes after initialization."""
        if not self.description or not self.description.strip():
            raise RuleValidationError("Rule description cannot be empty")
        if not self.category or not self.category.strip():
            raise RuleValidationError("Rule category cannot be empty")
        
        # Split category into main category and subcategory if present
        if "/" in self.category:
            self.category, self.subcategory = self.category.split("/", 1)
        
        self.description = self.description.strip()
        self.category = self.category.strip()
        if self.subcategory:
            self.subcategory = self.subcategory.strip()
    
    def __eq__(self, other):
        """Compare rules based on their description and category."""
        if not isinstance(other, Rule):
            return False
        return (self.description.lower() == other.description.lower() and
                self.category.lower() == other.category.lower() and
                (self.subcategory or "").lower() == (other.subcategory or "").lower())
    
    def __hash__(self):
        """Hash based on description and category."""
        return hash((self.description.lower(), self.category.lower(), (self.subcategory or "").lower()))

    def get_key(self) -> Tuple[str, str, str]:
        """Get a unique key for the rule."""
        return (
            self.category.lower(),
            (self.subcategory or "").lower(),
            self.description.lower()
        )

class RulesManager:
    """Manages project and global rules."""
    
    def __init__(self, workspace_root: Path):
        """Initialize the rules manager.
        
        Args:
            workspace_root: Path to the project workspace root
        """
        self.workspace_root = Path(workspace_root)
        self.rules_dir = self.workspace_root / ".erasmus"
        self.project_rules_file = self.rules_dir / "rules.md"
        self.global_rules_file = self.rules_dir / "global_rules.md"
        self.active_rules: Set[Rule] = set()
        self._seen_rules: Set[str] = set()  # Track rules by their unique key
        self._conflicting_patterns = [
            (r"use\s+spaces\s+for\s+indentation", r"use\s+tabs\s+for\s+indentation"),
            # Add more conflicting patterns as needed
        ]
    
    def _rule_key(self, rule: Rule) -> str:
        """Generate a unique key for a rule."""
        return f"{rule.category.lower()}:{rule.description.lower()}"

    def load_rules(self) -> None:
        """Load both global and project rules."""
        self.active_rules.clear()
        self._seen_rules.clear()

        # Load global rules first
        global_rules_path = self.workspace_root / ".erasmus" / "global_rules.md"
        if global_rules_path.exists():
            global_rules = self.parse_rules(global_rules_path, is_global=True)
            for rule in global_rules:
                key = self._rule_key(rule)
                if key not in self._seen_rules:
                    self.active_rules.add(rule)
                    self._seen_rules.add(key)

        # Load project rules, overriding global rules
        project_rules_path = self.workspace_root / ".erasmus" / "rules.md"
        if project_rules_path.exists():
            project_rules = self.parse_rules(project_rules_path)
            for rule in project_rules:
                key = self._rule_key(rule)
                # Remove any existing rule with the same key or conflicting rules
                conflicting_rules = set()
                for existing_rule in self.active_rules:
                    if self._rule_key(existing_rule) == key:
                        conflicting_rules.add(existing_rule)
                    else:
                        # Check for pattern-based conflicts
                        desc1 = rule.description.lower()
                        desc2 = existing_rule.description.lower()
                        for pattern1, pattern2 in self._conflicting_patterns:
                            if (re.search(pattern1, desc1) and re.search(pattern2, desc2)) or \
                               (re.search(pattern2, desc1) and re.search(pattern1, desc2)):
                                conflicting_rules.add(existing_rule)
                
                # Remove conflicting rules
                self.active_rules -= conflicting_rules
                self.active_rules.add(rule)
                self._seen_rules.add(key)
    
    def _check_conflicting_rules(self, rules: List[Rule]) -> None:
        """Check for conflicting rules within a list of rules."""
        for rule1 in rules:
            desc1 = rule1.description.lower()
            for rule2 in rules:
                if rule1 is rule2:
                    continue
                desc2 = rule2.description.lower()
                
                # Check for direct conflicts using patterns
                for pattern1, pattern2 in self._conflicting_patterns:
                    if (re.search(pattern1, desc1) and re.search(pattern2, desc2)) or \
                       (re.search(pattern2, desc1) and re.search(pattern1, desc2)):
                        raise RuleValidationError(
                            f"Conflicting rules found: '{rule1.description}' and '{rule2.description}'"
                        )
    
    def parse_rules(self, rules_path: Path, is_global: bool = False) -> List[Rule]:
        """Parse rules from a markdown file."""
        if not rules_path.exists():
            return []

        content = rules_path.read_text()
        lines = content.strip().split("\n")
        
        if not lines or not lines[0].startswith("# "):
            raise RuleValidationError("Rules file must start with a title (# Rules)")

        rules: List[Rule] = []
        current_category = ""
        current_subcategory = None
        seen_rules = set()  # Track rules within this file

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("## "):
                # New category
                current_category = line[3:].strip()
                current_subcategory = None
                if "/" in current_category:
                    current_category, current_subcategory = current_category.split("/", 1)
                continue
            
            if line.startswith("- "):
                # New rule
                description = line[2:].strip()
                # Remove any trailing comments
                if "#" in description:
                    description = description.split("#")[0].strip()
                
                rule = Rule(description, current_category, current_subcategory, is_global)
                rule_key = self._rule_key(rule)
                
                # Check for duplicates
                if rule_key in seen_rules:
                    raise RuleValidationError(f"Duplicate rule: {description}")
                
                seen_rules.add(rule_key)
                rules.append(rule)
        
        # Check for conflicts
        self._check_conflicting_rules(rules)
        
        return rules
    
    def validate_code(self, code: str, rules: Optional[List[Rule]] = None) -> List[str]:
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
                            if not node.returns or not any(isinstance(arg.annotation, ast.Name) for arg in node.args.args):
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
                        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
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
    
    def _write_rules_file(self, rules: List[Rule], path: Path, title: str) -> None:
        """Write rules to a file.
        
        Args:
            rules: List of rules to write
            path: Path to write rules to
            title: Title for the rules file
        """
        # Group rules by category
        rules_by_category: Dict[str, List[Rule]] = {}
        for rule in rules:
            category = rule.category
            if category not in rules_by_category:
                rules_by_category[category] = []
            rules_by_category[category].append(rule)
        
        # Write rules to file
        with path.open("w") as f:
            f.write(f"# {title}\n\n")
            for category in sorted(rules_by_category.keys()):
                f.write(f"## {category}\n")
                for rule in sorted(rules_by_category[category], key=lambda r: r.description):
                    f.write(f"- {rule.description}\n")
                f.write("\n")

    def get_rules_for_file(self, file_path: Path) -> List[Rule]:
        """Get applicable rules for a file.
        
        Args:
            file_path: Path to the file to get rules for
            
        Returns:
            List of applicable rules
        """
        # For now, return all active rules
        # In the future, this could be enhanced to filter rules based on file type, path, etc.
        return list(self.active_rules) 