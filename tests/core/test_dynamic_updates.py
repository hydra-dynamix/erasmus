"""Tests for dynamic updates functionality."""

import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from erasmus.core.dynamic_updates import Change, ChangeTracker, DynamicUpdates, Update, UpdateValidator
from erasmus.core.rules import Rule, RulesManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def rules_dir(temp_dir):
    """Create a temporary directory for rule files."""
    rules_dir = temp_dir / "rules"
    rules_dir.mkdir()
    return rules_dir


@pytest.fixture
def test_file(temp_dir):
    """Create a test file with initial content."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("Initial content")
    return file_path


@pytest.fixture
def change_tracker():
    """Create a ChangeTracker instance."""
    return ChangeTracker(max_history=5)


@pytest.fixture
def dynamic_updates(rules_dir):
    """Create a DynamicUpdates instance."""
    return DynamicUpdates(rules_dir)


def test_change_tracker_initialization(change_tracker):
    """Test ChangeTracker initialization."""
    assert len(change_tracker.changes) == 0
    assert change_tracker.max_history == 5
    assert len(change_tracker._current_batch) == 0


def test_change_tracker_batch_operations(change_tracker):
    """Test batch operations in ChangeTracker."""
    change1 = Change(
        file_path=Path("test1.txt"),
        timestamp=datetime.now(),
        old_content="old1",
        new_content="new1",
        change_type="modification",
        metadata={}
    )
    change2 = Change(
        file_path=Path("test2.txt"),
        timestamp=datetime.now(),
        old_content="old2",
        new_content="new2",
        change_type="modification",
        metadata={}
    )

    # Start batch and add changes
    change_tracker.start_batch()
    change_tracker.add_change(change1)
    change_tracker.add_change(change2)
    assert len(change_tracker.changes) == 0
    assert len(change_tracker._current_batch) == 2

    # End batch
    change_tracker.end_batch()
    assert len(change_tracker.changes) == 2
    assert len(change_tracker._current_batch) == 0


def test_change_tracker_history_trimming(change_tracker):
    """Test that change history is trimmed correctly."""
    # Add more changes than max_history
    for i in range(10):
        change = Change(
            file_path=Path(f"test{i}.txt"),
            timestamp=datetime.now() + timedelta(seconds=i),
            old_content=f"old{i}",
            new_content=f"new{i}",
            change_type="modification",
            metadata={}
        )
        change_tracker.changes.append(change)

    # Verify only the last 5 changes are kept
    assert len(change_tracker.changes) == 5
    assert change_tracker.changes[-1].file_path.name == "test9.txt"


def test_change_tracker_rollback(change_tracker):
    """Test rollback functionality."""
    # Add some changes
    changes = []
    for i in range(3):
        change = Change(
            file_path=Path("test.txt"),
            timestamp=datetime.now() + timedelta(seconds=i),
            old_content=f"old{i}",
            new_content=f"new{i}",
            change_type="modification",
            metadata={}
        )
        changes.append(change)
        change_tracker.changes.append(change)

    # Rollback one step
    target = change_tracker.rollback(Path("test.txt"))
    assert target == changes[1]
    assert len(change_tracker.changes) == 2

    # Rollback two steps
    target = change_tracker.rollback(Path("test.txt"), 2)
    assert target == changes[0]
    assert len(change_tracker.changes) == 1


def test_dynamic_updates_initialization(dynamic_updates, rules_dir):
    """Test DynamicUpdates initialization."""
    assert dynamic_updates.rules_dir == rules_dir
    assert isinstance(dynamic_updates.rule_manager, RulesManager)
    assert isinstance(dynamic_updates.change_tracker, ChangeTracker)
    assert len(dynamic_updates._watched_files) == 0
    assert len(dynamic_updates._file_content_cache) == 0


def test_file_watching(dynamic_updates, test_file):
    """Test file watching functionality."""
    # Watch file
    dynamic_updates.watch_file(test_file)
    assert test_file in dynamic_updates._watched_files
    assert test_file in dynamic_updates._file_content_cache
    assert dynamic_updates._file_content_cache[test_file] == "Initial content"

    # Unwatch file
    dynamic_updates.unwatch_file(test_file)
    assert test_file not in dynamic_updates._watched_files
    assert test_file not in dynamic_updates._file_content_cache


def test_change_detection(dynamic_updates, test_file):
    """Test change detection functionality."""
    dynamic_updates.watch_file(test_file)

    # Modify file
    test_file.write_text("Modified content")
    changes = dynamic_updates.check_for_updates()
    assert len(changes) == 1
    assert changes[0].change_type == "modification"
    assert changes[0].old_content == "Initial content"
    assert changes[0].new_content == "Modified content"

    # Delete file
    test_file.unlink()
    changes = dynamic_updates.check_for_updates()
    assert len(changes) == 1
    assert changes[0].change_type == "deletion"
    assert changes[0].old_content == "Modified content"
    assert changes[0].new_content is None

    # Recreate file
    test_file.write_text("New content")
    changes = dynamic_updates.check_for_updates()
    assert len(changes) == 1
    assert changes[0].change_type == "creation"
    assert changes[0].old_content is None
    assert changes[0].new_content == "New content"


def test_change_validation(dynamic_updates, test_file, rules_dir):
    """Test change validation functionality."""
    # Create a rule file
    rule_file = rules_dir / "test.rules"
    rule_file.write_text("""
    rule require_docstring {
        description: "Require docstring"
        type: documentation
        pattern: "^\\s*\"\"\".*\"\"\""
    }
    """)

    dynamic_updates.watch_file(test_file)

    # Test valid change
    test_file.write_text('"""Valid docstring"""\ndef test(): pass')
    changes = dynamic_updates.check_for_updates()
    is_valid, errors = dynamic_updates.validate_changes(changes)
    assert is_valid
    assert not errors

    # Test invalid change
    test_file.write_text("def test(): pass")  # No docstring
    changes = dynamic_updates.check_for_updates()
    is_valid, errors = dynamic_updates.validate_changes(changes)
    assert not is_valid
    assert len(errors) == 1
    assert "Rule violation" in errors[0]


def test_change_application(dynamic_updates, test_file):
    """Test change application functionality."""
    dynamic_updates.watch_file(test_file)

    # Apply valid change
    test_file.write_text("New content")
    changes = dynamic_updates.check_for_updates()
    assert dynamic_updates.apply_changes(changes)
    assert test_file.read_text() == "New content"

    # Try to apply invalid change (file doesn't exist)
    test_file.unlink()
    changes = dynamic_updates.check_for_updates()
    assert not dynamic_updates.apply_changes(changes)


def test_rollback_functionality(dynamic_updates, test_file):
    """Test rollback functionality."""
    dynamic_updates.watch_file(test_file)

    # Make some changes
    test_file.write_text("First change")
    changes = dynamic_updates.check_for_updates()
    dynamic_updates.apply_changes(changes)

    test_file.write_text("Second change")
    changes = dynamic_updates.check_for_updates()
    dynamic_updates.apply_changes(changes)

    # Rollback one step
    assert dynamic_updates.rollback_changes(test_file)
    assert test_file.read_text() == "First change"

    # Rollback to initial state
    assert dynamic_updates.rollback_changes(test_file)
    assert test_file.read_text() == "Initial content"


def test_rollback():
    """Test rolling back changes."""
    tracker = ChangeTracker(max_history=5)

    # Add some changes
    changes = [
        Change("file1.txt", "content1", "modify", {"timestamp": datetime.now()}),
        Change("file2.txt", "content2", "modify", {"timestamp": datetime.now()}),
        Change("file3.txt", "content3", "modify", {"timestamp": datetime.now()}),
        Change("file4.txt", "content4", "modify", {"timestamp": datetime.now()}),
        Change("file5.txt", "content5", "modify", {"timestamp": datetime.now()}),
        Change("file6.txt", "content6", "modify", {"timestamp": datetime.now()}),
    ]

    for change in changes:
        tracker.add_change(change)

    # Rollback to third change
    assert tracker.rollback_to(changes[2].metadata["timestamp"])
    assert len(tracker.history) == 3
    assert tracker.history[0] == changes[0]
    assert tracker.history[1] == changes[1]
    assert tracker.history[2] == changes[2]

    # Try to rollback to future timestamp
    future_time = datetime.now() + timedelta(hours=1)
    with pytest.raises(ValueError):
        tracker.rollback_to(future_time)

    # Rollback to second change
    assert tracker.rollback_to(changes[1].metadata["timestamp"])
    assert len(tracker.history) == 2
    assert tracker.history[0] == changes[0]
    assert tracker.history[1] == changes[1]


def test_file_content_rollback(tmp_path):
    """Test rolling back file content changes."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Initial content")
    
    tracker = ChangeTracker(max_history=5)
    
    # Make some changes
    changes = [
        Change(str(test_file), "First change", "modify", {"timestamp": datetime.now()}),
        Change(str(test_file), "Second change", "modify", {"timestamp": datetime.now()}),
        Change(str(test_file), "Third change", "modify", {"timestamp": datetime.now()})
    ]
    
    for change in changes:
        test_file.write_text(change.content)
        tracker.add_change(change)
    
    # Rollback to first change
    assert tracker.rollback_to(changes[0].metadata["timestamp"])
    test_file.write_text(changes[0].content)
    assert test_file.read_text() == "Initial content"
    
    # Rollback to second change
    assert tracker.rollback_to(changes[1].metadata["timestamp"])
    test_file.write_text(changes[1].content)
    assert test_file.read_text() == "First change"


