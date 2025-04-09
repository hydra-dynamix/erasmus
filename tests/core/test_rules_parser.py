"""
Tests for the RulesParser class.

This module contains tests for parsing and validating rules in the context management system.
"""

import pytest
from pathlib import Path
from typing import Dict, List, Optional
from erasmus.core.rules_parser import RulesParser, Rule, RuleType, RuleValidationError

@pytest.fixture
def sample_rules_content() -> str:
    """Return sample rules content for testing."""
    return """
# Code Style Rules
rule: require_type_hints
description: All functions must have type hints
type: code_style
pattern: def\\s+\\w+\\s*\\([^)]*\\)\\s*->\\s*[^:]+:
severity: error

rule: require_docstrings
description: All functions must have docstrings
type: documentation
pattern: def\\s+\\w+[^\\n]*\\n\\s*[\\"\\'][\\"\\'][\\"\\'](.|\\n)*?[\\"\\'][\\"\\'][\\"\\'](\\s|\\n)
severity: warning

rule: no_print_statements
description: No print statements in production code
type: code_style
pattern: print\\s*\\(
severity: error
"""

@pytest.fixture
def rules_parser(temp_dir: Path, sample_rules_content: str) -> RulesParser:
    """Create a RulesParser instance with sample rules."""
    rules_file = temp_dir / "rules.md"
    rules_file.write_text(sample_rules_content)
    return RulesParser(rules_file)

def test_rules_parser_initialization(rules_parser: RulesParser):
    """Test RulesParser initialization."""
    assert rules_parser.rules_file.exists()
    assert len(rules_parser.rules) == 3

def test_rule_parsing(rules_parser: RulesParser):
    """Test parsing of individual rules."""
    # Check first rule
    type_hints_rule = rules_parser.rules[0]
    assert type_hints_rule.name == "require_type_hints"
    assert type_hints_rule.description == "All functions must have type hints"
    assert type_hints_rule.type == RuleType.CODE_STYLE
    assert type_hints_rule.pattern == "def\\s+\\w+\\s*\\([^)]*\\)\\s*->\\s*[^:]+:"
    assert type_hints_rule.severity == "error"

    # Check second rule
    docstrings_rule = rules_parser.rules[1]
    assert docstrings_rule.name == "require_docstrings"
    assert docstrings_rule.description == "All functions must have docstrings"
    assert docstrings_rule.type == RuleType.DOCUMENTATION
    assert docstrings_rule.severity == "warning"

def test_rule_validation(rules_parser: RulesParser):
    """Test rule validation."""
    # Valid code with type hints and docstring
    valid_code = '''
    def example_function(x: int, y: str) -> bool:
        """Example function with proper type hints and docstring."""
        return True
    '''
    errors = rules_parser.validate_code(valid_code)
    assert not errors

    # Invalid code without type hints
    invalid_code = '''
    def example_function(x, y):
        """Example function without type hints."""
        return True
    '''
    errors = rules_parser.validate_code(invalid_code)
    assert len(errors) == 1
    assert errors[0].rule.name == "require_type_hints"
    assert errors[0].severity == "error"

def test_rule_priority(rules_parser: RulesParser):
    """Test rule priority handling."""
    # Add a rule with higher priority
    high_priority_rule = Rule(
        name="high_priority",
        description="High priority rule",
        type=RuleType.CODE_STYLE,
        pattern="test",
        severity="error",
        priority=1
    )
    rules_parser.rules.append(high_priority_rule)
    
    # Sort rules by priority
    rules_parser.rules.sort(key=lambda x: (-x.priority, x.order))
    
    # Rules should be sorted by priority (higher priority first)
    assert rules_parser.rules[0].name == "high_priority"
    assert rules_parser.rules[0].priority == 1

def test_invalid_rule_file(temp_dir: Path):
    """Test handling of invalid rule file."""
    invalid_file = temp_dir / "invalid_rules.md"
    invalid_file.write_text("invalid content")
    
    with pytest.raises(RuleValidationError):
        RulesParser(invalid_file)

def test_rule_caching(rules_parser: RulesParser):
    """Test rule caching functionality."""
    # First parse should cache the rules
    initial_rules = rules_parser.rules.copy()
    
    # Modify the rules file
    rules_parser.rules_file.write_text("")
    
    # Rules should still be cached
    assert rules_parser.rules == initial_rules
    
    # Force reload
    rules_parser.reload_rules()
    assert len(rules_parser.rules) == 0 