# Erasmus Dependency Graph

## Component Dependencies

```mermaid
graph TD
    subgraph "Entry Points"
        A[__main__.py] --> B[erasmus.py]
        B --> C[cli/commands.py]
    end

    subgraph "Core Components"
        D[core/context.py] --> E[utils/paths.py]
        D --> F[utils/logging.py]
        G[core/watcher.py] --> F
        G --> E
        H[core/task.py] --> F
        H --> E
    end

    subgraph "CLI Components"
        C --> I[cli/protocol.py]
        C --> J[cli/setup.py]
        I --> K[utils/protocols/manager.py]
        I --> D
    end

    subgraph "Git Components"
        L[git/manager.py] --> F
        L --> E
        C --> L
    end

    subgraph "Protocol Components"
        K --> M[utils/protocols/base.py]
        K --> N[utils/path_manager.py]
        K --> F
    end

    subgraph "Utility Components"
        E --> O[utils/env.py]
        E --> P[utils/env_manager.py]
        F --> Q[utils/file.py]
        F --> R[utils/file_ops.py]
    end

    subgraph "IDE Integration"
        S[ide/cursor_integration.py] --> F
        S --> E
        T[ide/sync_integration.py] --> F
        T --> E
    end

    subgraph "Sync Components"
        U[sync/file_sync.py] --> F
        U --> E
    end
```

## File Dependencies

### Entry Points

- `__main__.py`: Main entry point for the Erasmus package
- `erasmus.py`: Erasmus CLI entry point
- `cli/commands.py`: CLI interface for Erasmus

### Core Components

- `core/context.py`: Context management system
- `core/watcher.py`: File watching system
- `core/task.py`: Task management system

### CLI Components

- `cli/protocol.py`: Protocol management commands
- `cli/setup.py`: Project setup commands

### Git Components

- `git/manager.py`: Git repository management

### Protocol Components

- `utils/protocols/manager.py`: Protocol manager
- `utils/protocols/base.py`: Base protocol classes
- `utils/path_manager.py`: Path management for protocols

### Utility Components

- `utils/paths.py`: Path management
- `utils/logging.py`: Logging utilities
- `utils/env.py`: Environment utilities
- `utils/env_manager.py`: Environment management
- `utils/file.py`: File utilities
- `utils/file_ops.py`: File operations

### IDE Integration

- `ide/cursor_integration.py`: Cursor IDE integration
- `ide/sync_integration.py`: Sync IDE integration

### Sync Components

- `sync/file_sync.py`: File synchronization

## Key Dependencies

1. **Context Management**

   - Depends on path utilities and logging
   - Used by CLI commands and protocol management

2. **File Watching**

   - Depends on path utilities and logging
   - Used by CLI watch command

3. **Task Management**

   - Depends on path utilities and logging
   - Used by CLI task commands

4. **Git Management**

   - Depends on path utilities and logging
   - Used by CLI git commands

5. **Protocol Management**

   - Depends on path utilities, logging, and base protocol classes
   - Used by CLI protocol commands

6. **CLI Interface**
   - Depends on all other components
   - Provides the user interface for all functionality
