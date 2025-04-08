"""
Tests for File Watching System
============================

This module contains tests for the file watching system components.
"""

import os
import time
from pathlib import Path
import pytest
from watchdog.observers import Observer
from erasmus.core.watcher import BaseWatcher, MarkdownWatcher, ScriptWatcher, create_file_watchers, WatcherFactory
from typing import Optional

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path

@pytest.fixture
def mock_callback():
    """Create a mock callback function that tracks calls."""
    calls = []
    def callback(file_key: str):
        calls.append(file_key)
    callback.calls = calls  # type: ignore
    return callback

@pytest.fixture
def mock_event():
    """Create a mock event with the required attributes."""
    def create_event(src_path: str, is_directory: bool = False, event_type: str = 'modified', dest_path: Optional[str] = None):
        attrs = {
            'src_path': src_path,
            'is_directory': is_directory,
            'event_type': event_type
        }
        if dest_path:
            attrs['dest_path'] = dest_path
        return type('Event', (), attrs)()
    return create_event

@pytest.fixture
def setup_files(temp_dir):
    """Create temporary markdown files for testing."""
    files = {
        "ARCHITECTURE": temp_dir / "ARCHITECTURE.md",
        "PROGRESS": temp_dir / "PROGRESS.md",
        "TASKS": temp_dir / "TASKS.md"
    }
    
    # Create files with content
    for key, path in files.items():
        path.write_text(f"# {key}\n\nTest content for {key}")
    
    return files

@pytest.fixture
def test_script(temp_dir):
    """Create a test script file."""
    script_file = temp_dir / "test_script.py"
    script_file.write_text("print('Hello, World!')")
    return script_file

def test_base_watcher_initialization(temp_dir, mock_callback):
    """Test BaseWatcher initialization and configuration."""
    # Set up test files
    file1 = temp_dir / "test1.txt"
    file2 = temp_dir / "test2.txt"
    file1.touch()
    file2.touch()
    
    # Create file paths mapping
    file_paths = {
        str(file1): "file1",
        str(file2): "file2"
    }
    
    # Create watcher
    watcher = BaseWatcher(file_paths, mock_callback)
    
    # Check initialization
    assert watcher.file_paths == file_paths
    assert watcher.callback == mock_callback
    assert len(mock_callback.calls) == 0

def test_base_watcher_event_handling(temp_dir, mock_callback, mock_event):
    """Test BaseWatcher event handling for different event types."""
    # Set up test file
    test_file = temp_dir / "test.txt"
    test_file.touch()
    
    # Create watcher
    file_paths = {str(test_file): "test_key"}
    watcher = BaseWatcher(file_paths, mock_callback)
    
    # Test modification event
    event = mock_event(str(test_file))
    watcher.on_modified(event)
    assert mock_callback.calls == ["test_key"]
    
    # Test creation event
    mock_callback.calls.clear()
    watcher.on_created(event)
    assert mock_callback.calls == ["test_key"]
    
    # Test deletion event
    mock_callback.calls.clear()
    watcher.on_deleted(event)
    assert mock_callback.calls == ["test_key"]
    
    # Test movement event
    mock_callback.calls.clear()
    new_path = temp_dir / "new.txt"
    move_event = mock_event(str(test_file), dest_path=str(new_path))
    watcher.on_moved(move_event)
    assert mock_callback.calls == ["test_key"]

def test_base_watcher_unknown_file(temp_dir, mock_callback, mock_event):
    """Test BaseWatcher behavior with unknown files."""
    # Set up test file
    test_file = temp_dir / "test.txt"
    test_file.touch()
    unknown_file = temp_dir / "unknown.txt"
    unknown_file.touch()
    
    # Create watcher
    file_paths = {str(test_file): "test_key"}
    watcher = BaseWatcher(file_paths, mock_callback)
    
    # Test event for unknown file
    event = mock_event(str(unknown_file))
    watcher.on_modified(event)
    assert len(mock_callback.calls) == 0

