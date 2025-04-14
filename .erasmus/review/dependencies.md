# Component Dependencies

## Class Hierarchy

```mermaid
classDiagram
    FileSystemEventHandler <|-- BaseWatcher
    BaseWatcher <|-- MarkdownWatcher
    BaseWatcher <|-- ScriptWatcher
    WatcherFactory --> BaseWatcher
    WatcherFactory --> MarkdownWatcher
    WatcherFactory --> ScriptWatcher
```

## Module Dependencies

```mermaid
graph TD
    A[watcher.py] --> B[watchdog.events]
    A --> C[watchdog.observers]
    A --> D[pathlib]
    A --> E[threading]
    A --> F[rich.console]
    A --> G[erasmus.utils.logging]
```

## File Watching Flow

```mermaid
sequenceDiagram
    participant F as FileSystem
    participant O as Observer
    participant W as Watcher
    participant C as Callback

    F->>O: File Change Event
    O->>W: on_modified/created/deleted
    W->>W: _should_process_event
    W->>W: _get_file_key
    W->>C: Execute Callback
```

## Component Relationships

### BaseWatcher

- **Inherits from**: `FileSystemEventHandler` (watchdog)
- **Used by**: `MarkdownWatcher`, `ScriptWatcher`
- **Dependencies**:
  - `watchdog.events.FileSystemEvent`
  - `watchdog.observers.Observer`
  - `pathlib.Path`
  - `threading.Lock`
  - `rich.console.Console`
  - `erasmus.utils.logging`

### MarkdownWatcher

- **Inherits from**: `BaseWatcher`
- **Used by**: `WatcherFactory`
- **Dependencies**:
  - All BaseWatcher dependencies
  - Git integration (implied)

### ScriptWatcher

- **Inherits from**: `BaseWatcher`
- **Used by**: `WatcherFactory`
- **Dependencies**:
  - All BaseWatcher dependencies
  - Python AST module

### WatcherFactory

- **Creates**: `BaseWatcher`, `MarkdownWatcher`, `ScriptWatcher`
- **Manages**: `Observer` instances
- **Dependencies**:
  - All watcher classes
  - `watchdog.observers.Observer`
