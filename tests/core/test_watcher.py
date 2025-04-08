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
from src.core.watcher import BaseWatcher, MarkdownWatcher, ScriptWatcher, create_file_watchers

def test_base_watcher(temp_dir):
    """Test BaseWatcher initialization and file monitoring."""
    # Set up test files
    file1 = temp_dir / "test1.txt"
    file2 = temp_dir / "test2.txt"
    file1.touch()
    file2.touch()
    
    # Track which files were modified
    modified_files = []
    def callback(file_key):
        modified_files.append(file_key)
    
    # Create watcher
    file_paths = {
        str(file1): "file1",
        str(file2): "file2"
    }
    watcher = BaseWatcher(file_paths, callback)
    
    # Simulate file modification event
    event = type('Event', (), {'src_path': str(file1)})()
    watcher.on_modified(event)
    
    assert len(modified_files) == 1
    assert modified_files[0] == "file1"

def test_markdown_watcher(setup_files):
    """Test MarkdownWatcher initialization and monitoring."""
    # Track which files were modified
    modified_files = []
    def callback(file_key):
        modified_files.append(file_key)
    
    # Create watcher
    watcher = MarkdownWatcher(setup_files, callback)
    
    # Simulate file modification events
    for path in setup_files.values():
        event = type('Event', (), {'src_path': str(path)})()
        watcher.on_modified(event)
    
    assert len(modified_files) == len(setup_files)
    assert set(modified_files) == set(setup_files.keys())

def test_script_watcher(test_script):
    """Test ScriptWatcher initialization and monitoring."""
    # Track restart events
    restart_count = 0
    def callback(file_key):
        nonlocal restart_count
        restart_count += 1
    
    # Create watcher
    watcher = ScriptWatcher(str(test_script), callback)
    
    # Simulate script modification
    event = type('Event', (), {'src_path': str(test_script)})()
    watcher.on_modified(event)
    
    assert restart_count == 1

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
