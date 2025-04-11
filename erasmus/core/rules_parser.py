"""
Rules Parser Module

This module provides functionality for parsing and validating rules in the context management system.
It includes classes for representing rules and their types, as well as a parser for reading rules from files.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ..utils.file_ops import safe_read_file


class RuleType(Enum):
    """Enumeration of rule types."""
    CODE_STYLE = "code_style"
    DOCUMENTATION = "documentation"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"

@dataclass
class Rule:
    """
    Represents a single rule with its properties.
    
    Attributes:
        name (str): Unique identifier for the rule
        description (str): Human-readable description of the rule
        type (RuleType): Type of the rule
        pattern (str): Regular expression pattern to match
        severity (str): Severity level (error, warning, info)
        priority (int): Rule priority (higher numbers = higher priority)
        order (int): Original order in the rules file
    """
    name: str
    description: str
    type: RuleType
    pattern: str
    severity: str
    priority: int = 0
    order: int = 0

    def __post_init__(self):
        """Validate rule properties after initialization."""
        if not self.name:
            raise ValueError("Rule name cannot be empty")
        if not self.description:
            raise ValueError("Rule description cannot be empty")
        if not self.pattern:
            raise ValueError("Rule pattern cannot be empty")
        if self.severity not in ["error", "warning", "info"]:
            raise ValueError("Invalid severity level")

class RuleValidationError(Exception):
    """Exception raised when rule validation fails."""

@dataclass
class ValidationError:
    """
    Represents a validation error found during rule checking.
    
    Attributes:
        rule (Rule): The rule that was violated
        message (str): Description of the violation
        line_number (Optional[int]): Line number where the violation occurred
        severity (str): Severity level of the violation
    """
    rule: Rule
    message: str
    line_number: int | None = None
    severity: str = "error"

class RulesParser:
    """
    Parser for reading and validating rules from files.
    
    This class handles reading rules from markdown files, parsing their content,
    and validating code against the rules.
    
    Attributes:
        rules_file (Path): Path to the rules file
        rules (List[Rule]): List of parsed rules
        _cached_rules (Optional[List[Rule]]): Cached rules for performance
    """

    def __init__(self, rules_file: Path):
        """
        Initialize the RulesParser with a rules file.
        
        Args:
            rules_file (Path): Path to the rules file to parse
            
        Raises:
            RuleValidationError: If the rules file is invalid
        """
        self.rules_file = Path(rules_file)
        self._cached_rules: list[Rule] | None = None
        self.rules = self._parse_rules()

    def _parse_rules(self) -> list[Rule]:
        """
        Parse rules from the rules file.
        
        Returns:
            List[Rule]: List of parsed rules
            
        Raises:
            RuleValidationError: If the rules file is invalid
        """
        if not self.rules_file.exists():
            raise RuleValidationError(f"Rules file not found: {self.rules_file}")

        try:
            content = self.rules_file.read_text()
            if not content.strip():
                return []

            rules = []
            current_rule: dict[str, Any] = {}
            order = 0

            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if line.startswith("rule:"):
                    if current_rule:
                        current_rule["order"] = order
                        rules.append(self._create_rule(current_rule))
                        order += 1
                    current_rule = {}
                    current_rule["name"] = line.split(":", 1)[1].strip()
                elif ":" in line:
                    key, value = line.split(":", 1)
                    current_rule[key.strip()] = value.strip()

            if current_rule:
                current_rule["order"] = order
                rules.append(self._create_rule(current_rule))

            if not rules:
                raise RuleValidationError("No valid rules found in file")

            # Sort rules by priority (higher priority first), then by original order
            rules.sort(key=lambda x: (-x.priority, x.order))
            return rules

        except (ValueError, KeyError) as e:
            raise RuleValidationError(f"Error parsing rules file: {e!s}")
        except Exception as e:
            raise RuleValidationError(f"Unexpected error parsing rules file: {e!s}")

    def _create_rule(self, rule_data: dict[str, Any]) -> Rule:
        """
        Create a Rule object from parsed data.
        
        Args:
            rule_data (Dict[str, Any]): Dictionary of rule properties
            
        Returns:
            Rule: Created Rule object
            
        Raises:
            RuleValidationError: If required fields are missing or invalid
        """
        required_fields = ["name", "description", "type", "pattern", "severity"]
        missing_fields = [field for field in required_fields if field not in rule_data]

        if missing_fields:
            raise RuleValidationError(f"Missing required fields: {', '.join(missing_fields)}")

        try:
            rule_type = RuleType(rule_data["type"])
        except ValueError:
            raise RuleValidationError(f"Invalid rule type: {rule_data['type']}")

        try:
            priority = int(rule_data.get("priority", 0))
        except ValueError:
            raise RuleValidationError("Priority must be an integer")

        return Rule(
            name=rule_data["name"],
            description=rule_data["description"],
            type=rule_type,
            pattern=rule_data["pattern"],
            severity=rule_data["severity"],
            priority=priority,
            order=rule_data.get("order", 0),
        )

    def validate_code(self, code: str) -> list[ValidationError]:
        """
        Validate code against all rules.
        
        Args:
            code (str): Code to validate
            
        Returns:
            List[ValidationError]: List of validation errors found
        """
        errors = []

        for rule in self.rules:
            try:
                pattern = re.compile(rule.pattern)
                matches = list(pattern.finditer(code))

                if rule.type == RuleType.CODE_STYLE:
                    # For code style rules, we want to ensure the pattern is NOT found
                    if matches and rule.name == "no_print_statements":
                        errors.append(ValidationError(
                            rule=rule,
                            message=f"Code violates rule: {rule.description}",
                            severity=rule.severity,
                        ))
                    # For other code style rules, we want to ensure the pattern IS found
                    elif not matches and rule.name != "no_print_statements":
                        errors.append(ValidationError(
                            rule=rule,
                            message=f"Code does not match rule pattern: {rule.description}",
                            severity=rule.severity,
                        ))
                elif rule.type == RuleType.DOCUMENTATION:
                    # For documentation rules, we want to ensure the pattern IS found
                    if not matches:
                        errors.append(ValidationError(
                            rule=rule,
                            message=f"Code does not match rule pattern: {rule.description}",
                            severity=rule.severity,
                        ))
            except re.error as e:
                errors.append(ValidationError(
                    rule=rule,
                    message=f"Invalid rule pattern: {e!s}",
                    severity="error",
                ))

        return errors

    def reload_rules(self) -> None:
        """Force reload of rules from file."""
        self._cached_rules = None
        self.rules = self._parse_rules()

    def parse_rules_file(self, file_path: Path) -> list[Rule]:
        """Parse rules from a markdown file.
        
        Args:
            file_path: Path to the markdown file containing rules
            
        Returns:
            List of Rule objects parsed from the file
            
        Raises:
            FileNotFoundError: If the rules file does not exist
            RuleParsingError: If there are errors parsing the rules
        """
        try:
            content = safe_read_file(file_path)
            return self.parse_rules_content(content)
        except FileNotFoundError:
            logging.exception(f"Rules file not found: {file_path}")
            raise
        except Exception as e:
            logging.exception(f"Error parsing rules from {file_path}: {e}")
            raise RuleParsingError(f"Failed to parse rules from {file_path}: {e}")
