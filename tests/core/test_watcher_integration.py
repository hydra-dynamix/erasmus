"""
Integration Tests for File Watching System
=======================================

This module contains integration tests that verify the complete
file watching system works correctly as a whole.
"""

import os
import time
import threading
from pathlib import Path
import pytest
from watchdog.observers import Observer
from erasmus.core.watcher import WatcherFactory, MarkdownWatcher, ScriptWatcher

@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with test files."""
    # Create directory structure
    docs_dir = tmp_path / "docs"
    scripts_dir = tmp_path / "scripts"
    docs_dir.mkdir()
    scripts_dir.mkdir()
    
    # Create test files
    files = {
        "ARCHITECTURE": docs_dir / "ARCHITECTURE.md",
        "PROGRESS": docs_dir / "PROGRESS.md",
        "script": scripts_dir / "test_script.py"
    }
    
    # Initialize files with content
    files["ARCHITECTURE"].write_text("# Architecture\n\nTest content")
    files["PROGRESS"].write_text("# Progress\n\nTest content")
    files["script"].write_text("print('Hello, World!')")
    
    return tmp_path, files

def test_concurrent_file_updates(temp_workspace):
    """Test handling of concurrent file updates across different watchers."""
    workspace, files = temp_workspace
    events = []
    
    def callback(file_key: str):
        events.append(file_key)
    
    # Create factory and watchers
    factory = WatcherFactory()
    markdown_files = {
        "ARCHITECTURE": files["ARCHITECTURE"],
        "PROGRESS": files["PROGRESS"]
    }
    
    markdown_watcher = factory.create_markdown_watcher(markdown_files, callback)
    script_watcher = factory.create_script_watcher(str(files["script"]), callback)
    
    # Create observers
    factory.create_observer(markdown_watcher, str(workspace / "docs"))
    factory.create_observer(script_watcher, str(workspace / "scripts"))
    
    try:
        # Start watching
        factory.start_all()
        time.sleep(0.1)  # Let observers initialize
        
        # Modify files concurrently
        def update_files():
            files["ARCHITECTURE"].write_text("# Architecture\n\nUpdated content")
            files["PROGRESS"].write_text("# Progress\n\nUpdated content")
            files["script"].write_text("print('Updated!')")
        
        update_thread = threading.Thread(target=update_files)
        update_thread.start()
        update_thread.join()
        
        time.sleep(0.1)  # Wait for events to be processed
        
        # Verify all files were detected
        assert "ARCHITECTURE" in events
        assert "PROGRESS" in events
        assert str(files["script"]) in events
        
    finally:
        factory.stop_all()

def test_error_recovery(temp_workspace):
    """Test system recovery from errors in callbacks."""
    workspace, files = temp_workspace
    processed_files = []
    error_count = 0
    
    def failing_callback(file_key: str):
        nonlocal error_count
        processed_files.append(file_key)
        error_count += 1
        if error_count <= 2:  # Fail first two times
            raise Exception(f"Test error {error_count}")
    
    # Create factory and watchers
    factory = WatcherFactory()
    markdown_watcher = factory.create_markdown_watcher(
        {"ARCHITECTURE": files["ARCHITECTURE"]},
        failing_callback
    )
    
    # Create observer
    factory.create_observer(markdown_watcher, str(workspace / "docs"))
    
    try:
        # Start watching
        factory.start_all()
        time.sleep(0.1)  # Let observers initialize
        
        # Trigger multiple updates
        for i in range(4):
            files["ARCHITECTURE"].write_text(f"# Architecture\n\nUpdate {i}")
            time.sleep(0.1)
        
        # Verify system continued processing after errors
        assert len(processed_files) == 4
        assert all(f == "ARCHITECTURE" for f in processed_files)
        
    finally:
        factory.stop_all()

def test_file_system_events(temp_workspace):
    """Test handling of various file system events."""
    workspace, files = temp_workspace
    events = []
    
    def callback(file_key: str):
        events.append(file_key)
    
    # Create factory and watchers
    factory = WatcherFactory()
    markdown_watcher = factory.create_markdown_watcher(
        {"ARCHITECTURE": files["ARCHITECTURE"]},
        callback
    )
    
    # Create observer
    factory.create_observer(markdown_watcher, str(workspace / "docs"))
    
    try:
        # Start watching
        factory.start_all()
        time.sleep(0.1)  # Let observers initialize
        
        # Test file modification
        files["ARCHITECTURE"].write_text("# Architecture\n\nModified content")
        time.sleep(0.1)
        assert "ARCHITECTURE" in events
        events.clear()
        
        # Test file deletion and recreation
        files["ARCHITECTURE"].unlink()
        time.sleep(0.1)
        assert "ARCHITECTURE" in events
        events.clear()
        
        files["ARCHITECTURE"].write_text("# Architecture\n\nNew file")
        time.sleep(0.1)
        assert "ARCHITECTURE" in events
        events.clear()
        
        # Test file movement
        new_path = workspace / "docs" / "NEW_ARCH.md"
        files["ARCHITECTURE"].rename(new_path)
        time.sleep(0.1)
        assert "ARCHITECTURE" in events
        
    finally:
        factory.stop_all()

def test_watcher_interactions(temp_workspace):
    """Test interactions between different types of watchers."""
    workspace, files = temp_workspace
    markdown_events = []
    script_events = []
    
    def markdown_callback(file_key: str):
        markdown_events.append(file_key)
    
    def script_callback(file_key: str):
        script_events.append(file_key)
    
    # Create factory and watchers
    factory = WatcherFactory()
    markdown_watcher = factory.create_markdown_watcher(
        {"ARCHITECTURE": files["ARCHITECTURE"]},
        markdown_callback
    )
    script_watcher = factory.create_script_watcher(
        str(files["script"]),
        script_callback
    )
    
    # Create observers
    factory.create_observer(markdown_watcher, str(workspace / "docs"))
    factory.create_observer(script_watcher, str(workspace / "scripts"))
    
    try:
        # Start watching
        factory.start_all()
        time.sleep(0.1)  # Let observers initialize
        
        # Test that watchers don't interfere with each other
        files["ARCHITECTURE"].write_text("# Invalid Markdown")  # Should not trigger callback
        files["script"].write_text("invalid python")  # Should not trigger callback
        time.sleep(0.1)
        assert not markdown_events
        assert not script_events
        
        # Test that valid updates work correctly
        files["ARCHITECTURE"].write_text("# Valid\n\nMarkdown")
        files["script"].write_text("print('Valid Python')")
        time.sleep(0.1)
        assert "ARCHITECTURE" in markdown_events
        assert str(files["script"]) in script_events
        
    finally:
        factory.stop_all() 