# Erasmus: AI Context Watcher for Development

## Overview
Erasmus is a context tracking and injection system designed to enhance AI-powered development environments. It monitors project state and documentation, providing dynamic context updates to AI-powered IDEs.

## System Architecture

### 1. Core Components

#### 1.1 Task Management System
- Task tracking and lifecycle management
- Status tracking (pending, in-progress, completed, blocked)
- Task metadata and notes
- Serialization/deserialization support

#### 1.2 File Watching System
- Real-time file monitoring
- Event handling for file modifications
- Support for different file types (Markdown, Scripts)
- Callback system for file changes

#### 1.3 Git Integration
- Atomic commit management
- Repository state tracking
- Commit message generation and validation
- Branch management

#### 1.4 Context Management
- Context file handling
- Rules management (global and context-specific)
- Dynamic context updates
- File content synchronization

#### 1.5 Environment Management
- IDE environment detection
- Credentials management
- Configuration handling
- Environment variable management

### 2. Package Structure

```
src/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── task.py           # Task and TaskManager classes
│   ├── watcher.py        # File watching system
│   └── context.py        # Context management
├── git/
│   ├── __init__.py
│   └── manager.py        # Git integration
├── utils/
│   ├── __init__.py
│   ├── env.py           # Environment management
│   └── file.py          # File operations
└── cli/
    ├── __init__.py
    └── commands.py      # CLI interface
```

### 3. Key Interfaces

#### 3.1 Task Management
```python
class TaskManager:
    def add_task(description: str) -> Task
    def get_task(task_id: str) -> Optional[Task]
    def list_tasks(status: Optional[TaskStatus]) -> List[Task]
    def update_task_status(task_id: str, status: TaskStatus) -> None
```

#### 3.2 File Watching
```python
class BaseWatcher(FileSystemEventHandler):
    def on_modified(event) -> None
    def handle_event(file_key: str) -> None
```

#### 3.3 Git Operations
```python
class GitManager:
    def stage_all_changes() -> bool
    def commit_changes(message: str) -> bool
    def get_repository_state() -> dict
```

### 4. Configuration

#### 4.1 Environment Variables
- IDE_ENV: Current IDE environment
- OPENAI_API_KEY: OpenAI API credentials
- OPENAI_BASE_URL: API endpoint
- OPENAI_MODEL: AI model selection

#### 4.2 File Paths
- ARCHITECTURE.md: System architecture
- PROGRESS.md: Development progress
- TASKS.md: Task tracking
- .erasmus/: Configuration directory

### 5. Dependencies
- openai: AI integration
- rich: Console output
- watchdog: File system monitoring
- python-dotenv: Environment configuration

## Development Guidelines

### Code Style
- Type hints for all function parameters and returns
- Comprehensive docstrings for classes and methods
- Error handling with specific exceptions
- Logging for debugging and monitoring

### Testing Strategy
- Unit tests for core components
- Integration tests for file operations
- Mock testing for external services
- Coverage reporting

### Documentation
- Inline documentation for complex logic
- README.md for setup and usage
- API documentation for public interfaces
- Change log for version tracking