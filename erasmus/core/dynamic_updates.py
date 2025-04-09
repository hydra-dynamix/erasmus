"""Dynamic context updates management.

This module provides functionality for managing dynamic updates to context files,
including change detection, validation, and rollback support.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .rules import Rule, RulesManager


@dataclass
class Change:
    """Represents a single change to a context file."""

    file_path: Path
    content: str
    change_type: str  # 'modification', 'creation', 'deletion'
    metadata: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    old_content: Optional[str] = None
    new_content: Optional[str] = None

    def __post_init__(self):
        """Post-initialization processing."""
        # Convert file_path to Path if it's a string
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)
        
        # Set new_content to content if not provided
        if self.new_content is None:
            self.new_content = self.content
        
        # Set timestamp if provided in metadata
        if 'timestamp' in self.metadata:
            self.timestamp = self.metadata['timestamp']
        
        # Set old_content to content if not provided and change_type is modification
        if self.old_content is None and self.change_type == 'modification':
            self.old_content = self.content

    def __eq__(self, other):
        """Compare two changes for equality."""
        if not isinstance(other, Change):
            return False
        return (
            self.file_path == other.file_path and
            self.content == other.content and
            self.change_type == other.change_type and
            self.metadata == other.metadata and
            self.timestamp == other.timestamp and
            self.old_content == other.old_content and
            self.new_content == other.new_content
        )


class ChangeTracker:
    """Tracks changes to context files and maintains change history."""

    def __init__(self, max_history: int = 100):
        """Initialize the change tracker.

        Args:
            max_history: Maximum number of changes to keep in history
        """
        self.changes: List[Change] = []
        self.max_history = max_history
        self._current_batch: List[Change] = []

    @property
    def history(self) -> List[Change]:
        """Get the change history.

        Returns:
            List of changes, most recent first
        """
        return list(reversed(self.changes + self._current_batch))

    def start_batch(self) -> None:
        """Start a new batch of changes."""
        self._current_batch = []

    def end_batch(self) -> None:
        """End the current batch and add changes to history."""
        self.changes.extend(self._current_batch)
        self._current_batch = []
        self._trim_history()

    def add_change(self, change: Change) -> None:
        """Add a change to the current batch.

        Args:
            change: The change to add
        """
        self._current_batch.append(change)
        # If not in a batch, add directly to history
        if not self._current_batch:
            self.changes.append(change)
            self._trim_history()

    def get_history(self, file_path: Optional[Path] = None) -> List[Change]:
        """Get change history, optionally filtered by file path.

        Args:
            file_path: Optional path to filter changes by

        Returns:
            List of changes, most recent first
        """
        all_changes = self.changes + self._current_batch
        if file_path:
            return [c for c in reversed(all_changes) if c.file_path == file_path]
        return list(reversed(all_changes))

    def rollback(self, file_path: Path, steps: int = 1) -> Optional[Change]:
        """Rollback changes for a file.

        Args:
            file_path: Path of the file to rollback
            steps: Number of changes to rollback

        Returns:
            The change that was rolled back to, or None if no changes found
        """
        file_changes = [c for c in self.changes if c.file_path == file_path]
        if not file_changes:
            return None

        # Get the change to rollback to
        target_change = file_changes[-min(steps, len(file_changes))]
        
        # Remove all changes after the target
        self.changes = [c for c in self.changes if c.timestamp <= target_change.timestamp]
        self._current_batch = []
        
        return target_change

    def rollback_to(self, timestamp: datetime) -> bool:
        """Rollback changes to a specific timestamp.

        Args:
            timestamp: The timestamp to rollback to

        Returns:
            True if rollback was successful
        """
        if not self.changes:
            return False

        if timestamp > datetime.now():
            raise ValueError("Cannot rollback to future timestamp")

        # Find all changes before or at the target timestamp
        self.changes = [c for c in self.changes if c.timestamp <= timestamp]
        self._current_batch = []
        return True

    def _trim_history(self) -> None:
        """Trim the change history to the maximum size."""
        if len(self.changes) > self.max_history:
            # Sort by timestamp and keep the most recent changes
            self.changes.sort(key=lambda x: x.timestamp)
            self.changes = self.changes[-self.max_history:]
            # Also trim the current batch if needed
            if len(self._current_batch) > self.max_history:
                self._current_batch.sort(key=lambda x: x.timestamp)
                self._current_batch = self._current_batch[-self.max_history:]


class DynamicUpdates:
    """Manages dynamic updates to context files."""

    def __init__(self, rules_dir: Path):
        """Initialize the dynamic updates manager.

        Args:
            rules_dir: Directory containing rule files
        """
        self.rules_dir = Path(rules_dir)
        self.rule_manager = RulesManager(rules_dir)
        self.change_tracker = ChangeTracker()
        self._watched_files: Set[Path] = set()
        self._file_content_cache: Dict[Path, str] = {}

    def watch_file(self, file_path: Path) -> None:
        """Start watching a file for changes.

        Args:
            file_path: Path to the file to watch
        """
        file_path = Path(file_path)
        self._watched_files.add(file_path)
        if file_path.exists():
            self._file_content_cache[file_path] = file_path.read_text()

    def unwatch_file(self, file_path: Path) -> None:
        """Stop watching a file for changes.

        Args:
            file_path: Path to the file to unwatch
        """
        file_path = Path(file_path)
        self._watched_files.discard(file_path)
        self._file_content_cache.pop(file_path, None)

    def check_for_updates(self) -> List[Change]:
        """Check all watched files for updates.

        Returns:
            List of detected changes
        """
        changes: List[Change] = []
        self.change_tracker.start_batch()

        for file_path in self._watched_files:
            if not file_path.exists():
                if file_path in self._file_content_cache:
                    # File was deleted
                    changes.append(Change(
                        file_path=str(file_path),
                        content=self._file_content_cache[file_path],
                        change_type='deletion',
                        metadata={'reason': 'file_deleted'}
                    ))
                    del self._file_content_cache[file_path]
                continue

            try:
                current_content = file_path.read_text()
                if file_path not in self._file_content_cache:
                    # New file
                    changes.append(Change(
                        file_path=str(file_path),
                        content=current_content,
                        change_type='creation',
                        metadata={'reason': 'file_created'}
                    ))
                elif current_content != self._file_content_cache[file_path]:
                    # File was modified
                    changes.append(Change(
                        file_path=str(file_path),
                        content=current_content,
                        change_type='modification',
                        metadata={'reason': 'content_changed'},
                        old_content=self._file_content_cache[file_path]
                    ))
                self._file_content_cache[file_path] = current_content
            except Exception as e:
                changes.append(Change(
                    file_path=str(file_path),
                    content=self._file_content_cache.get(file_path, ""),
                    change_type='error',
                    metadata={'reason': 'read_error', 'error': str(e)}
                ))

        for change in changes:
            self.change_tracker.add_change(change)
        self.change_tracker.end_batch()

        return changes

    def validate_changes(self, changes: List[Change]) -> Tuple[bool, List[str]]:
        """Validate a list of changes against applicable rules.

        Args:
            changes: List of changes to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors: List[str] = []
        is_valid = True

        for change in changes:
            if change.change_type == 'error':
                errors.append(f"Error reading {change.file_path}: {change.metadata.get('error', 'Unknown error')}")
                is_valid = False
                continue

            if change.new_content is None:
                continue

            # Get applicable rules for the file
            rules = self.rule_manager.get_rules_for_file(change.file_path)
            if not rules:
                continue

            # Validate the new content
            for rule in rules:
                if not rule.validate(change.new_content):
                    errors.append(f"Rule violation in {change.file_path}: {rule.description}")
                    is_valid = False

        return is_valid, errors

    def apply_changes(self, changes: List[Change]) -> bool:
        """Apply a list of changes to the filesystem.

        Args:
            changes: List of changes to apply

        Returns:
            True if all changes were applied successfully
        """
        is_valid, errors = self.validate_changes(changes)
        if not is_valid:
            return False

        for change in changes:
            try:
                if change.change_type == 'deletion':
                    change.file_path.unlink(missing_ok=True)
                elif change.new_content is not None:
                    change.file_path.write_text(change.new_content)
                    self._file_content_cache[change.file_path] = change.new_content
            except Exception as e:
                errors.append(f"Error applying change to {change.file_path}: {str(e)}")
                return False

        return True

    def rollback_changes(self, file_path: Path, steps: int = 1) -> bool:
        """Rollback changes for a specific file.

        Args:
            file_path: Path to the file to rollback
            steps: Number of changes to rollback

        Returns:
            True if rollback was successful
        """
        file_path = Path(file_path)
        target_change = self.change_tracker.rollback(file_path, steps)
        if not target_change:
            return False

        try:
            if target_change.old_content is None:
                # File was created, so delete it
                file_path.unlink(missing_ok=True)
            else:
                # Restore the old content
                file_path.write_text(target_change.old_content)
                self._file_content_cache[file_path] = target_change.old_content
            return True
        except Exception:
            return False


@dataclass
class Update:
    """Represents a proposed update to a file."""

    file_path: Path
    content: str
    update_type: str  # 'modify', 'create', 'delete'
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization processing."""
        # Convert file_path to Path if it's a string
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)


class UpdateValidator:
    """Validates proposed updates before they are applied."""

    def __init__(self, rules_manager: RulesManager):
        """Initialize the update validator.

        Args:
            rules_manager: Rules manager instance for validation
        """
        self.rules_manager = rules_manager

    def validate_update(self, update: Update) -> bool:
        """Validate a proposed update.

        Args:
            update: The update to validate

        Returns:
            True if the update is valid, False otherwise
        """
        if update.update_type == 'delete':
            return True  # Deletions are always valid

        if not update.content:
            return False  # Empty content is invalid

        if update.update_type == 'modify':
            if not update.file_path.exists():
                return False  # Can't modify non-existent file

        # Get applicable rules for the file
        rules = self.rules_manager.get_rules_for_file(update.file_path)
        if not rules:
            return True  # No rules means valid

        # Validate content against rules
        for rule in rules:
            if not rule.validate(update.content):
                return False

        return True 