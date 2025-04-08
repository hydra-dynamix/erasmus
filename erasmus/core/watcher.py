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
            bool: True if the event should be processed
        """
        current_time = time.time()
        with self._event_lock:
            last_time = self._last_events.get(event_path, 0)
            if current_time - last_time < 0.05:  # 50ms debounce
                return False
            self._last_events[event_path] = current_time
            return True
    
    def _get_file_key(self, file_path: str) -> Optional[str]:
        """Get the key for a file path."""
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
            
        file_key = self._get_file_key(event.src_path)
        if file_key and self._should_process_event(event.src_path):
            try:
                if os.path.exists(event.src_path):
                    with open(event.src_path, 'r') as f:
                        content = f.read()
                    if self._validate_content(content):
                        self.callback(file_key)
                else:
                    # For deletion events, we still want to notify
                    self.callback(file_key)
            except Exception as e:
                logging.error(f"Error handling event for {event.src_path}: {e}")
    
    def _validate_content(self, content: str) -> bool:
        """Validate file content. Override in subclasses.
        
        Args:
            content: The file content to validate
            
        Returns:
            bool: True if content is valid
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
        """Handle file move events."""
        self._handle_event(event)

class MarkdownWatcher(BaseWatcher):
    """Specialized watcher for markdown documentation files.
    
    This class extends BaseWatcher to provide specific handling for Markdown files.
    It validates file content and only triggers callbacks for valid Markdown files.
    
    Args:
        file_paths: A dictionary mapping file paths to their keys
        callback: A function to call when a watched file is modified
    """
    
    def _validate_content(self, content: str) -> bool:
        """Validate markdown content.
        
        Args:
            content: The markdown content to validate
            
        Returns:
            bool: True if content appears to be valid markdown
        """
        # More thorough markdown validation:
        # 1. Must have non-empty content
        if not content.strip():
            return False
            
        # 2. Must have at least one proper heading
        lines = content.split('\n')
        has_heading = False
        for line in lines:
            if line.strip().startswith('# '):  # Must have space after #
                has_heading = True
                break
                
        # 3. Must have some content after the heading
        has_content = len([l for l in lines if l.strip() and not l.strip().startswith('#')]) > 0
        
        return has_heading and has_content

class ScriptWatcher(BaseWatcher):
    """Specialized watcher for Python script files.
    
    This class extends BaseWatcher to provide specific handling for Python script files.
    It validates file content and only triggers callbacks for valid Python files.
    
    Args:
        script_path: Path to the script file to watch
        callback: A function to call when the script is modified
    """
    
    def __init__(self, script_path: str, callback: Callable[[str], None]):
        """Initialize the script watcher.
        
        Args:
            script_path: Path to the script file to watch
            callback: Function to call when the script changes
        """
        if not script_path.endswith('.py'):
            logging.warning(f"Script path {script_path} does not have .py extension")
        super().__init__({script_path: Path(script_path)}, callback)
    
    def _validate_content(self, content: str) -> bool:
        """Validate Python script content.
        
        Args:
            content: The Python code to validate
            
        Returns:
            bool: True if content is valid Python code
        """
        if not content.strip():
            return False
            
        try:
            ast.parse(content)
            return True
        except SyntaxError:
            return False

def run_observer(observer: Observer):
    """
    Run a watchdog Observer in a blocking manner.
    
    This helper function starts an Observer and blocks until the Observer
    is stopped. It's typically used to run Observers in separate threads.
    
    Args:
        observer (Observer): The watchdog Observer to run
    """
    observer.start()
    observer.join()

def create_file_watchers(setup_files: Dict[str, Path], 
                        update_callback: Callable[[str], None],
                        script_path: str,
                        restart_callback: Callable[[str], None]) -> tuple[Observer, Observer]:
    """
    Create and configure file watchers for both markdown files and scripts.
    
    This function sets up the necessary watchers and observers for monitoring
    both documentation files and script files. It creates separate observers
    for each watcher type to allow independent control.
    
    Args:
        setup_files (Dict[str, Path]): Dictionary mapping file keys to their paths
        update_callback (Callable[[str], None]): Function to call when a markdown file changes
        script_path (str): Path to the script file to monitor
        restart_callback (Callable[[str], None]): Function to call when the script changes
        
    Returns:
        tuple[Observer, Observer]: Tuple containing (markdown_observer, script_observer)
    """
    # Create markdown watcher
    markdown_watcher = MarkdownWatcher(setup_files, update_callback)
    markdown_observer = Observer()
    markdown_observer.schedule(markdown_watcher, str(Path.cwd()), recursive=False)
    
    # Create script watcher
    script_watcher = ScriptWatcher(script_path, restart_callback)
    script_observer = Observer()
    script_observer.schedule(script_watcher, os.path.dirname(os.path.abspath(script_path)), recursive=False)
    
    return markdown_observer, script_observer

class WatcherFactory:
    """Factory class for creating and managing file watchers.
    
    This class provides a centralized way to create and manage different types
    of file watchers and their associated observers. It handles the lifecycle
    of watchers and observers, including creation, starting, and stopping.
    """
    
    def __init__(self):
        """Initialize the factory."""
        self.watchers: Dict[str, FileSystemEventHandler] = {}
        self.observers: List[Observer] = []
    
    def create_markdown_watcher(self, file_paths: Dict[str, Path], callback: Callable[[str], None]) -> MarkdownWatcher:
        """Create a new MarkdownWatcher instance.
        
        Args:
            file_paths: Dictionary mapping file keys to their paths
            callback: Function to call when a markdown file changes
            
        Returns:
            MarkdownWatcher: The created watcher instance
        """
        watcher = MarkdownWatcher(file_paths, callback)
        self.watchers['markdown'] = watcher
        return watcher
    
    def create_script_watcher(self, script_path: str, callback: Callable[[str], None]) -> ScriptWatcher:
        """Create a new ScriptWatcher instance.
        
        Args:
            script_path: Path to the script file to watch
            callback: Function to call when the script changes
            
        Returns:
            ScriptWatcher: The created watcher instance
        """
        watcher = ScriptWatcher(script_path, callback)
        self.watchers['script'] = watcher
        return watcher
    
    def create_observer(self, watcher: FileSystemEventHandler, directory: str) -> Observer:
        """Create and configure a new Observer for a watcher.
        
        Args:
            watcher: The file system event handler to use
            directory: The directory to watch
            
        Returns:
            Observer: The configured observer instance
            
        Raises:
            ValueError: If the directory does not exist
            TypeError: If the watcher is invalid
        """
        if not isinstance(watcher, FileSystemEventHandler):
            raise TypeError("Invalid watcher type")
        
        if not os.path.exists(directory):
            raise ValueError(f"Directory does not exist: {directory}")
        
        observer = Observer()
        observer.schedule(watcher, directory, recursive=False)
        self.observers.append(observer)
        return observer
    
    def start_all(self) -> None:
        """Start all registered observers."""
        for observer in self.observers:
            if not observer.is_alive():
                observer.start()
    
    def stop_all(self) -> None:
        """Stop all registered observers."""
        for observer in self.observers:
            if observer.is_alive():
                observer.stop()
                observer.join()
