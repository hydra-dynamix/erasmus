"""Tests for the dynamic update system."""

import json
from datetime import datetime
from pathlib import Path
import pytest
from erasmus.core.dynamic_updates import DynamicUpdateManager, ChangeRecord

@pytest.fixture
def temp_context_dir(tmp_path):
    """Create a temporary context directory."""
    context_dir = tmp_path / ".erasmus"
    context_dir.mkdir()
    return context_dir

@pytest.fixture
def update_manager(temp_context_dir):
    """Create a DynamicUpdateManager instance."""
    return DynamicUpdateManager(temp_context_dir)

def test_init(temp_context_dir):
    """Test initialization of DynamicUpdateManager."""
    manager = DynamicUpdateManager(temp_context_dir)
    assert manager.context_dir == temp_context_dir
    assert manager.changes_file.exists()
    assert manager.changes == []

def test_detect_changes(update_manager):
    """Test change detection."""
    # Test initial change
    has_changes, diff = update_manager.detect_changes("test", "value")
    assert has_changes
    assert diff == {"type": "initial", "component": "test"}

    # Apply initial value
    update_manager.apply_update("test", "value", "test")

    # Test no changes
    has_changes, diff = update_manager.detect_changes("test", "value")
    assert not has_changes
    assert diff is None

    # Test value change
    has_changes, diff = update_manager.detect_changes("test", "new_value")
    assert has_changes
    assert diff == {"type": "value_change", "old": "value", "new": "new_value"}

    # Test structure change
    has_changes, diff = update_manager.detect_changes("test", {"key": "value"})
    assert has_changes
    assert diff == {"type": "structure_change", "component": "test"}

def test_validate_update(update_manager):
    """Test update validation."""
    # Test empty component
    is_valid, error = update_manager.validate_update("", "value")
    assert not is_valid
    assert error == "Component name cannot be empty"

    # Test None value
    is_valid, error = update_manager.validate_update("test", None)
    assert not is_valid
    assert error == "New value cannot be None"

    # Test valid simple value
    is_valid, error = update_manager.validate_update("test", "value")
    assert is_valid
    assert error is None

    # Test valid complex value
    is_valid, error = update_manager.validate_update("test", {"key": "value"})
    assert is_valid
    assert error is None

    # Test invalid JSON
    class NonSerializable:
        pass
    is_valid, error = update_manager.validate_update("test", NonSerializable())
    assert not is_valid
    assert "JSON serializable" in error

    # Test tasks validation
    is_valid, error = update_manager.validate_update("tasks", [])
    assert not is_valid
    assert error == "tasks must be a dictionary"

    is_valid, error = update_manager.validate_update("tasks", {"1": []})
    assert not is_valid
    assert error == "Task 1 data must be a dictionary"

    is_valid, error = update_manager.validate_update("tasks", {"1": {"status": "pending"}})
    assert not is_valid
    assert error == "Task 1 missing description"

    is_valid, error = update_manager.validate_update("tasks", {"1": {"description": "test"}})
    assert is_valid
    assert error is None

def test_apply_update(update_manager):
    """Test applying updates."""
    # Test invalid update
    assert not update_manager.apply_update("", "value", "test")

    # Test valid update
    assert update_manager.apply_update("test", "value", "test")
    assert len(update_manager.changes) == 1
    change = update_manager.changes[0]
    assert change.component == "test"
    assert change.new_value == "value"
    assert change.source == "test"
    assert change.previous_value is None

    # Test update with metadata
    metadata = {"user": "test_user"}
    assert update_manager.apply_update("test", "new_value", "test", metadata)
    assert len(update_manager.changes) == 2
    change = update_manager.changes[1]
    assert change.metadata == metadata

def test_rollback(update_manager):
    """Test rollback functionality."""
    # Test rollback with no changes
    assert not update_manager.rollback_last_change("test")

    # Add some changes
    update_manager.apply_update("test", "value1", "test")
    update_manager.apply_update("test", "value2", "test")
    update_manager.apply_update("test", "value3", "test")

    # Test rollback
    assert update_manager.rollback_last_change("test")
    assert len(update_manager.changes) == 2
    assert update_manager.changes[-1].new_value == "value2"

    # Test rollback to initial state
    assert update_manager.rollback_last_change("test")
    assert update_manager.rollback_last_change("test")
    assert len(update_manager.changes) == 0

def test_change_history(update_manager):
    """Test change history retrieval."""
    # Add some changes
    update_manager.apply_update("test1", "value1", "test")
    update_manager.apply_update("test2", "value2", "test")
    update_manager.apply_update("test1", "value3", "test")

    # Test full history
    history = update_manager.get_change_history()
    assert len(history) == 3
    assert history[-1].new_value == "value3"

    # Test filtered history
    history = update_manager.get_change_history("test1")
    assert len(history) == 2
    assert all(change.component == "test1" for change in history)
    
    # Test history limit
    history = update_manager.get_change_history(limit=2)
    assert len(history) == 2
    assert history[-1].new_value == "value3"

def test_persistence(temp_context_dir):
    """Test persistence of changes."""
    # Create manager and add changes
    manager1 = DynamicUpdateManager(temp_context_dir)
    manager1.apply_update("test", "value1", "test")
    manager1.apply_update("test", "value2", "test")

    # Create new manager and verify changes are loaded
    manager2 = DynamicUpdateManager(temp_context_dir)
    assert len(manager2.changes) == 2
    assert manager2.changes[-1].new_value == "value2"

    # Verify changes file content
    changes_file = temp_context_dir / "changes.json"
    content = json.loads(changes_file.read_text())
    assert len(content) == 2
    assert content[-1]["new_value"] == "value2" 