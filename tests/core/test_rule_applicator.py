"""
Tests for the RuleApplicator class.

This module contains tests for applying rules to code and managing rule chains.
"""

import pytest
from pathlib import Path
from typing import List, Dict
from erasmus.core.rules_parser import Rule, RuleType, ValidationError
from erasmus.core.rule_applicator import RuleApplicator, RuleChain, RuleApplicationError

@pytest.fixture
def sample_rules() -> List[Rule]:
    """Return a list of sample rules for testing."""
    return [
        Rule(
            name="require_type_hints",
            description="All functions must have type hints",
            type=RuleType.CODE_STYLE,
            pattern=r"def\s+\w+\s*\([^)]*\)\s*->\s*[^:]+:",
            severity="error",
            priority=1
        ),
        Rule(
            name="require_docstrings",
            description="All functions must have docstrings",
            type=RuleType.DOCUMENTATION,
            pattern=r'def\s+\w+[^\n]*\n\s*["\']["\']["\'](.|\n)*?["\']["\']["\'](\s|\n)',
            severity="warning",
            priority=0
        ),
        Rule(
            name="no_print_statements",
            description="No print statements in production code",
            type=RuleType.CODE_STYLE,
            pattern=r"print\s*\(",
            severity="error",
            priority=2
        )
    ]

@pytest.fixture
def rule_applicator(sample_rules: List[Rule]) -> RuleApplicator:
    """Create a RuleApplicator instance with sample rules."""
    return RuleApplicator(sample_rules)

def test_rule_applicator_initialization(rule_applicator: RuleApplicator):
    """Test RuleApplicator initialization."""
    assert len(rule_applicator.rules) == 3
    assert rule_applicator.rules[0].name == "no_print_statements"  # Highest priority
    assert rule_applicator.rules[1].name == "require_type_hints"   # Medium priority
    assert rule_applicator.rules[2].name == "require_docstrings"   # Lowest priority

def test_rule_chain_creation(rule_applicator: RuleApplicator):
    """Test creating a chain of rules."""
    chain = rule_applicator.create_chain(["require_type_hints", "require_docstrings"])
    assert len(chain.rules) == 2
    assert chain.rules[0].name == "require_type_hints"
    assert chain.rules[1].name == "require_docstrings"

def test_invalid_rule_chain(rule_applicator: RuleApplicator):
    """Test creating a chain with invalid rules."""
    with pytest.raises(RuleApplicationError):
        rule_applicator.create_chain(["nonexistent_rule"])

def test_rule_chain_application(rule_applicator: RuleApplicator):
    """Test applying a chain of rules to code."""
    # Create a chain with type hints and docstring rules
    chain = rule_applicator.create_chain(["require_type_hints", "require_docstrings"])
    
    # Test valid code
    valid_code = '''
    def example_function(x: int, y: str) -> bool:
        """Example function with proper type hints and docstring."""
        return True
    '''
    errors = rule_applicator.apply_chain(chain, valid_code)
    assert not errors

    # Test invalid code (missing type hints and docstring)
    invalid_code = '''
    def example_function(x, y):
        return True
    '''
    errors = rule_applicator.apply_chain(chain, invalid_code)
    assert len(errors) == 2
    assert any(e.rule.name == "require_type_hints" for e in errors)
    assert any(e.rule.name == "require_docstrings" for e in errors)

def test_rule_chain_order(rule_applicator: RuleApplicator):
    """Test that rules in a chain are applied in order."""
    # Create a chain with all rules in specific order
    chain = rule_applicator.create_chain([
        "require_type_hints",
        "require_docstrings",
        "no_print_statements"
    ])
    
    # Test code that violates all rules
    invalid_code = '''
    def example_function(x, y):
        print("Debug message")
        return True
    '''
    errors = rule_applicator.apply_chain(chain, invalid_code)
    assert len(errors) == 3
    # Errors should be in chain order, not priority order
    assert errors[0].rule.name == "require_type_hints"
    assert errors[1].rule.name == "require_docstrings"
    assert errors[2].rule.name == "no_print_statements"

def test_rule_chain_subset(rule_applicator: RuleApplicator):
    """Test applying a subset of rules."""
    # Create a chain with only the docstring rule
    chain = rule_applicator.create_chain(["require_docstrings"])
    
    # Test code that violates type hints but has docstring
    code = '''
    def example_function(x, y):
        """This function has a docstring but no type hints."""
        return True
    '''
    errors = rule_applicator.apply_chain(chain, code)
    assert not errors  # Should pass because we're only checking docstrings

def test_empty_rule_chain(rule_applicator: RuleApplicator):
    """Test behavior with empty rule chain."""
    chain = rule_applicator.create_chain([])
    code = "def example(): pass"
    errors = rule_applicator.apply_chain(chain, code)
    assert not errors

def test_rule_chain_modification(rule_applicator: RuleApplicator):
    """Test modifying a rule chain."""
    chain = rule_applicator.create_chain(["require_type_hints"])
    assert len(chain.rules) == 1
    
    # Add a rule
    chain.add_rule(rule_applicator.get_rule("require_docstrings"))
    assert len(chain.rules) == 2
    
    # Remove a rule
    chain.remove_rule("require_type_hints")
    assert len(chain.rules) == 1
    assert chain.rules[0].name == "require_docstrings" 