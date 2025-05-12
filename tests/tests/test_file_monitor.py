"""Tests for file monitoring functionality."""
import os
import pytest
import tempfile
import time
from watchdog.observers import Observer
from erasmus.file_monitor import FileMonitor, FileEventHandler

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname

@pytest.fixture
def file_monitor(temp_dir):
    """Create a FileMonitor instance for testing."""
    monitor = FileMonitor(temp_dir)
    monitor.start()
    yield monitor
    monitor.stop()

def test_file_monitor_init(temp_dir):
    """Test FileMonitor initialization."""
    monitor = FileMonitor(temp_dir)
    monitor.start()
    try:
        assert monitor.watch_path == temp_dir
        assert isinstance(monitor.observer, Observer)
        assert monitor.observer.is_alive()
        assert monitor._is_running
    finally:
        monitor.stop()

def test_file_pattern_matching(temp_dir):
    """Test file pattern matching."""
    monitor = FileMonitor(temp_dir)
    
    # Create test files
    rules_file = os.path.join(temp_dir, ".windsurfrules")
    with open(rules_file, 'w') as f:
        f.write("test")
    
    context_file = os.path.join(temp_dir, "architecture.md")
    with open(context_file, 'w') as f:
        f.write("test")
    
    # Test pattern matching
    assert monitor._matches_rules_file(rules_file)
    assert not monitor._matches_rules_file(context_file)

def test_event_handling(temp_dir):
    """Test file event handling."""
    monitor = FileMonitor(temp_dir)
    monitor.start()
    try:
        # Create a test file
        test_file = os.path.join(temp_dir, ".windsurfrules")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Wait for event processing
        time.sleep(0.2)
        
        # Verify event was processed
        assert test_file in monitor.event_handler.processed_events
    finally:
        monitor.stop()

def test_debouncing(temp_dir):
    """Test event debouncing."""
    monitor = FileMonitor(temp_dir)
    monitor.start()
    try:
        # Create and modify a test file rapidly
        test_file = os.path.join(temp_dir, ".windsurfrules")
        
        # Multiple rapid modifications
        for i in range(5):
            with open(test_file, 'w') as f:
                f.write(f"content {i}")
            time.sleep(0.01)  # Very short delay
        
        # Wait for debounce period
        time.sleep(0.2)
        
        # Verify only one event was processed
        assert len(monitor.event_handler.processed_events) == 1
        assert test_file in monitor.event_handler.processed_events
    finally:
        monitor.stop()

def test_error_handling(temp_dir):
    """Test error handling."""
    nonexistent_path = os.path.join(temp_dir, "nonexistent")
    
    # Try to monitor non-existent directory
    with pytest.raises(FileNotFoundError):
        FileMonitor(nonexistent_path)

def test_lifecycle_management(temp_dir):
    """Test monitor lifecycle."""
    monitor = FileMonitor(temp_dir)
    
    # Test initial state
    assert not monitor._is_running
    assert monitor.observer is None
    
    # Test start
    monitor.start()
    assert monitor._is_running
    assert monitor.observer.is_alive()
    
    # Test stop
    monitor.stop()
    assert not monitor._is_running
    assert monitor.observer is None
    
    # Test restart
    monitor.start()
    assert monitor._is_running
    assert monitor.observer.is_alive()
    monitor.stop() 