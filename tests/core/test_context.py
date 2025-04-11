"""
Tests for Context Management System
================================

This module contains tests for the context management system components.
"""

import json

import pytest

from erasmus.core.context import ContextFileHandler, ContextValidationError


@pytest.fixture
def temp_context_files(tmp_path):
    """Create temporary context files for testing."""
    # Create test directories
    context_dir = tmp_path / ".erasmus"
    context_dir.mkdir()

    # Create test files
    files = {
        "rules": context_dir / "rules.md",
        "global_rules": context_dir / "global_rules.md",
        "context": context_dir / "context.json",
    }

    # Initialize with valid content
    files["rules"].write_text("""# Project Rules

## Code Style
- Use type hints
- Follow PEP 8
- Document all functions

## Testing
- Write unit tests
- Maintain >90% coverage
""")

    files["global_rules"].write_text("""# Global Rules

## Security
- No hardcoded credentials
- Use environment variables
- Validate all inputs

## Documentation
- Keep README up to date
- Document breaking changes
""")

    files["context"].write_text(json.dumps({
        "project_root": str(tmp_path),
        "active_rules": ["Code Style", "Testing"],
        "global_rules": ["Security"],
        "file_patterns": ["*.py", "*.md"],
        "excluded_paths": ["venv/", "__pycache__/"],
    }, indent=2))

    return tmp_path, files

def test_context_file_handler_initialization(temp_context_files):
    """Test initialization of ContextFileHandler."""
    workspace_root, _ = temp_context_files
    handler = ContextFileHandler(workspace_root)

    assert handler.workspace_root == workspace_root
    assert handler.context_dir == workspace_root / ".erasmus"
    assert handler.rules_file == handler.context_dir / "rules.md"
    assert handler.global_rules_file == handler.context_dir / "global_rules.md"
    assert handler.context_file == handler.context_dir / "context.json"

def test_context_file_reading(temp_context_files):
    """Test reading context files."""
    workspace_root, files = temp_context_files
    handler = ContextFileHandler(workspace_root)

    # Test reading rules
    rules = handler.read_rules()
    assert "Code Style" in rules
    assert "Testing" in rules
    assert len(rules["Code Style"]) == 3
    assert "Use type hints" in rules["Code Style"]

    # Test reading global rules
    global_rules = handler.read_global_rules()
    assert "Security" in global_rules
    assert "Documentation" in global_rules
    assert len(global_rules["Security"]) == 3

    # Test reading context
    context = handler.read_context()
    assert context["project_root"] == str(workspace_root)
    assert "Code Style" in context["active_rules"]
    assert "Security" in context["global_rules"]
    assert "*.py" in context["file_patterns"]

def test_context_file_validation(temp_context_files):
    """Test validation of context files."""
    workspace_root, files = temp_context_files
    handler = ContextFileHandler(workspace_root)

    # Test invalid rules format
    files["rules"].write_text("Invalid rules content")
    with pytest.raises(ContextValidationError):
        handler.read_rules()

    # Test invalid global rules format
    files["global_rules"].write_text("Invalid global rules")
    with pytest.raises(ContextValidationError):
        handler.read_global_rules()

    # Test invalid context JSON
    files["context"].write_text("Invalid JSON")
    with pytest.raises(ContextValidationError):
        handler.read_context()

    # Test missing required fields in context
    files["context"].write_text("{}")
    with pytest.raises(ContextValidationError):
        handler.read_context()

def test_context_file_parsing(temp_context_files):
    """Test parsing of context files."""
    workspace_root, files = temp_context_files
    handler = ContextFileHandler(workspace_root)

    # Test parsing rules with subsections
    files["rules"].write_text("""# Project Rules

## Code Style
### Formatting
- Use black
- Use isort

### Documentation
- Type hints
- Docstrings

## Testing
- Unit tests
- Integration tests
""")

    rules = handler.read_rules()
    assert "Code Style" in rules
    assert "Formatting" in rules["Code Style"]
    assert "Documentation" in rules["Code Style"]
    assert len(rules["Code Style"]["Formatting"]) == 2
    assert "Use black" in rules["Code Style"]["Formatting"]

    # Test parsing with empty sections
    files["rules"].write_text("""# Project Rules

## Empty Section

## Valid Section
- Item 1
- Item 2
""")

    rules = handler.read_rules()
    assert "Empty Section" in rules
    assert not rules["Empty Section"]
    assert len(rules["Valid Section"]) == 2

def test_context_file_updates(temp_context_files):
    """Test updating context files."""
    workspace_root, files = temp_context_files
    handler = ContextFileHandler(workspace_root)

    # Test updating context
    new_context = {
        "project_root": str(workspace_root),
        "active_rules": ["Testing"],
        "global_rules": ["Documentation"],
        "file_patterns": ["*.py"],
        "excluded_paths": ["venv/"],
    }

    handler.update_context(new_context)
    updated_context = handler.read_context()
    assert updated_context == new_context

    # Test partial context update
    handler.update_context({"active_rules": ["Code Style"]}, partial=True)
    updated_context = handler.read_context()
    assert updated_context["active_rules"] == ["Code Style"]
    assert updated_context["global_rules"] == ["Documentation"]  # Unchanged

def test_context_file_backup(temp_context_files):
    """Test backup functionality for context files."""
    workspace_root, files = temp_context_files
    handler = ContextFileHandler(workspace_root)

    # Create backups
    handler.backup_rules()

    # Verify backup files exist
    assert (handler.context_dir / "rules.md.bak").exists()
    assert (handler.context_dir / "global_rules.md.bak").exists()

    # Verify backup content
    rules_backup = (handler.context_dir / "rules.md.bak").read_text()
    assert "Project Rules" in rules_backup
    assert "Code Style" in rules_backup

    global_rules_backup = (handler.context_dir / "global_rules.md.bak").read_text()
    assert "Global Rules" in global_rules_backup
    assert "Security" in global_rules_backup
