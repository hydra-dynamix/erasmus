"""
File Watching System
==================

This module provides classes for monitoring file changes in the project.
It includes specialized watchers for different file types and use cases.

Classes:
    BaseWatcher: Generic file system event handler
    MarkdownWatcher: Specialized watcher for markdown documentation files
    ScriptWatcher: Specialized watcher for monitoring script files
    WatcherFactory: Factory class for creating and managing watchers
"""

import os
import time
import logging
import ast
from pathlib import Path
from typing import Dict, Callable, Optional, List
from threading import Thread, Lock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

# Configure logging
logger = logging.getLogger(__name__)

class BaseWatcher(FileSystemEventHandler):
    """Base class for file system event handlers."""
    
    def __init__(self, file_paths: Dict[str, Path], callback: Callable[[str], None]):
        """Initialize the watcher.
        
        Args:
            file_paths: Dictionary mapping file keys to their paths
            callback: Function to call when a file changes
        """
        super().__init__()
        # Store both the original mapping and the normalized paths
        self.file_paths = file_paths
        self.callback = callback  # Store the callback
        self._path_mapping = {str(path.resolve()): key for key, path in file_paths.items()}
        self._event_lock = Lock()
        self._last_events: Dict[str, float] = {}
    
    def _should_process_event(self, event_path: str) -> bool:
        """Check if an event should be processed based on debouncing.
        
        Args:
            event_path: Path of the file that triggered the event
            
        Returns:
            True if the event should be processed, False otherwise
        """
        with self._event_lock:
            current_time = time.time()
            last_time = self._last_events.get(event_path, 0)
            
            # Debounce events within 0.1 seconds
            if current_time - last_time < 0.1:
                return False
            
            self._last_events[event_path] = current_time
            return True
    
    def _get_file_key(self, file_path: str) -> Optional[str]:
        """Get the file key for a given path.
        
        Args:
            file_path: Path to look up
            
        Returns:
            File key if found, None otherwise
        """
        try:
            resolved_path = str(Path(file_path).resolve())
            return self._path_mapping.get(resolved_path)
        except Exception:
            return None
    
    def _handle_event(self, event: FileSystemEvent) -> None:
        """Handle a file system event.
        
        Args:
            event: The file system event to handle
        """
        if event.is_directory:
            return
        
        file_path = event.src_path
        if not self._should_process_event(file_path):
            return
        
        file_key = self._get_file_key(file_path)
        if file_key is None:
            return
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                if self._validate_content(content):
                    self.callback(file_key)
            else:
                # For deletion events, we still want to notify
                self.callback(file_key)
        except Exception as e:
            logger.error(f"Error handling event for {file_path}: {e}")
    
    def _validate_content(self, content: str) -> bool:
        """Validate file content.
        
        Args:
            content: Content to validate
            
        Returns:
            True if content is valid, False otherwise
        """
        return True
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        self._handle_event(event)
    
    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        self._handle_event(event)
    
    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        self._handle_event(event)
    
    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file movement events."""
        self._handle_event(event)

class MarkdownWatcher(BaseWatcher):
    """Specialized watcher for markdown documentation files."""
    
    def _validate_content(self, content: str) -> bool:
        """Validate markdown content.
        
        Args:
            content: Content to validate
            
        Returns:
            True if content is valid markdown, False otherwise
        """
        # Basic markdown validation
        lines = content.split("\n")
        if not lines:
            return False
        
        # Check for title
        if not lines[0].startswith("# "):
            return False
        
        return True

class ScriptWatcher(BaseWatcher):
    """Specialized watcher for script files."""
    
    def __init__(self, script_path: Path, callback: Callable[[str], None]):
        """Initialize the script watcher.
        
        Args:
            script_path: Path to the script file to watch
            callback: Function to call when the script changes
        """
        script_path = Path(script_path)
        if not str(script_path).endswith('.py'):
            raise ValueError("Script path must end with .py")
        
        # Use the script name without extension as the key
        script_key = script_path.stem
        super().__init__({script_key: script_path}, callback)
    
    def _validate_content(self, content: str) -> bool:
        """Validate Python script content.
        
        Args:
            content: Content to validate
            
        Returns:
            True if content is valid Python, False otherwise
        """
        try:
            ast.parse(content)
            return True
        except SyntaxError:
            return False

def run_observer(observer: Observer):
    """Run an observer in a separate thread.
    
    Args:
        observer: Observer to run
    """
    observer.start()
    try:
        while observer.is_alive():
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def create_file_watchers(setup_files: Dict[str, Path], 
                        update_callback: Callable[[str], None],
                        script_path: Path,
                        restart_callback: Callable[[str], None]) -> tuple[Observer, Observer]:
    """Create and configure file watchers.
    
    Args:
        setup_files: Dictionary mapping file keys to their paths
        update_callback: Callback for file updates
        script_path: Path to the script file
        restart_callback: Callback for script restarts
        
    Returns:
        Tuple of (markdown_observer, script_observer)
    """
    # Create watchers
    markdown_watcher = MarkdownWatcher(setup_files, update_callback)
    script_watcher = ScriptWatcher(script_path, restart_callback)
    
    # Create observers
    markdown_observer = Observer()
    script_observer = Observer()
    
    # Schedule watchers
    markdown_observer.schedule(markdown_watcher, str(script_path.parent), recursive=False)
    script_observer.schedule(script_watcher, str(script_path.parent), recursive=False)
    
    return markdown_observer, script_observer

class WatcherFactory:
    """Factory class for creating and managing watchers."""
    
    def __init__(self):
        """Initialize the factory."""
        self.observers: List[Observer] = []
    
    def create_markdown_watcher(self, file_paths: Dict[str, Path], callback: Callable[[str], None]) -> MarkdownWatcher:
        """Create a markdown watcher.
        
        Args:
            file_paths: Dictionary mapping file keys to their paths
            callback: Function to call when files change
            
        Returns:
            Configured MarkdownWatcher
        """
        return MarkdownWatcher(file_paths, callback)
    
    def create_script_watcher(self, script_path: Path, callback: Callable[[str], None]) -> ScriptWatcher:
        """Create a script watcher.
        
        Args:
            script_path: Path to the script file
            callback: Function to call when the script changes
            
        Returns:
            Configured ScriptWatcher
        """
        return ScriptWatcher(script_path, callback)
    
    def create_observer(self, watcher: FileSystemEventHandler, directory: str) -> Observer:
        """Create and configure an observer.
        
        Args:
            watcher: Event handler to use
            directory: Directory to watch
            
        Returns:
            Configured Observer
        """
        observer = Observer()
        observer.schedule(watcher, directory, recursive=False)
        observer.start()
        self.observers.append(observer)
        return observer
    
    def start_all(self) -> None:
        """Start all observers."""
        for observer in self.observers:
            if not observer.is_alive():
                observer.start()
    
    def stop_all(self) -> None:
        """Stop all observers."""
        for observer in self.observers:
            observer.stop()
            observer.join()
        self.observers.clear()
