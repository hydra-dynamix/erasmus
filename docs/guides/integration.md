# Integration Guide

## Overview

This guide explains how to integrate the Erasmus context management system into your development environment. Erasmus provides real-time context tracking and synchronization for AI-powered development tools.

## Quick Start

1. **Installation**
   ```bash
   pip install erasmus-context
   ```

2. **Basic Configuration**
   ```python
   from erasmus.ide import CursorContextManager
   from pathlib import Path

   # Initialize context manager
   context_manager = CursorContextManager(Path.cwd())
   
   # Start the manager
   await context_manager.start()
   ```

## Environment Setup

1. **Required Environment Variables**
   Create a `.env` file in your project root:
   ```env
   IDE_TYPE=cursor
   RULES_DIR=.cursorrules
   WORKSPACE_ROOT=/path/to/workspace
   OPENAI_API_KEY=your-api-key
   OPENAI_MODEL=gpt-4
   ```

2. **File Structure**
   ```
   workspace/
   ├── .cursorrules/
   │   └── rules.json
   ├── architecture.md
   ├── progress.md
   └── tasks.md
   ```

## Context Management

### Setting Up File Watching

```python
from erasmus.core import BaseWatcher
from watchdog.events import FileSystemEvent

class CustomWatcher(BaseWatcher):
    def handle_event(self, file_key: str) -> None:
        # Custom event handling logic
        pass

# Initialize watcher
watcher = CustomWatcher()
observer.schedule(watcher, str(workspace_path), recursive=False)
```

### Handling Updates

```python
# Queue an update
success = await context_manager.queue_update(
    component="architecture",
    content="# Updated architecture"
)

# Handle the result
if success:
    logger.info("Update successful")
else:
    logger.error("Update failed")
```

## Synchronization

### File Change Handling

```python
from erasmus.ide import SyncIntegration

# Initialize sync integration
sync = SyncIntegration(context_manager, workspace_path)

# Start synchronization
await sync.start()

# Handle file changes
await sync.handle_file_change(Path("architecture.md"))
```

### Error Recovery

```python
try:
    await sync.handle_file_change(file_path)
except Exception as e:
    logger.error(f"Error handling file change: {e}")
    # Implement recovery logic
```

## Performance Optimization

### Update Batching

For non-critical updates, use the batch processing feature:

```python
# Configure batch delay
context_manager.batch_delay = 0.5  # 500ms

# Queue multiple updates
for component, content in updates:
    await context_manager.queue_update(component, content)
```

### Resource Management

```python
async def manage_resources():
    try:
        # Start components
        await context_manager.start()
        await sync.start()
        
        # Main processing
        while running:
            await process_updates()
            
    finally:
        # Cleanup
        await sync.stop()
        await context_manager.stop()
```

## Thread Safety

### Cross-Thread Communication

```python
# Use thread-safe queues for communication
from queue import Queue
from threading import Lock

class ThreadSafeHandler:
    def __init__(self):
        self._queue = Queue()
        self._lock = Lock()
        
    def handle_event(self, event):
        with self._lock:
            self._queue.put(event)
```

### Async Operations

```python
# Use asyncio primitives for async operations
async def process_events():
    async with lock:
        while not queue.empty():
            event = await queue.get()
            await process_event(event)
```

## Error Handling

### Retry Mechanism

```python
async def with_retries(operation, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return await operation()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(0.5 * (attempt + 1))
```

### File Operations

```python
def safe_write(path: Path, content: str):
    temp_path = path.with_suffix('.tmp')
    try:
        temp_path.write_text(content)
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
```

## Testing

### Unit Tests

```python
async def test_context_manager():
    # Set up
    context_manager = CursorContextManager(tmp_path)
    await context_manager.start()
    
    try:
        # Test update
        success = await context_manager.queue_update(
            "architecture",
            "# Test Content"
        )
        assert success
        
        # Verify update
        rules = json.loads(
            (tmp_path / ".cursorrules" / "rules.json").read_text()
        )
        assert rules["architecture"] == "# Test Content"
        
    finally:
        await context_manager.stop()
```

### Integration Tests

```python
async def test_sync_integration():
    # Set up components
    context_manager = CursorContextManager(workspace_path)
    sync = SyncIntegration(context_manager, workspace_path)
    
    await context_manager.start()
    await sync.start()
    
    try:
        # Test file change
        content = "# Updated Content"
        architecture_file.write_text(content)
        await sync.handle_file_change(architecture_file)
        
        # Verify synchronization
        rules = json.loads(rules_file.read_text())
        assert rules["architecture"] == content
        
    finally:
        await sync.stop()
        await context_manager.stop()
```

## Troubleshooting

### Common Issues

1. **File Lock Errors**
   ```python
   # Solution: Use atomic operations
   temp_file = path.with_suffix('.tmp')
   temp_file.write_text(content)
   temp_file.replace(path)
   ```

2. **Event Loop Errors**
   ```python
   # Solution: Ensure proper event loop usage
   loop = asyncio.get_event_loop()
   if not loop.is_running():
       loop.run_until_complete(async_operation())
   ```

3. **Thread Safety Issues**
   ```python
   # Solution: Use proper synchronization
   async with self._lock:
       await self._queue.put(item)
   ```

### Debugging

1. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. Monitor file operations:
   ```python
   def debug_file_op(func):
       def wrapper(*args, **kwargs):
           logger.debug(f"File operation: {func.__name__}")
           return func(*args, **kwargs)
       return wrapper
   ```

3. Track update processing:
   ```python
   async def debug_update(component: str, content: str):
       logger.debug(f"Processing update: {component}")
       result = await context_manager.queue_update(component, content)
       logger.debug(f"Update result: {result}")
       return result
   ``` 