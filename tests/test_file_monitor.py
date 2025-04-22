import os
import time
import pytest
from pathlib import Path
from erasmus.file_monitor import FileMonitor, FileMonitorError


@pytest.fixture
def file_monitor(tmp_path):
    """Create a FileMonitor instance with a temporary watch path."""
    return FileMonitor(watch_path=str(tmp_path))


@pytest.fixture
def sample_files(tmp_path):
    """Create sample files for testing."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Initial content")

    # Create a test directory with a file
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    test_dir_file = test_dir / "test.txt"
    test_dir_file.write_text("Initial content")

    return tmp_path, test_file, test_dir, test_dir_file


def test_add_watch_path(file_monitor, tmp_path):
    """Test adding a watch path."""
    watch_path = tmp_path / "watch_path"
    watch_path.mkdir()

    file_monitor.add_watch_path(str(watch_path))
    assert str(watch_path) in file_monitor.watch_paths


def test_add_nonexistent_watch_path(file_monitor, tmp_path):
    """Test adding a nonexistent watch path."""
    watch_path = tmp_path / "nonexistent"

    with pytest.raises(FileMonitorError):
        file_monitor.add_watch_path(str(watch_path))


def test_remove_watch_path(file_monitor, tmp_path):
    """Test removing a watch path."""
    watch_path = tmp_path / "watch_path"
    watch_path.mkdir()

    file_monitor.add_watch_path(str(watch_path))
    file_monitor.remove_watch_path(str(watch_path))
    assert str(watch_path) not in file_monitor.watch_paths


def test_file_created(file_monitor, tmp_path):
    """Test file creation event."""
    events = []

    def on_created(event):
        events.append(event)

    file_monitor.on_created = on_created
    file_monitor.start()

    # Create a new file
    test_file = tmp_path / "new_file.txt"
    test_file.write_text("Test content")

    # Wait for event
    time.sleep(1)
    file_monitor.stop()

    assert len(events) == 1
    assert events[0].src_path == str(test_file)


def test_file_modified(file_monitor, sample_files):
    """Test file modification event."""
    _, test_file, _, _ = sample_files
    events = []

    def on_modified(event):
        events.append(event)

    file_monitor.on_modified = on_modified
    file_monitor.start()

    # Modify the file
    test_file.write_text("Modified content")

    # Wait for event
    time.sleep(1)
    file_monitor.stop()

    assert len(events) == 1
    assert events[0].src_path == str(test_file)


def test_file_deleted(file_monitor, sample_files):
    """Test file deletion event."""
    _, test_file, _, _ = sample_files
    events = []

    def on_deleted(event):
        events.append(event)

    file_monitor.on_deleted = on_deleted
    file_monitor.start()

    # Delete the file
    test_file.unlink()

    # Wait for event
    time.sleep(1)
    file_monitor.stop()

    assert len(events) == 1
    assert events[0].src_path == str(test_file)


def test_directory_created(file_monitor, tmp_path):
    """Test directory creation event."""
    events = []

    def on_created(event):
        events.append(event)

    file_monitor.on_created = on_created
    file_monitor.start()

    # Create a new directory
    test_dir = tmp_path / "new_dir"
    test_dir.mkdir()

    # Wait for event
    time.sleep(1)
    file_monitor.stop()

    assert len(events) == 1
    assert events[0].src_path == str(test_dir)


def test_directory_deleted(file_monitor, sample_files):
    """Test directory deletion event."""
    _, _, test_dir, _ = sample_files
    events = []

    def on_deleted(event):
        events.append(event)

    file_monitor.on_deleted = on_deleted
    file_monitor.start()

    # Delete the directory
    test_dir.rmdir()

    # Wait for event
    time.sleep(1)
    file_monitor.stop()

    assert len(events) == 1
    assert events[0].src_path == str(test_dir)


def test_multiple_watch_paths(file_monitor, tmp_path):
    """Test monitoring multiple paths."""
    watch_path1 = tmp_path / "watch1"
    watch_path2 = tmp_path / "watch2"
    watch_path1.mkdir()
    watch_path2.mkdir()

    file_monitor.add_watch_path(str(watch_path1))
    file_monitor.add_watch_path(str(watch_path2))

    events = []

    def on_created(event):
        events.append(event)

    file_monitor.on_created = on_created
    file_monitor.start()

    # Create files in both paths
    test_file1 = watch_path1 / "test1.txt"
    test_file2 = watch_path2 / "test2.txt"
    test_file1.write_text("Test 1")
    test_file2.write_text("Test 2")

    # Wait for events
    time.sleep(1)
    file_monitor.stop()

    assert len(events) == 2
    assert str(test_file1) in [e.src_path for e in events]
    assert str(test_file2) in [e.src_path for e in events]


def test_ignore_patterns(file_monitor, tmp_path):
    """Test ignoring files based on patterns."""
    file_monitor.ignore_patterns = ["*.tmp"]
    events = []

    def on_created(event):
        events.append(event)

    file_monitor.on_created = on_created
    file_monitor.start()

    # Create files with different extensions
    test_file1 = tmp_path / "test.txt"
    test_file2 = tmp_path / "test.tmp"
    test_file1.write_text("Test 1")
    test_file2.write_text("Test 2")

    # Wait for events
    time.sleep(1)
    file_monitor.stop()

    assert len(events) == 1
    assert events[0].src_path == str(test_file1)


def test_recursive_watching(file_monitor, tmp_path):
    """Test recursive directory watching."""
    events = []

    def on_created(event):
        events.append(event)

    file_monitor.on_created = on_created
    file_monitor.start()

    # Create a nested directory structure
    nested_dir = tmp_path / "nested" / "dir" / "structure"
    nested_dir.mkdir(parents=True)
    test_file = nested_dir / "test.txt"
    test_file.write_text("Test content")

    # Wait for events
    time.sleep(1)
    file_monitor.stop()

    assert len(events) == 4  # 3 directories + 1 file
    assert str(test_file) in [e.src_path for e in events]


def test_stop_and_start(file_monitor, tmp_path):
    """Test stopping and starting the monitor."""
    events = []

    def on_created(event):
        events.append(event)

    file_monitor.on_created = on_created

    # Start monitor
    file_monitor.start()

    # Create a file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")

    # Wait for event
    time.sleep(1)

    # Stop monitor
    file_monitor.stop()

    # Create another file
    test_file2 = tmp_path / "test2.txt"
    test_file2.write_text("Test content 2")

    # Wait
    time.sleep(1)

    # Start monitor again
    file_monitor.start()

    # Create another file
    test_file3 = tmp_path / "test3.txt"
    test_file3.write_text("Test content 3")

    # Wait for event
    time.sleep(1)
    file_monitor.stop()

    assert len(events) == 2  # Only events while monitor was running
    assert str(test_file) in [e.src_path for e in events]
    assert str(test_file3) in [e.src_path for e in events]
    assert str(test_file2) not in [e.src_path for e in events]
