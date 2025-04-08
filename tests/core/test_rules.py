"""
Tests for Rules Management System
===============================

This module contains tests for the rules management system components.
"""

import pytest
from pathlib import Path
from erasmus.core.context import ContextValidationError
from erasmus.core.rules import RulesManager, RuleValidationError, Rule

@pytest.fixture
def temp_rules_files(tmp_path):
    """Create temporary rules files for testing."""
    # Create test directories
    rules_dir = tmp_path / ".erasmus"
    rules_dir.mkdir()
    
    # Create test files
    files = {
        "project": rules_dir / "rules.md",
        "global": rules_dir / "global_rules.md",
    }
    
    # Initialize with valid content
    files["project"].write_text("""# Project Rules

## Code Style
- Use type hints
- Follow PEP 8
- Document all functions

## Testing
- Write unit tests
- Maintain >90% coverage
""")
    
    files["global"].write_text("""# Global Rules

## Security
- No hardcoded credentials
- Use environment variables
- Validate all inputs

## Documentation
- Keep README up to date
- Document breaking changes
""")
    
    return tmp_path, files

def test_rules_manager_initialization(temp_rules_files):
    """Test initialization of RulesManager."""
    workspace_root, _ = temp_rules_files
    manager = RulesManager(workspace_root)
    
    assert manager.workspace_root == workspace_root
    assert manager.rules_dir == workspace_root / ".erasmus"
    assert manager.project_rules_file == manager.rules_dir / "rules.md"
    assert manager.global_rules_file == manager.rules_dir / "global_rules.md"

def test_rule_creation():
    """Test creation and validation of individual rules."""
    # Test valid rule creation
    rule = Rule("Use type hints", "Code Style")
    assert rule.description == "Use type hints"
    assert rule.category == "Code Style"
    assert not rule.is_global
    
    # Test rule with subcategory
    rule = Rule("Use black", "Code Style/Formatting")
    assert rule.description == "Use black"
    assert rule.category == "Code Style"
    assert rule.subcategory == "Formatting"
    
    # Test invalid rule
    with pytest.raises(RuleValidationError):
        Rule("", "")  # Empty description and category

def test_rule_parsing(temp_rules_files):
    """Test parsing of rules from markdown content."""
    workspace_root, files = temp_rules_files
    manager = RulesManager(workspace_root)
    
    # Test parsing project rules
    rules = manager.parse_rules(files["project"])
    assert len(rules) == 5  # Total number of rules
    assert any(r.description == "Use type hints" and r.category == "Code Style" for r in rules)
    assert any(r.description == "Write unit tests" and r.category == "Testing" for r in rules)
    
    # Test parsing global rules
    rules = manager.parse_rules(files["global"], is_global=True)
    assert len(rules) == 5  # Total number of global rules
    assert all(r.is_global for r in rules)
    assert any(r.description == "No hardcoded credentials" and r.category == "Security" for r in rules)

def test_rule_validation(temp_rules_files):
    """Test validation of rules content and structure."""
    workspace_root, files = temp_rules_files
    manager = RulesManager(workspace_root)
    
    # Test invalid rules format
    files["project"].write_text("Invalid rules content")
    with pytest.raises(RuleValidationError):
        manager.parse_rules(files["project"])
    
    # Test duplicate rules
    files["project"].write_text("""# Project Rules

## Code Style
- Use type hints
- Use type hints  # Duplicate
""")
    with pytest.raises(RuleValidationError, match="Duplicate rule"):
        manager.parse_rules(files["project"])
    
    # Test conflicting rules
    files["project"].write_text("""# Project Rules

## Code Style
- Use spaces for indentation

## Formatting
- Use tabs for indentation
""")
    with pytest.raises(RuleValidationError, match="Conflicting rules"):
        manager.parse_rules(files["project"])

def test_rule_inheritance(temp_rules_files):
    """Test inheritance and merging of global and project rules."""
    workspace_root, files = temp_rules_files
    manager = RulesManager(workspace_root)
    
    # Load both global and project rules
    manager.load_rules()
    
    # Check that global rules are inherited
    assert any(r.description == "No hardcoded credentials" and r.is_global for r in manager.active_rules)
    
    # Check that project rules override global rules when there's a conflict
    files["global"].write_text("""# Global Rules

## Code Style
- Use spaces for indentation
""")
    files["project"].write_text("""# Project Rules

## Code Style
- Use tabs for indentation
""")
    
    manager.load_rules()
    indentation_rules = [r for r in manager.active_rules if "indentation" in r.description.lower()]
    assert len(indentation_rules) == 1
    assert "tabs" in indentation_rules[0].description.lower()

def test_rule_application():
    """Test application of rules to files."""
    workspace_root = Path("/tmp/test_rules")
    manager = RulesManager(workspace_root)
    
    # Create test rules
    rules = [
        Rule("Use type hints", "Code Style"),
        Rule("Document all functions", "Documentation"),
        Rule("No print statements", "Code Quality")
    ]
    
    # Test valid Python file
    valid_code = '''
def greet(name: str) -> str:
    """Return a greeting message.
    
    Args:
        name: The name to greet
        
    Returns:
        A greeting message
    """
    return f"Hello, {name}!"
'''
    assert manager.validate_code(valid_code, rules)
    
    # Test invalid Python file (missing type hints)
    invalid_code = '''
def greet(name):
    """Greet someone."""
    print(f"Hello, {name}!")  # Print statement violation
    return f"Hello, {name}!"
'''
    violations = manager.validate_code(invalid_code, rules)
    assert len(violations) == 2  # Missing type hints and print statement

def test_rule_export_import(temp_rules_files):
    """Test exporting and importing rules."""
    workspace_root, files = temp_rules_files
    manager = RulesManager(workspace_root)
    
    # Load initial rules
    manager.load_rules()
    initial_rules = manager.active_rules
    
    # Export rules to new files
    export_dir = workspace_root / "exported_rules"
    export_dir.mkdir()
    manager.export_rules(export_dir / "exported_project_rules.md", export_dir / "exported_global_rules.md")
    
    # Create new manager and import rules
    new_manager = RulesManager(workspace_root)
    new_manager.import_rules(export_dir / "exported_project_rules.md", export_dir / "exported_global_rules.md")
    
    # Verify rules are the same
    assert len(new_manager.active_rules) == len(initial_rules)
    for r1, r2 in zip(sorted(new_manager.active_rules, key=lambda x: x.description),
                      sorted(initial_rules, key=lambda x: x.description)):
        assert r1.description == r2.description
        assert r1.category == r2.category
        assert r1.is_global == r2.is_global 