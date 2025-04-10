# Erasmus API Reference

## Overview

Erasmus is a context tracking and injection system designed to enhance AI-powered development environments. This API reference provides detailed information about the core interfaces and classes.

## Core Components

### 1. Task Management

#### `Task` Class
Located in: `erasmus/core/task.py`

```python
class Task:
    """Represents a task with lifecycle management and metadata."""
    
    def __init__(self, description: str, status: TaskStatus = TaskStatus.PENDING)
    def update_status(self, new_status: TaskStatus)
    def add_note(self, note: str)
    def serialize() -> Dict[str, Any]
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> Task
```

#### `TaskManager` Class
Located in: `erasmus/core/task.py`

```python
class TaskManager:
    """Manages a collection of tasks with advanced tracking capabilities."""
    
    def add_task(self, description: str) -> Task
    def get_task(self, task_id: str) -> Optional[Task]
    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]
    def update_task_status(self, task_id: str, status: TaskStatus)
```

### 2. File Watching System

#### `BaseWatcher` Class
Located in: `erasmus/core/watcher.py`

```python
class BaseWatcher(FileSystemEventHandler):
    """Base class for file system event monitoring."""
    
    def on_created(self, event)
    def on_modified(self, event)
    def on_deleted(self, event)
    def on_moved(self, event)
```

#### Specialized Watchers
- `MarkdownWatcher`: Extends `BaseWatcher` for Markdown file monitoring
- `ScriptWatcher`: Extends `BaseWatcher` for script file monitoring

### 3. Git Integration

#### `GitManager` Class
Located in: `erasmus/git/manager.py`

```python
class GitManager:
    """Manages Git repository operations and commit workflows."""
    
    def stage_all_changes() -> bool
    def commit_changes(message: str) -> bool
    def get_repository_state() -> Dict[str, Any]
```

### 4. File Synchronization

#### `FileSynchronizer` Class
Located in: `erasmus/sync/file_sync.py`

```python
class FileSynchronizer:
    """Manages file synchronization across different contexts."""
    
    async def start()
    async def stop()
    async def sync_all()
    async def sync_file(filename: str)
    async def get_sync_status() -> Dict[str, Dict]
```

## Configuration and Environment

### Environment Variables

- `IDE_ENV`: Current IDE environment
- `OPENAI_API_KEY`: OpenAI API credentials
- `OPENAI_BASE_URL`: API endpoint
- `OPENAI_MODEL`: AI model selection

## Error Handling

### Common Exceptions

- `FileNotFoundError`: Raised when a tracked file is missing
- `PermissionError`: Indicates insufficient file system permissions
- `RuntimeError`: Generic error for synchronization failures

## Usage Examples

### Task Management

```python
from erasmus.core.task import TaskManager, TaskStatus

# Create a task manager
task_manager = TaskManager()

# Add a new task
task = task_manager.add_task("Implement API documentation")

# Update task status
task_manager.update_task_status(task.id, TaskStatus.IN_PROGRESS)
```

### File Synchronization

```python
import asyncio
from erasmus.sync.file_sync import FileSynchronizer

async def main():
    syncer = FileSynchronizer(workspace_path, rules_dir)
    await syncer.start()
    
    # Synchronize all tracked files
    await syncer.sync_all()
    
    # Get synchronization status
    status = await syncer.get_sync_status()
    print(status)
    
    await syncer.stop()

asyncio.run(main())
```

## Performance Considerations

- Memory usage is optimized for file synchronization
- Supports tracking and synchronizing multiple file types
- Provides detailed logging for debugging

## Future Roadmap

- Enhanced AI integration
- More sophisticated synchronization strategies
- Expanded IDE support

## Contributing

Please refer to the project's README for contribution guidelines and development setup.