def test_base_watcher_error_handling(temp_dir, mock_callback, mock_event):
    """Test BaseWatcher error handling."""
    # Set up test file
    test_file = temp_dir / "test.txt"
    test_file.touch()
    
    # Create watcher with a callback that raises an exception
    def failing_callback(file_key):
        raise Exception("Test error")
    
    file_paths = {str(test_file): "test_key"}
    watcher = BaseWatcher(file_paths, failing_callback)
    
    # Test that exception in callback is handled gracefully
    event = mock_event(str(test_file))
    watcher.on_modified(event)  # Should not raise exception

def test_markdown_watcher_initialization(setup_files):
    """Test MarkdownWatcher initialization."""
    # Create watcher
    watcher = MarkdownWatcher(setup_files, lambda _: None)
    
    # Check initialization
    assert watcher.file_paths == {str(path): key for key, path in setup_files.items()}
    assert all(str(path).endswith('.md') for path in setup_files.values())

def test_markdown_watcher_event_handling(setup_files, mock_event):
    """Test MarkdownWatcher event handling."""
    # Track which files were modified
    modified_files = []
    def callback(file_key):
        modified_files.append(file_key)
    
    # Create watcher
    watcher = MarkdownWatcher(setup_files, callback)
    
    # Test modification event
    path = setup_files["ARCHITECTURE"]
    event = mock_event(str(path))
    watcher.on_modified(event)
    assert modified_files == ["ARCHITECTURE"]
    
    # Test non-markdown file
    modified_files.clear()
    non_md_file = path.parent / "test.txt"
    non_md_file.touch()
    event = mock_event(str(non_md_file))
    watcher.on_modified(event)
    assert not modified_files
    
    # Test directory event
    modified_files.clear()
    event = mock_event(str(path.parent), is_directory=True)
    watcher.on_modified(event)
    assert not modified_files

def test_markdown_watcher_content_validation(setup_files, mock_event):
    """Test MarkdownWatcher content validation."""
    # Track which files were modified
    modified_files = []
    def callback(file_key):
        modified_files.append(file_key)
    
    # Create watcher
    watcher = MarkdownWatcher(setup_files, callback)
    
    # Test valid markdown content
    path = setup_files["ARCHITECTURE"]
    path.write_text("# Valid Markdown\n\n- List item\n- Another item")
    event = mock_event(str(path))
    watcher.on_modified(event)
    assert modified_files == ["ARCHITECTURE"]
    
    # Test invalid markdown content
    modified_files.clear()
    path.write_text("Not a valid markdown file without headers")
    event = mock_event(str(path))
    watcher.on_modified(event)
    assert not modified_files  # Should not trigger callback for invalid content

def test_script_watcher_initialization(test_script):
    """Test ScriptWatcher initialization."""
    # Create watcher
    watcher = ScriptWatcher(str(test_script), lambda _: None)
    
    # Check initialization
    assert watcher.file_paths == {str(test_script): str(test_script)}
    assert str(test_script).endswith('.py')

def test_script_watcher_event_handling(test_script, mock_event):
    """Test ScriptWatcher event handling."""
    # Track restart events
    restart_count = 0
    def callback(file_key):
        nonlocal restart_count
        restart_count += 1
    
    # Create watcher
    watcher = ScriptWatcher(str(test_script), callback)
    
    # Test modification event
    event = mock_event(str(test_script))
    watcher.on_modified(event)
    assert restart_count == 1
    
    # Test non-script file
    restart_count = 0
    non_script_file = test_script.parent / "test.txt"
    non_script_file.touch()
    event = mock_event(str(non_script_file))
    watcher.on_modified(event)
    assert restart_count == 0
    
    # Test directory event
    event = mock_event(str(test_script.parent), is_directory=True)
    watcher.on_modified(event)
    assert restart_count == 0

def test_script_watcher_content_validation(test_script, mock_event):
    """Test ScriptWatcher content validation."""
    # Track restart events
    restart_count = 0
    def callback(file_key):
        nonlocal restart_count
        restart_count += 1
    
    # Create watcher
    watcher = ScriptWatcher(str(test_script), callback)
    
    # Test valid Python content
    test_script.write_text("def main():\n    print('Hello')\n\nif __name__ == '__main__':\n    main()")
    event = mock_event(str(test_script))
    watcher.on_modified(event)
    assert restart_count == 1
    
    # Test invalid Python content
    restart_count = 0
    test_script.write_text("This is not valid Python code")
    event = mock_event(str(test_script))
    watcher.on_modified(event)
    assert restart_count == 0  # Should not trigger callback for invalid content

