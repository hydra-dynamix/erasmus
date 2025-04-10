# Core API Documentation

## Context Management

### CursorContextManager

The main class responsible for managing context updates in the cursor IDE environment.

```python
class CursorContextManager:
    def __init__(self, workspace_path: Path):
        """Initialize the CursorContextManager.
        
        Args:
            workspace_path (Path): Path to the workspace root directory
        """

    async def start(self) -> None:
        """Start the context manager.
        
        Initializes all required components:
        - Creates rules directory if it doesn't exist
        - Initializes rules file
        - Starts update processing
        - Starts file watching
        - Initializes sync integration
        """

    async def stop(self) -> None:
        """Stop the context manager.
        
        Cleans up all resources:
        - Stops file watching
        - Cancels all pending tasks
        - Stops sync integration
        """

    async def queue_update(self, component: str, content: Any) -> bool:
        """Queue an update for processing.
        
        Args:
            component (str): Component to update ("architecture", "progress", "tasks")
            content (Any): New content for the component
            
        Returns:
            bool: True if update was successful, False otherwise
            
        Raises:
            RuntimeError: If context manager is not running
        """
```

### SyncIntegration

Handles synchronization between source files and rules.

```python
class SyncIntegration:
    def __init__(self, context_manager: CursorContextManager, workspace_path: Path):
        """Initialize the sync integration.
        
        Args:
            context_manager (CursorContextManager): The context manager instance
            workspace_path (Path): Path to the workspace root
        """

    async def start(self) -> None:
        """Start the sync integration.
        
        - Initializes file watching
        - Performs initial sync of all components
        """

    async def stop(self) -> None:
        """Stop the sync integration.
        
        - Stops file watching
        - Cleans up resources
        """

    async def handle_file_change(self, file_path: Path) -> None:
        """Handle changes to source files.
        
        Args:
            file_path (Path): Path to the changed file
            
        Features:
        - Retries failed updates up to 3 times
        - Uses progressive delays between retries
        - Verifies updates in rules file
        - Protects against task cancellation
        """
```

## File Watching

### BaseWatcher

Base class for file system event handling.

```python
class BaseWatcher(FileSystemEventHandler):
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.
        
        Args:
            event (FileSystemEvent): The file system event
        """

    def handle_event(self, file_key: str) -> None:
        """Handle a specific file event.
        
        Args:
            file_key (str): Identifier for the file
        """
```

### CursorRulesHandler

Handles file system events specifically for rules files.

```python
class CursorRulesHandler(FileSystemEventHandler):
    def __init__(self, manager: CursorContextManager):
        """Initialize the handler.
        
        Args:
            manager (CursorContextManager): The context manager instance
        """

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.
        
        Features:
        - Debounces frequent events
        - Uses thread-safe queues for communication
        - Handles both rules and source file changes
        """
```

## Configuration

### Environment Variables

Required environment variables for the system:

- `IDE_TYPE`: Type of IDE (cursor/windsurf)
- `RULES_DIR`: Directory for rules files (.cursorrules/.windsurf)
- `WORKSPACE_ROOT`: Root directory of the workspace
- `OPENAI_API_KEY`: OpenAI API key for AI features
- `OPENAI_MODEL`: OpenAI model to use

### File Paths

Important file paths in the system:

- `architecture.md`: System architecture documentation
- `progress.md`: Development progress tracking
- `tasks.md`: Task tracking and management
- `.cursorrules/rules.json`: Rules file for cursor IDE

## Error Handling

The system uses a comprehensive error handling approach:

1. **File Operations**
   - Atomic writes using temporary files
   - Proper cleanup of temporary resources
   - Verification of file contents after writes

2. **Update Processing**
   - progressive retry mechanism
   - Timeout handling with configurable limits
   - Event cleanup in finally blocks

3. **Thread Safety**
   - Thread-safe queues for cross-thread communication
   - Proper synchronization locks
   - Task cancellation protection

## Best Practices

1. **Update Processing**
   ```python
   # Queue an update with proper error handling
   try:
       success = await context_manager.queue_update("architecture", content)
       if not success:
           logger.error("Update failed")
   except Exception as e:
       logger.error(f"Error during update: {e}")
   ```

2. **File Watching**
   ```python
   # Set up file watching with proper cleanup
   observer = Observer()
   try:
       observer.schedule(watcher, str(workspace_path), recursive=False)
       observer.start()
       # ... main processing ...
   finally:
       observer.stop()
       observer.join()
   ```

3. **Resource Management**
   ```python
   # Use context managers for proper cleanup
   async with self._sync_lock:
       try:
           # ... operations ...
       finally:
           # ... cleanup ...
   ``` 