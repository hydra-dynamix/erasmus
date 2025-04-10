"""
Tests for Task Management System
==============================

This module contains tests for the Task and TaskManager classes.
"""

import time
import pytest
from erasmus.core.task import Task, TaskManager, TaskStatus

def test_task_creation():
    """Test basic task creation and initialization."""
    task = Task("1", "Test task")
    assert task.id == "1"
    assert task.description == "Test task"
    assert task.status == TaskStatus.NOT_STARTED
    assert task.notes == []
    assert task.completion_time is None
    assert isinstance(task.created_at, float)
    assert isinstance(task.updated_at, float)

def test_task_serialization():
    """Test task serialization and deserialization."""
    task = Task("1", "Test task")
    task.status = TaskStatus.IN_progress
    task.notes.append("Test note")
    
    # Serialize
    data = task.to_dict()
    assert data["id"] == "1"
    assert data["description"] == "Test task"
    assert data["status"] == TaskStatus.IN_progress
    assert data["notes"] == ["Test note"]
    
    # Deserialize
    new_task = Task.from_dict(data)
    assert new_task.id == task.id
    assert new_task.description == task.description
    assert new_task.status == task.status
    assert new_task.notes == task.notes
    assert new_task.created_at == task.created_at
    assert new_task.updated_at == task.updated_at

def test_task_manager_creation():
    """Test TaskManager initialization."""
    manager = TaskManager()
    assert manager.tasks == {}
    
    # Initialize with tasks
    tasks = {
        "1": {"id": "1", "description": "Task 1", "status": TaskStatus.PENDING,
              "created_at": time.time(), "updated_at": time.time(),
              "completion_time": None, "notes": []}
    }
    manager = TaskManager(tasks)
    assert len(manager.tasks) == 1
    assert isinstance(manager.tasks["1"], Task)

def test_task_manager_add_task():
    """Test adding tasks to TaskManager."""
    manager = TaskManager()
    task = manager.add_task("Test task")
    assert task.id == "1"
    assert task.description == "Test task"
    assert len(manager.tasks) == 1
    assert manager.tasks["1"] == task

def test_task_manager_get_task():
    """Test retrieving tasks from TaskManager."""
    manager = TaskManager()
    task = manager.add_task("Test task")
    
    # Get existing task
    retrieved = manager.get_task("1")
    assert retrieved == task
    
    # Get non-existent task
    assert manager.get_task("999") is None

def test_task_manager_list_tasks():
    """Test listing tasks with optional status filter."""
    manager = TaskManager()
    task1 = manager.add_task("Task 1")
    task2 = manager.add_task("Task 2")
    task3 = manager.add_task("Task 3")
    
    # Update task statuses
    task1.status = TaskStatus.COMPLETED
    task2.status = TaskStatus.IN_progress
    task3.status = TaskStatus.COMPLETED
    
    # List all tasks
    all_tasks = manager.list_tasks()
    assert len(all_tasks) == 3
    
    # List completed tasks
    completed = manager.list_tasks(TaskStatus.COMPLETED)
    assert len(completed) == 2
    assert all(t.status == TaskStatus.COMPLETED for t in completed)
    
    # List in-progress tasks
    in_progress = manager.list_tasks(TaskStatus.IN_progress)
    assert len(in_progress) == 1
    assert in_progress[0].status == TaskStatus.IN_progress

def test_task_manager_update_status():
    """Test updating task status."""
    manager = TaskManager()
    task = manager.add_task("Test task")
    
    # Update to in-progress
    manager.update_task_status("1", TaskStatus.IN_progress)
    assert task.status == TaskStatus.IN_progress
    assert task.completion_time is None
    
    # Update to completed
    manager.update_task_status("1", TaskStatus.COMPLETED)
    assert task.status == TaskStatus.COMPLETED
    assert task.completion_time is not None

def test_task_manager_add_note():
    """Test adding notes to tasks."""
    manager = TaskManager()
    task = manager.add_task("Test task")
    
    # Add a note
    manager.add_note_to_task("1", "Test note")
    assert len(task.notes) == 1
    assert task.notes[0] == "Test note"
    
    # Add another note
    manager.add_note_to_task("1", "Another note")
    assert len(task.notes) == 2
    assert task.notes[1] == "Another note"
