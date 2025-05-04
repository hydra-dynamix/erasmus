# Erasmus: Intelligent Context Management System

## Overview

Erasmus is an advanced context management library for software development. It provides intelligent context tracking, protocol-driven workflows, multi-IDE support, and automated documentation. It is designed to power AI coding assistants and streamline project management.

## Key Features

- **Path Management**: Centralized, cross-platform path handling for Windsurf, Cursor, Codex, Claude, and Warp
- **Environment Configuration**: Type-safe, dynamic environment variable management
- **Context Management**: Save/load `.ctx.architecture.md`, `.ctx.progress.md`, `.ctx.tasks.md`
- **Protocol Handling**: Define, store, and execute development protocols (developer, documentation, dependency, etc.)
- **File Monitoring**: Real-time tracking of context files and automatic rules file updates
- **MCP Integration**: CLI and protocol support for GitHub/MCP workflows

## Architecture and Workflow

### Core Components

- Path Management (`erasmus/utils/paths.py`)
- Environment Management (`erasmus/environment.py`)
- Context Management (`erasmus/context.py`)
- Protocol Handler (`erasmus/protocol.py`)
- File Monitor Service (`erasmus/file_monitor.py`)
- CLI (`erasmus/cli/main.py` and subcommands)
- MCP Integration (CLI and protocol support)
- Templates and Protocols (`.erasmus/templates/`)

### Directory Structure

```
erasmus/
├── erasmus/
│   ├── cli/
│   ├── context.py
│   ├── environment.py
│   ├── file_monitor.py
│   ├── protocol.py
│   ├── utils/
│   └── ...
├── .erasmus/
│   ├── templates/
│   ├── protocols/
│   └── ...
├── .ctx.architecture.md
├── .ctx.progress.md
├── .ctx.tasks.md
├── README.md
└── ...
```

### Workflow

1. Define project architecture in `.ctx.architecture.md`
2. Track progress in `.ctx.progress.md`
3. Break down tasks in `.ctx.tasks.md`
4. Use `erasmus watch` to monitor and sync context
5. Use protocols to drive development, documentation, and releases

### Context File Structure

- **`.ctx.architecture.md`**: Project blueprint (high-level design, stack, user stories, criteria)
- **`.ctx.progress.md`**: Development tracking (component progress, blockers, dependencies)
- **`.ctx.tasks.md`**: Granular task management (detailed breakdown, status, assignment)

## Installation

### Quick Install

```bash
curl -sSL https://raw.githubusercontent.com/bakobiibizo/erasmus/refs/heads/main/releases/erasmus/0.3.1/erasmus_v0.3.1.sh -o erasmus.sh && bash erasmus.sh
```

## Command Line Usage

Erasmus provides a powerful CLI for managing development contexts, protocols, and project setup. Here are a few key examples:

```bash
# List all contexts
erasmus context list

# Create a new protocol
erasmus protocol create my-protocol

# Setup a new project interactively
erasmus setup

# Watch for .ctx file changes
erasmus watch

# Show current status
erasmus status
```

For a full list of commands and detailed usage, see [docs/CLI_COMMANDS.md](docs/CLI_COMMANDS.md).

## What Does Erasmus Do?

Erasmus sits in the background of your development environment and:

1. **Tracks Project Context** - Maintains a complete view of your codebase structure, decisions, and progress
2. **Powers IDE Context Injection** - Feeds rich context to AI code assistants in compatible IDEs
3. **Monitors Development Files** - Watches for changes in key files like architecture docs and progress tracking
4. **Creates Essential Documentation** - Automatically generates and updates project documentation

## Protocols

- Developer: Implements code, tracks tasks, ensures code quality
- Documentation: Maintains docs, tracks doc tasks
- Dependency: Manages dependencies, tracks updates
- Testing, CI/CD, Security, Style, Product Owner, etc.

## Completion Criteria

- All core components implemented and tested
- Protocols in use for all major workflows
- Documentation and context files up-to-date
- Automated rules file updates working in all supported IDEs

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT
