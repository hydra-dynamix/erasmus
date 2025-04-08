"""
File Watching System
==================

This module provides classes for monitoring file changes in the project.
It includes specialized watchers for different file types and use cases.

Classes:
    BaseWatcher: Generic file system event handler
    MarkdownWatcher: Specialized watcher for markdown documentation files
    ScriptWatcher: Specialized watcher for monitoring script files
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, Callable
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logger = logging.getLogger(__name__)

class BaseWatcher(FileSystemEventHandler):
    """
    Base file system event handler for monitoring file changes.
    
    This class extends watchdog's FileSystemEventHandler to provide a configurable
    file monitoring system. It maps specific file paths to identifiers and executes
    a callback function when any of the monitored files are modified.
    
    The watcher normalizes all file paths to absolute paths to ensure consistent
    path comparison across different operating systems and environments.
    
    Attributes:
        file_paths (Dict[str, str]): Dictionary mapping normalized absolute file paths
            to their logical identifiers/keys
        callback (Callable): Function to call when a watched file is modified.
            The callback receives the file identifier as its argument.
    """
    def __init__(self, file_paths: Dict[str, str], callback: Callable[[str], None]):
        """
        Initialize a new file watcher.
        
        Args:
            file_paths (Dict[str, str]): Dictionary mapping file paths to their
                logical identifiers/keys. Keys in this dictionary will be used
                to identify which file triggered the callback.
            callback (Callable[[str], None]): Function to call when a watched file is modified.
                The callback receives the file identifier as its argument.
        """
        super().__init__()
        # Normalize and store the file paths
        self.file_paths = {str(Path(fp).resolve()): key for fp, key in file_paths.items()}
        self.callback = callback
        logger.info(f"Watching files: {list(self.file_paths.values())}")

    def on_modified(self, event):
        """
        Handle file modification events.
        
        This method is automatically called by the watchdog Observer when a file
        in the watched directory is modified. It checks if the modified file is
        one of the tracked files and executes the callback if it is.
        
        Args:
            event (FileSystemEvent): Event object containing information about
                the file system change
        """
        path = str(Path(event.src_path).resolve())
        if path in self.file_paths:
            file_key = self.file_paths[path]
            logger.info(f"Detected update in {file_key}")
            self.callback(file_key)

class MarkdownWatcher(BaseWatcher):
    """
    Specialized watcher for monitoring markdown documentation files.
    
    This watcher subclass is specifically designed to monitor the project's
    documentation files (ARCHITECTURE.md, PROGRESS.md, TASKS.md, etc.).
    When any of these files change, it automatically updates the context
    tracking system and creates a Git commit to track the changes.
    
    The file mapping is built automatically from the SETUP_FILES dictionary,
    which defines the standard set of project documentation files.
    """
    def __init__(self, setup_files: Dict[str, Path], update_callback: Callable[[str], None]):
        """
        Initialize a new MarkdownWatcher.
        
        Args:
            setup_files (Dict[str, Path]): Dictionary mapping file keys to their paths
            update_callback (Callable[[str], None]): Function to call when a file is modified
        """
        # Build the file mapping from setup_files
        file_mapping = {str(path.resolve()): name for name, path in setup_files.items()}
        super().__init__(file_mapping, update_callback)

class ScriptWatcher(BaseWatcher):
    """
    Specialized watcher for monitoring the script file itself.
    
    This watcher is responsible for detecting changes to Python script files
    and triggering appropriate actions when changes are detected. This allows
    for automatic reloading or restarting of scripts when they are modified.
    """
    def __init__(self, script_path: str, restart_callback: Callable[[str], None]):
        """
        Initialize a new ScriptWatcher.
        
        Args:
            script_path (str): Path to the script file to monitor
            restart_callback (Callable[[str], None]): Function to call when the script changes
        """
        # We only want to watch the script file itself
        file_mapping = {os.path.abspath(script_path): "Script File"}
        super().__init__(file_mapping, restart_callback)

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
