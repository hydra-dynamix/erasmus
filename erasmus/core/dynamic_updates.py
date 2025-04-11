"""
Dynamic Update System for Context Management
==========================================

This module provides functionality for handling dynamic updates to the context
management system, including change tracking, validation, and rollback support.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class ChangeRecord:
    """Records a single change to the context system."""
    timestamp: datetime
    component: str
    previous_value: Any
    new_value: Any
    source: str
    metadata: dict[str, Any]

class DynamicUpdateManager:
    """
    Manages dynamic updates to the context management system.
    
    This class handles:
    - Change detection and validation
    - Update application with rollback support
    - Change history tracking
    - Update notifications
    """

    def __init__(self, context_dir: Path):
        """
        Initialize the dynamic update manager.

        Args:
            context_dir: Directory containing context files
        """
        self.context_dir = Path(context_dir)
        self.changes_file = self.context_dir / "changes.json"
        self.changes_file.touch(exist_ok=True)
        self._load_changes()

    def _load_changes(self) -> None:
        """Load the change history from disk."""
        try:
            if self.changes_file.stat().st_size > 0:
                content = self.changes_file.read_text()
                raw_changes = json.loads(content)
                self.changes = [
                    ChangeRecord(
                        timestamp=datetime.fromisoformat(c["timestamp"]),
                        component=c["component"],
                        previous_value=c["previous_value"],
                        new_value=c["new_value"],
                        source=c["source"],
                        metadata=c["metadata"],
                    )
                    for c in raw_changes
                ]
            else:
                self.changes = []
        except Exception as e:
            logger.error(f"Failed to load changes: {e}")
            self.changes = []

    def _save_changes(self) -> None:
        """Save the change history to disk."""
        try:
            changes_data = [
                {
                    "timestamp": c.timestamp.isoformat(),
                    "component": c.component,
                    "previous_value": c.previous_value,
                    "new_value": c.new_value,
                    "source": c.source,
                    "metadata": c.metadata,
                }
                for c in self.changes
            ]
            self.changes_file.write_text(json.dumps(changes_data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save changes: {e}")

    def detect_changes(self, component: str, new_value: Any) -> tuple[bool, dict[str, Any] | None]:
        """
        Detect if there are meaningful changes to a component.

        Args:
            component: Name of the component being checked
            new_value: New value to compare against current state

        Returns:
            Tuple of (has_changes: bool, diff: Optional[Dict[str, Any]])
        """
        try:
            # Get the most recent change for this component
            current_value = None
            for change in reversed(self.changes):
                if change.component == component:
                    current_value = change.new_value
                    break

            if current_value is None:
                return True, {"type": "initial", "component": component}

            # Compare values based on type
            if isinstance(new_value, (str, int, float, bool)):
                has_changed = new_value != current_value
                diff = {"type": "value_change", "old": current_value, "new": new_value} if has_changed else None
            elif isinstance(new_value, (list, dict)):
                has_changed = json.dumps(new_value, sort_keys=True) != json.dumps(current_value, sort_keys=True)
                diff = {"type": "structure_change", "component": component} if has_changed else None
            else:
                has_changed = new_value != current_value
                diff = {"type": "unknown_change", "component": component} if has_changed else None

            return has_changed, diff

        except Exception as e:
            logger.error(f"Error detecting changes: {e}")
            return False, None

    def validate_update(self, component: str, new_value: Any) -> tuple[bool, str | None]:
        """
        Validate a proposed update before applying it.

        Args:
            component: Name of the component to update
            new_value: New value to validate

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        try:
            # Basic validation
            if component.strip() == "":
                return False, "Component name cannot be empty"

            if new_value is None:
                return False, "New value cannot be None"

            # Ensure serializable
            try:
                json.dumps(new_value)
            except (TypeError, ValueError):
                return False, "New value must be JSON serializable"

            # Type-specific validation
            if not isinstance(new_value, (str, int, float, bool, list, dict)):
                return False, "New value must be a basic type (str, int, float, bool) or a container (list, dict)"

            # Component-specific validation
            if component == "tasks":
                if not isinstance(new_value, dict):
                    return False, "tasks must be a dictionary"
                for task_id, task_data in new_value.items():
                    if not isinstance(task_data, dict):
                        return False, f"Task {task_id} data must be a dictionary"
                    if "description" not in task_data:
                        return False, f"Task {task_id} missing description"

            return True, None

        except Exception as e:
            logger.error(f"Error validating update: {e}")
            return False, str(e)

    def apply_update(self, component: str, new_value: Any, source: str, metadata: dict[str, Any] = None) -> bool:
        """
        Apply an update to a component with rollback support.

        Args:
            component: Name of the component to update
            new_value: New value to apply
            source: Source of the update (e.g., "file_watcher", "user", "system")
            metadata: Optional metadata about the update

        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Validate the update
            is_valid, error = self.validate_update(component, new_value)
            if not is_valid:
                logger.error(f"Invalid update: {error}")
                return False

            # Detect changes
            has_changes, diff = self.detect_changes(component, new_value)
            if not has_changes:
                logger.info(f"No changes detected for {component}")
                return True

            # Get current value for rollback
            current_value = None
            for change in reversed(self.changes):
                if change.component == component:
                    current_value = change.new_value
                    break

            # Create change record
            change = ChangeRecord(
                timestamp=datetime.now(),
                component=component,
                previous_value=current_value,
                new_value=new_value,
                source=source,
                metadata=metadata or {},
            )

            # Apply the change
            self.changes.append(change)
            self._save_changes()

            logger.info(f"Successfully updated {component}")
            return True

        except Exception as e:
            logger.error(f"Error applying update: {e}")
            return False

    def rollback_last_change(self, component: str) -> bool:
        """
        Rollback the last change for a component.

        Args:
            component: Name of the component to rollback

        Returns:
            bool: True if rollback was successful, False otherwise
        """
        try:
            # Find the last two changes for this component
            last_change = None
            previous_change = None

            for change in reversed(self.changes):
                if change.component == component:
                    if last_change is None:
                        last_change = change
                    else:
                        previous_change = change
                        break

            if last_change is None:
                logger.error(f"No changes found for {component}")
                return False

            # Remove the last change
            self.changes.remove(last_change)

            # If there was a previous change, that becomes the current state
            if previous_change is not None:
                logger.info(f"Rolled back {component} to previous state")
            else:
                logger.info(f"Rolled back {component} to initial state")

            self._save_changes()
            return True

        except Exception as e:
            logger.error(f"Error rolling back change: {e}")
            return False

    def get_change_history(self, component: str | None = None, limit: int = 10) -> list[ChangeRecord]:
        """
        Get the change history for a component.

        Args:
            component: Optional component to filter by
            limit: Maximum number of changes to return

        Returns:
            List of ChangeRecord objects
        """
        if component:
            filtered_changes = [c for c in self.changes if c.component == component]
        else:
            filtered_changes = self.changes

        return filtered_changes[-limit:]
