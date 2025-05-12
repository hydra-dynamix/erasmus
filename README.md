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
curl -sSL https://raw.githubusercontent.com/bakobiibizo/erasmus/refs/heads/main/releases/erasmus/0.4.0/erasmus_v0.4.0.sh -o erasmus.sh && bash erasmus.sh
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

## Making MCP Calls to Servers

Erasmus supports making JSON-RPC calls to MCP servers (such as the GitHub MCP server) via both the CLI and programmatically. Below are the key details and sharp edges to be aware of when constructing these calls:

### 1. JSON-RPC Request Structure

- **Every session must begin with an `initialize` request.**
- **Tool calls use the `tools/call` method.**
- The `params` object for `tools/call` must include:
  - `name`: The tool's name (e.g., `list_branches`, `get_user`). This is NOT the JSON-RPC method name, but the tool identifier.
  - `arguments`: A dictionary of arguments required by the tool. All tool-specific parameters must be nested inside this `arguments` object.

**Example JSON-RPC tool call:**

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "list_branches",
    "arguments": {
      "owner": "bakobi",
      "repo": "hexamerous"
    }
  },
  "id": 2
}
```

**Sharp Edges:**

- The `name` field is required and must match the tool's identifier exactly.
- All tool arguments must be inside the `arguments` dictionary. Passing them at the top level will result in errors.
- The `method` is always `tools/call` for tool invocations, not the tool name itself.
- You must send an `initialize` request first in the same session.
- The server will respond with one JSON object per line for each request (e.g., one for `initialize`, one for the tool call).

### 2. CLI Usage

You can invoke MCP tools via the Erasmus CLI:

```
erasmus mcp servers github list_branches --owner bakobi --repo hexamerous
```

The CLI handles the JSON-RPC structure for you, but you must provide all required arguments as CLI options. The CLI will pretty-print the server's response, including any nested JSON content.

### 3. Programmatic Usage (Python)

To make calls programmatically, use the `StdioClient` class:

```python
from erasmus.mcp.client import StdioClient

client = StdioClient()
stdout, stderr = client.communicate(
    server_name="github",
    method="tools/call",
    params={
        "name": "list_branches",
        "arguments": {
            "owner": "bakobi",
            "repo": "hexamerous"
        }
    }
)
print(stdout)
```

**Note:**

- Always send both `initialize` and `tools/call` requests in the same session (the client does this for you).
- Parse each line of the response as a separate JSON object.
- The tool response is usually the last JSON object returned.

### 4. Common Pitfalls

- **Missing `arguments` nesting:** All tool parameters must be inside the `arguments` dict.
- **Incorrect `name`:** The `name` must match the tool's identifier, not the method.
- **Forgetting `initialize`:** The server expects an `initialize` request before any tool calls.
- **Parsing responses:** The server returns one JSON object per line; parse each line separately.

Refer to the CLI help (`erasmus mcp servers github --help`) for available tools and their required arguments.