def test_change_tracking(tmp_path):
    """Test tracking changes to files."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Initial content")
    
    tracker = ChangeTracker(max_history=5)
    
    # Track a modification
    change1 = Change(str(test_file), "Modified content", "modify", {"timestamp": datetime.now()})
    tracker.add_change(change1)
    assert len(tracker.history) == 1
    assert tracker.history[0] == change1
    
    # Track a deletion
    test_file.unlink()
    change2 = Change(str(test_file), "", "delete", {"timestamp": datetime.now()})
    tracker.add_change(change2)
    assert len(tracker.history) == 2
    assert tracker.history[1] == change2
    
    # Track a recreation
    test_file.write_text("New content")
    change3 = Change(str(test_file), "New content", "create", {"timestamp": datetime.now()})
    tracker.add_change(change3)
    assert len(tracker.history) == 3
    assert tracker.history[2] == change3
    
    # Test history limit
    for i in range(5):
        change = Change(str(test_file), f"Content {i}", "modify", {"timestamp": datetime.now()})
        tracker.add_change(change)
    
    assert len(tracker.history) == 5  # Max history limit
    assert tracker.history[-1].content == "Content 4"  # Most recent change


def test_update_validation(tmp_path):
    """Test validation of updates."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Initial content")
    
    # Create a mock rules manager
    rules_manager = RulesManager(tmp_path)
    validator = UpdateValidator(rules_manager)
    
    # Test valid update
    valid_update = Update(str(test_file), "Valid content", "modify")
    assert validator.validate_update(valid_update)
    
    # Test invalid update (empty content)
    invalid_update = Update(str(test_file), "", "modify")
    assert not validator.validate_update(invalid_update)
    
    # Test invalid update (nonexistent file)
    nonexistent_update = Update(str(tmp_path / "nonexistent.txt"), "Content", "modify")
    assert not validator.validate_update(nonexistent_update)
    
    # Test invalid update (invalid type)
    invalid_type_update = Update(str(test_file), "Content", "invalid_type")
    assert not validator.validate_update(invalid_type_update)
    
    # Test update with metadata
    metadata_update = Update(
        str(test_file),
        "Content with metadata",
        "modify",
        {"author": "test", "timestamp": datetime.now()}
    )
    assert validator.validate_update(metadata_update) 