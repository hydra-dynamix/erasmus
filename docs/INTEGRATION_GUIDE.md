# Erasmus Integration Guide

## 1. Installation

### Prerequisites
- Python 3.9+
- pip or poetry
- Git

### Install via pip
```bash
pip install erasmus
```

### Install via poetry
```bash
poetry add erasmus
```

## 2. Configuration

### Environment Setup
Create a `.env` file in your project root:

```bash
# IDE Environment
IDE_ENV=cursor  # or windsurf

# Optional AI Integration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
```

### Project Structure
```
your_project/
├── .erasmus/
│   ├── rules.json
│   └── config.yaml
├── .env
└── pyproject.toml
```

## 3. Basic Usage

### Task Management
```python
from erasmus.core.task import TaskManager, TaskStatus

# Initialize task manager
task_manager = TaskManager()

# Create a task
task = task_manager.add_task("Implement feature X")

# Update task status
task_manager.update_task_status(task.id, TaskStatus.IN_progress)
```

### File Synchronization
```python
import asyncio
from erasmus.sync.file_sync import FileSynchronizer

async def sync_project():
    syncer = FileSynchronizer(
        workspace_path='/path/to/project',
        rules_dir='/path/to/.erasmus'
    )
    await syncer.start()
    await syncer.sync_all()
    
    # Check synchronization status
    status = await syncer.get_sync_status()
    print(status)
```

## 4. Advanced Configuration

### Custom Watchers
```python
from erasmus.core.watcher import BaseWatcher

class CustomWatcher(BaseWatcher):
    def on_modified(self, event):
        # Custom modification handling
        pass
```

### Git Integration
```python
from erasmus.git.manager import GitManager

git_manager = GitManager()
git_manager.stage_all_changes()
git_manager.commit_changes("Implement new features")
```

## 5. IDE-Specific Setup

### cursor IDE
- Automatically detects cursor workspace
- Uses `.erasmus/rules.json` for configuration

### windsurf IDE
- Set `IDE_ENV=windsurf` in `.env`
- Configure workspace in `.erasmus/config.yaml`

## 6. Troubleshooting

### Common Issues
- **Missing Files**: Ensure tracked files exist
- **Sync Failures**: Check file permissions
- **Configuration Errors**: Validate `.env` and `.erasmus/config.yaml`

### Logging
Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 7. Performance Optimization

### Memory Management
- Use `sync_all()` for batch synchronization
- Monitor memory usage with provided benchmarks
- Avoid synchronizing large binary files

## 8. Security Considerations

- Keep `.env` file private
- Use environment variables for sensitive information
- Regularly update Erasmus to latest version

## 9. Contributing

- Report issues on GitHub
- Follow PEP 8 style guidelines
- Write comprehensive tests for new features

## 10. License

Erasmus is open-source software released under [LICENSE TYPE].
