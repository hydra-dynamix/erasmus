"""
Task Management System
====================

This module provides classes for managing development tasks and their lifecycle.
It includes functionality for task creation, status updates, and serialization.

Classes:
    TaskStatus: Constants for task states
    Task: Represents a single development task
    TaskManager: Manages a collection of tasks
"""

import time
from typing import Dict, List, Optional

class TaskStatus:
    """
    Task status constants.
    
    This class defines constants representing different states of a task
    throughout its lifecycle. Used by the Task class to track current status.
    """
    PENDING = "pending"       # Task is acknowledged but not started
    IN_PROGRESS = "in_progress"  # Task is actively being worked on
    COMPLETED = "completed"   # Task has been finished
    BLOCKED = "blocked"       # Task is blocked by another task or external factor
    NOT_STARTED = "not_started"  # Task has been created but not scheduled

class Task:
    """
    Represents a single development task with tracking information.
    
    This class provides methods for managing a task's state, including
    serialization/deserialization and metadata tracking. Each task has a
    unique ID, description, status, and timestamps for lifecycle events.
    
    Attributes:
        id (str): Unique identifier for the task
        description (str): Detailed description of the task
        status (str): Current status from TaskStatus constants
        created_at (float): Unix timestamp when task was created
        updated_at (float): Unix timestamp when task was last updated
        completion_time (Optional[float]): Unix timestamp when task was completed
        notes (List[str]): List of additional notes or comments for the task
    """
    def __init__(self, id: str, description: str):
        """
        Initialize a new Task with given ID and description.
        
        Args:
            id (str): Unique identifier for the task
            description (str): Detailed description of what the task involves
        """
        self.id = id
        self.description = description
        self.status = TaskStatus.NOT_STARTED
        self.created_at = time.time()
        self.updated_at = time.time()
        self.completion_time = None
        self.notes = []
        
    def to_dict(self) -> dict:
        """
        Convert task to dictionary representation for serialization.
        
        Returns:
            dict: Dictionary containing all task attributes
        """
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completion_time": self.completion_time,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        """
        Create a Task instance from a dictionary representation.
        
        Args:
            data (dict): Dictionary containing task attributes
            
        Returns:
            Task: New Task instance with restored attributes
        """
        task = cls(data["id"], data["description"])
        task.status = data["status"]
        task.created_at = data["created_at"]
        task.updated_at = data["updated_at"]
        task.completion_time = data["completion_time"]
        task.notes = data["notes"]
        return task

class TaskManager:
    """
    Manages a collection of tasks and provides operations for the task lifecycle.
    
    This class handles creating, retrieving, updating, and listing tasks. It also
    provides serialization/deserialization to integrate with the context tracking
    system.
    
    Attributes:
        tasks (Dict[str, Task]): Dictionary mapping task IDs to Task objects
    """
    def __init__(self, tasks: Optional[Dict[str, dict]] = None):
        """
        Initialize a new TaskManager with optional initial tasks.
        
        Args:
            tasks (Optional[Dict[str, dict]]): Dictionary of tasks to initialize with. Can be
                                   either Task objects or dictionaries to deserialize.
        """
        self.tasks: Dict[str, Task] = {}
        if tasks:
            self.tasks = {
                task_id: Task.from_dict(task_data) if isinstance(task_data, dict) else task_data
                for task_id, task_data in tasks.items()
            }
        
    def add_task(self, description: str) -> Task:
        """
        Add a new task with the given description.
        
        Creates a new Task with an automatically assigned sequential ID and
        adds it to the task collection.
        
        Args:
            description (str): Description of the new task
            
        Returns:
            Task: The newly created Task object
        """
        task_id = str(len(self.tasks) + 1)
        task = Task(task_id, description)
        self.tasks[task_id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Retrieve a task by its ID.
        
        Args:
            task_id (str): ID of the task to retrieve
            
        Returns:
            Optional[Task]: The Task if found, None otherwise
        """
        return self.tasks.get(task_id)
    
    def list_tasks(self, status: Optional[str] = None) -> List[Task]:
        """
        List all tasks, optionally filtered by status.
        
        Args:
            status (Optional[str]): If provided, only tasks with this status
                                  will be returned
                                           
        Returns:
            List[Task]: List of tasks matching the filter criteria
        """
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks
    
    def update_task_status(self, task_id: str, status: str) -> None:
        """
        Update a task's status.
        
        Args:
            task_id (str): ID of the task to update
            status (str): New status to set
        """
        if task := self.get_task(task_id):
            task.status = status
            task.updated_at = time.time()
            if status == TaskStatus.COMPLETED:
                task.completion_time = time.time()
    
    def add_note_to_task(self, task_id: str, note: str) -> None:
        """
        Add a note to a task.
        
        Args:
            task_id (str): ID of the task to add the note to
            note (str): Content of the note to add
        """
        if task := self.get_task(task_id):
            task.notes.append(note)
            task.updated_at = time.time()
    
    @classmethod
    def from_dict(cls, data: Dict[str, dict]) -> 'TaskManager':
        """
        Create a TaskManager from a dictionary representation.
        
        Args:
            data (Dict[str, dict]): Dictionary mapping task IDs to task data dictionaries
            
        Returns:
            TaskManager: New TaskManager instance with restored tasks
        """
        manager = cls()
        if isinstance(data, dict):
            manager.tasks = {
                task_id: Task.from_dict(task_data)
                for task_id, task_data in data.items()
            }
        return manager
