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
        "architecture": docs_dir / "architecture.md",
        "progress": docs_dir / "progress.md",
        "script": scripts_dir / "test_script.py"
    }
    
    # Initialize files with content
    files["architecture"].write_text("# architecture\n\nTest content")
    files["progress"].write_text("# progress\n\nTest content")
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
        "architecture": files["architecture"],
        "progress": files["progress"]
    }
    
    markdown_watcher = factory.create_markdown_watcher(markdown_files, callback)
    script_watcher = factory.create_script_watcher(files["script"], callback)
    
    # Create observers
    factory.create_observer(markdown_watcher, str(workspace / "docs"))
    factory.create_observer(script_watcher, str(workspace / "scripts"))
    
    try:
        # Start watching
        factory.start_all()
        time.sleep(0.1)  # Let observers initialize
        
        # Update markdown file
        files["architecture"].write_text("# architecture\n\nUpdated content")
        time.sleep(0.1)
        assert "architecture" in events
        events.clear()
        
        # Update script file
        files["script"].write_text("print('Updated script')")
        time.sleep(0.1)
        assert "test_script" in events
        
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
        {"architecture": files["architecture"]},
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
            files["architecture"].write_text(f"# architecture\n\nUpdate {i}")
            time.sleep(0.2)  # Increase delay to ensure events are processed
        
        # Verify system continued processing after errors
        assert len(processed_files) >= 3  # At least 3 events should be processed
        
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
        {"architecture": files["architecture"]},
        callback
    )
    
    # Create observer
    factory.create_observer(markdown_watcher, str(workspace / "docs"))
    
    try:
        # Start watching
        factory.start_all()
        time.sleep(0.1)  # Let observers initialize
        
        # Test file modification
        files["architecture"].write_text("# architecture\n\nModified content")
        time.sleep(0.2)
        assert "architecture" in events
        events.clear()
        
        # Test file deletion and recreation
        files["architecture"].unlink()
        time.sleep(0.2)
        assert "architecture" in events
        events.clear()
        
        # Test file recreation
        files["architecture"].write_text("# architecture\n\nRecreated content")
        time.sleep(0.2)
        assert "architecture" in events
        
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
        {"architecture": files["architecture"]},
        markdown_callback
    )
    script_watcher = factory.create_script_watcher(
        files["script"],
        script_callback
    )
    
    # Create observers
    factory.create_observer(markdown_watcher, str(workspace / "docs"))
    factory.create_observer(script_watcher, str(workspace / "scripts"))
    
    try:
        # Start watching
        factory.start_all()
        time.sleep(0.1)  # Let observers initialize
        
        # Update both files
        files["architecture"].write_text("# architecture\n\nUpdated content")
        files["script"].write_text("print('Updated script')")
        time.sleep(0.2)
        
        # Verify correct callbacks were triggered
        assert "architecture" in markdown_events
        assert "test_script" in script_events
        assert "architecture" not in script_events
        assert "test_script" not in markdown_events
        
    finally:
        factory.stop_all() 