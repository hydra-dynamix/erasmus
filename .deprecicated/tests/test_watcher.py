import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from watcher import Task, TaskManager, TaskStatus, is_valid_url


def test_task_creation():
    """Test task creation and basic properties."""
    task = Task("1", "Test task description")

    assert task.id == "1"
    assert task.description == "Test task description"
    assert task.status == TaskStatus.NOT_STARTED
    assert task.notes == []

def test_task_status_update():
    """Test updating task status."""
    task = Task("1", "Test task")
    task.status = TaskStatus.IN_progress

    assert task.status == TaskStatus.IN_progress

    task.status = TaskStatus.COMPLETED
    assert task.status == TaskStatus.COMPLETED

def test_task_manager_operations():
    """Test TaskManager basic operations."""
    task_manager = TaskManager()

    # Add task
    task = task_manager.add_task("Test task")
    assert task.id == "1"
    assert task.description == "Test task"

    # Get task
    retrieved_task = task_manager.get_task("1")
    assert retrieved_task == task

    # List tasks
    all_tasks = task_manager.list_tasks()
    assert len(all_tasks) == 1

    # List tasks by status
    task_manager.update_task_status("1", TaskStatus.COMPLETED)
    completed_tasks = task_manager.list_tasks(TaskStatus.COMPLETED)
    assert len(completed_tasks) == 1

def test_task_note_addition():
    """Test adding notes to a task."""
    task_manager = TaskManager()
    task = task_manager.add_task("Test task")

    task_manager.add_note_to_task("1", "First note")
    task_manager.add_note_to_task("1", "Second note")

    retrieved_task = task_manager.get_task("1")
    assert retrieved_task.notes == ["First note", "Second note"]

def test_task_serialization():
    """Test task dictionary conversion and recreation."""
    task_manager = TaskManager()
    task = task_manager.add_task("Test task")
    task.status = TaskStatus.IN_progress
    task.add_note_to_task("Test note")

    # Convert to dict
    task_dict = task.to_dict()

    # Recreate from dict
    recreated_task = Task.from_dict(task_dict)

    assert recreated_task.id == task.id
    assert recreated_task.description == task.description
    assert recreated_task.status == task.status
    assert recreated_task.notes == task.notes

def test_url_validation():
    """Test URL validation function."""
    valid_urls = [
        "https://example.com",
        "http://test.org",
        "https://api.openai.com/v1",
    ]

    invalid_urls = [
        "example.com",
        "ftp://invalid.url",
        "",
        "not a url",
    ]

    for url in valid_urls:
        assert is_valid_url(url), f"URL {url} should be valid"

    for url in invalid_urls:
        assert not is_valid_url(url), f"URL {url} should be invalid"