def test_script_watcher_error_handling(test_script, mock_event):
    """Test ScriptWatcher error handling."""
    # Track restart events
    restart_count = 0
    def callback(file_key):
        nonlocal restart_count
        restart_count += 1
        raise Exception("Test error")
    
    # Create watcher
    watcher = ScriptWatcher(str(test_script), callback)
    
    # Test that exception in callback is handled gracefully
    event = mock_event(str(test_script))
    watcher.on_modified(event)  # Should not raise exception
    assert restart_count == 1  # Callback should still be called

def test_create_file_watchers(setup_files, test_script):
    """Test creation and configuration of file watchers."""
    # Define callback functions
    def update_callback(file_key):
        pass
    
    def restart_callback(file_key):
        pass
    
    # Create watchers
    markdown_observer, script_observer = create_file_watchers(
        setup_files,
        update_callback,
        str(test_script),
        restart_callback
    )
    
    assert isinstance(markdown_observer, Observer)
    assert isinstance(script_observer, Observer)
    
    # Clean up
    markdown_observer.stop()
    script_observer.stop()

def test_watcher_factory_initialization():
    """Test WatcherFactory initialization and configuration."""
    factory = WatcherFactory()
    assert factory.watchers == {}
    assert factory.observers == []

def test_watcher_factory_create_markdown_watcher(setup_files, mock_callback):
    """Test creation of markdown watcher through factory."""
    factory = WatcherFactory()
    
    # Create markdown watcher
    watcher = factory.create_markdown_watcher(setup_files, mock_callback)
    
    assert isinstance(watcher, MarkdownWatcher)
    assert watcher.file_paths == {str(path): key for key, path in setup_files.items()}
    assert watcher.callback == mock_callback

def test_watcher_factory_create_script_watcher(test_script, mock_callback):
    """Test creation of script watcher through factory."""
    factory = WatcherFactory()
    
    # Create script watcher
    watcher = factory.create_script_watcher(str(test_script), mock_callback)
    
    assert isinstance(watcher, ScriptWatcher)
    assert watcher.file_paths == {str(test_script): str(test_script)}
    assert watcher.callback == mock_callback

def test_watcher_factory_create_observer(temp_dir, mock_callback):
    """Test creation and configuration of observer through factory."""
    factory = WatcherFactory()
    
    # Create a test file and watcher
    test_file = temp_dir / "test.txt"
    test_file.touch()
    watcher = BaseWatcher({str(test_file): "test"}, mock_callback)
    
    # Create observer
    observer = factory.create_observer(watcher, str(temp_dir))
    
    assert isinstance(observer, Observer)
    assert not observer.is_alive()  # Observer should not be started yet
    assert len(observer._handlers) == 1  # Observer should have one handler scheduled

def test_watcher_factory_start_and_stop(setup_files, test_script, mock_callback):
    """Test starting and stopping watchers through factory."""
    factory = WatcherFactory()
    
    # Create watchers
    markdown_watcher = factory.create_markdown_watcher(setup_files, mock_callback)
    script_watcher = factory.create_script_watcher(str(test_script), mock_callback)
    
    # Create and start observers
    factory.create_observer(markdown_watcher, str(setup_files["ARCHITECTURE"].parent))
    factory.create_observer(script_watcher, str(test_script.parent))
    
    # Start all observers
    factory.start_all()
    assert all(observer.is_alive() for observer in factory.observers)
    
    # Stop all observers
    factory.stop_all()
    assert all(not observer.is_alive() for observer in factory.observers)

def test_watcher_factory_error_handling(temp_dir):
    """Test error handling in watcher factory."""
    factory = WatcherFactory()
    
    # Test invalid directory
    with pytest.raises(ValueError):
        factory.create_observer(BaseWatcher({}, lambda _: None), "/nonexistent/path")
    
    # Test invalid watcher type
    with pytest.raises(TypeError):
        factory.create_observer(None, str(temp_dir))  # type: ignore
