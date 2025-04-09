"""
File Synchronization Module
=========================

This module handles synchronization of project files to the rules directory,
ensuring that context files are properly copied and updated.
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Set, Optional, Callable
from datetime import datetime
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ..utils.file import safe_read_file, safe_write_file
from ..core.watcher import BaseWatcher

logger = logging.getLogger(__name__)

class FileChangeHandler(FileSystemEventHandler):
    """Handles file system events for tracked files."""
    
    def __init__(self, filename: str, callback: Callable[[str], None]):
        """Initialize the handler.
        
        Args:
            filename: Name of the file to track
            callback: Function to call when file changes
        """
        super().__init__()
        self.filename = filename
        self.callback = callback
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and Path(event.src_path).name == self.filename:
            self.callback(self.filename)

class FileSynchronizer:
    """Manages synchronization of project files to the rules directory."""
    
    TRACKED_FILES = {
        'ARCHITECTURE.md': 'architecture',
        'TASKS.md': 'tasks',
        'PROGRESS.md': 'progress'
    }
    
    def __init__(self, workspace_path: Path, rules_dir: Path):
        """Initialize the FileSynchronizer.
        
        Args:
            workspace_path: Root path of the workspace
            rules_dir: Path to the rules directory (.cursorrules)
        """
        self.workspace_path = workspace_path
        self.rules_dir = rules_dir
        self._handlers: Dict[str, FileChangeHandler] = {}
        self._observers: Dict[str, Observer] = {}
        self._sync_lock = asyncio.Lock()
        self._last_sync: Dict[str, float] = {}
        self._debounce_delay = 0.5  # seconds
        self._pending_syncs: Set[str] = set()
        self._running = False
        self._sync_task = None
        self._event_loop = None
    
    async def start(self):
        """Start the file synchronizer."""
        if self._running:
            return
            
        self._running = True
        self._event_loop = asyncio.get_running_loop()
        
        # Create rules directory if it doesn't exist
        self.rules_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize rules file if it doesn't exist
        rules_file = self.rules_dir / "rules.json"
        if not rules_file.exists():
            safe_write_file(rules_file, "{}")
        
        # Set up handlers and observers for each tracked file
        for filename in self.TRACKED_FILES:
            source_file = self.workspace_path / filename
            if source_file.exists():
                # Create and configure the handler
                handler = FileChangeHandler(filename, lambda f=filename: 
                    asyncio.run_coroutine_threadsafe(
                        self._handle_file_change(f), 
                        self._event_loop
                    )
                )
                self._handlers[filename] = handler
                
                # Set up observer for this file
                observer = Observer()
                observer.schedule(handler, str(source_file.parent), recursive=False)
                observer.daemon = True
                observer.start()
                self._observers[filename] = observer
        
        # Start processing sync tasks
        self._sync_task = asyncio.create_task(self._process_syncs())
    
    async def stop(self):
        """Stop the file synchronizer."""
        if not self._running:
            return
            
        self._running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            
        # Stop observers
        for observer in self._observers.values():
            observer.stop()
            observer.join()
            
        # Clean up
        self._handlers.clear()
        self._observers.clear()
        self._event_loop = None
    
    async def sync_all(self):
        """Synchronize all tracked files."""
        for filename in self.TRACKED_FILES:
            await self.sync_file(filename)
    
    async def sync_file(self, filename: str):
        """Synchronize a specific file.
        
        Args:
            filename: Name of the file to synchronize
            
        Raises:
            FileNotFoundError: If the source file does not exist or is not tracked
            PermissionError: If there are permission issues
            RuntimeError: If there are other synchronization errors
        """
        if filename not in self.TRACKED_FILES:
            logger.warning(f"Attempted to sync untracked file: {filename}")
            raise FileNotFoundError(f"File is not tracked: {filename}")
            
        source_file = self.workspace_path / filename
        if not source_file.exists():
            # Remove from rules if file doesn't exist
            rules_file = self.rules_dir / "rules.json"
            async with self._sync_lock:
                try:
                    current_rules = json.loads(safe_read_file(rules_file)) if rules_file.exists() else {}
                    component = self.TRACKED_FILES[filename]
                    if component in current_rules:
                        del current_rules[component]
                        safe_write_file(rules_file, json.dumps(current_rules, indent=2))
                except Exception as e:
                    logger.error(f"Error cleaning up missing file {filename}: {e}")
            raise FileNotFoundError(f"Source file does not exist: {filename}")
            
        try:
            # Read source file content
            content = safe_read_file(source_file)
            if content is None:
                raise RuntimeError(f"Unable to read file: {filename}")
                
            # Update rules file
            rules_file = self.rules_dir / "rules.json"
            async with self._sync_lock:
                try:
                    current_rules = json.loads(safe_read_file(rules_file)) if rules_file.exists() else {}
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in rules file")
                    current_rules = {}
                
                # Update the specific component
                current_rules[self.TRACKED_FILES[filename]] = content
                
                # Write updated rules
                try:
                    safe_write_file(rules_file, json.dumps(current_rules, indent=2))
                    self._last_sync[filename] = datetime.now().timestamp()
                    logger.debug(f"Successfully synchronized {filename}")
                except PermissionError as e:
                    raise PermissionError(f"Permission denied writing to rules file: {e}")
                except Exception as e:
                    raise RuntimeError(f"Failed to sync file {filename}: {e}")
                
        except (PermissionError, RuntimeError) as e:
            logger.error(f"Error synchronizing {filename}: {e}")
            raise
    
    async def _handle_file_change(self, filename: str):
        """Handle a file change event.
        
        Args:
            filename: Name of the changed file
        """
        logger.debug(f"File change detected: {filename}")
        self._pending_syncs.add(filename)
    
    async def _process_syncs(self):
        """Process pending file synchronizations."""
        while self._running:
            try:
                if self._pending_syncs:
                    # Get current pending syncs
                    to_sync = self._pending_syncs.copy()
                    self._pending_syncs.clear()
                    
                    # Wait for debounce delay
                    await asyncio.sleep(self._debounce_delay)
                    
                    # Sync each file
                    for filename in to_sync:
                        await self.sync_file(filename)
                        
                await asyncio.sleep(0.1)  # Brief sleep to prevent busy loop
                
            except Exception as e:
                logger.error(f"Error processing syncs: {e}")
                await asyncio.sleep(1.0)  # Longer sleep on error
    
    async def get_sync_status(self) -> Dict[str, dict]:
        """Get the last sync time for each tracked file.
        
        Returns:
            Dict mapping filenames to status information including:
                - last_sync: timestamp of last sync
                - exists: whether the file exists
                - synced: whether the file has been synced
        """
        status = {}
        rules_file = self.rules_dir / "rules.json"
        
        try:
            current_rules = json.loads(safe_read_file(rules_file)) if rules_file.exists() else {}
        except json.JSONDecodeError:
            logger.error("Invalid JSON in rules file")
            current_rules = {}
        
        for filename, component in self.TRACKED_FILES.items():
            source_file = self.workspace_path / filename
            
            if source_file.exists():
                source_content = safe_read_file(source_file)
                is_synced = (
                    component in current_rules and
                    current_rules[component] == source_content
                )
                status[filename] = {
                    'last_sync': self._last_sync.get(filename) if is_synced else None,
                    'exists': True,
                    'synced': is_synced
                }
            else:
                status[filename] = {
                    'last_sync': None,
                    'exists': False,
                    'synced': False
                }
        return status
        
    async def cleanup(self):
        """Clean up files that no longer exist in workspace.
        
        Raises:
            PermissionError: If there are permission issues writing to rules file
            RuntimeError: If there are other cleanup errors
        """
        try:
            rules_file = self.rules_dir / "rules.json"
            if not rules_file.exists():
                return
                
            async with self._sync_lock:
                try:
                    current_rules = json.loads(safe_read_file(rules_file))
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in rules file")
                    return
                    
                # Check each tracked file
                for filename, component in self.TRACKED_FILES.items():
                    source_file = self.workspace_path / filename
                    if not source_file.exists() and component in current_rules:
                        del current_rules[component]
                        if filename in self._last_sync:
                            del self._last_sync[filename]
                            
                # Write updated rules
                try:
                    safe_write_file(rules_file, json.dumps(current_rules, indent=2))
                except PermissionError as e:
                    raise PermissionError(f"Permission denied writing to rules file: {e}")
                    
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise RuntimeError(f"Failed to clean up rules: {e}")