# Erasmus: Intelligent Context Management System

## Overview

Erasmus is an advanced context management library that revolutionizes software development workflows by providing:

- 🤖 **Intelligent Context Tracking**: Dynamically manage project context across different development stages
- 🔍 **Protocol-Driven Development**: Define and execute structured development protocols
- 🛠 **Multi-IDE Support**: Compatible with Windsurf, Cursor, Codex, and Claude IDEs
- 📋 **Automated Documentation**: Generate and maintain comprehensive project documentation

### Key Features

- **Path Management**: Centralized, cross-platform path handling
- **Environment Configuration**: Type-safe, dynamic environment variable management
- **File Monitoring**: Real-time tracking of project context files
- **Protocol Handling**: Define, store, and execute development protocols
- **Packager**: Universal installer for system and dependencies

## Architecture and Workflow

### Core Components

1. **Path Management** (`erasmus/utils/paths.py`)

   - Detect and manage paths across different IDEs
   - Support for Windsurf, Cursor, Codex, and Claude
   - Automatic directory and symlink creation

2. **Environment Management** (`erasmus/environment.py`)

   - Dynamic, type-safe environment variable handling
   - Support for `.env` file loading
   - Strong type and constraint validation

3. **Context Management** (`erasmus/context.py`)

   - Save and load context files
   - Sanitize document names
   - Ensure cross-platform compatibility

4. **Protocol Handler** (`erasmus/protocol.py`)

   - Manage protocol definitions
   - Preserve context across different development stages

5. **File Monitor Service** (`erasmus/file_monitor.py`)
   - Watch changes in context files
   - Update IDE rule files dynamically

## Installation

### Quick Install

```bash
curl -L https://raw.githubusercontent.com/bakobiibizo/erasmus/main/releases/erasmus/erasmus/erasmus_v0.2.2
```

### Workflow Overview

1. **Context Definition**

   - Define project architecture in `.ctx.architecture.xml`
   - Track progress in `.ctx.progress.xml`
   - Break down tasks in `.ctx.tasks.xml`

2. **Continuous Synchronization**

   - Real-time monitoring of context files
   - Automatic rule file updates
   - Dynamic context injection for AI assistants

3. **Protocol Execution**
   - Load predefined development protocols
   - Execute context-aware development workflows

### Context File Structure

- **`.ctx.architecture.xml`**: Project blueprint

  - High-level design
  - Technology stack
  - User stories
  - Completion criteria

- **`.ctx.progress.xml`**: Development tracking

  - Component progress
  - Blockers
  - Dependencies

- **`.ctx.tasks.xml`**: Granular task management
  - Detailed task breakdown
  - Status tracking
  - Assignment

\*Note: Cursor users will have to copy their `global_rules.md` that is generated when the setup command is run to their global rules in the settings. I still haven't figured out where that file actually is to automate it. If you know let me know!

## Release Packaging Path Changes

**Packager output path logic:**

- When packaging with a version bump (e.g., via `version-control bump`), the output is written to:
  - `releases/**<library_name>**/**<version>**/**<library_name>**_v**<version>**.py`
- For dry runs (not bumping), the output is written to:
  - `releases/**<library_name>**/0.0.0/**<library_name>**_v0.0.0.py`

The resolved output path is always passed to the installer build script (`build_installer.sh`).

## What Does Erasmus Do?

Erasmus sits in the background of your development environment and:

1. **Tracks Project Context** - Maintains a complete view of your codebase structure, decisions, and progress
2. **Powers IDE Context Injection** - Feeds rich context to AI code assistants in compatible IDEs
3. **Monitors Development Files** - Watches for changes in key files like architecture docs and progress tracking
4. **Creates Essential Documentation** - Automatically generates and updates project documentation

### Core Files Managed by Erasmus

- **.erasmus/.architecture.md** - Project architecture documentation
- **.progress.md** - Development progress tracking
- **.tasks.md** - Granular task management
- **.IDErules** - Bundled context for IDE integration

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

## Code Structure

### Core Components

1. **watcher.py** - Main application orchestrating project setup and management

   - `Watcher` class: Core functionality for file watching and context management
   - `Task` class: Task management and tracking
   - `TaskStatus` class: Task status enumeration

2. **src/script_converter.py** - Handles script conversion between platforms

   - `ScriptConverter` class: Converts shell scripts to batch scripts
   - Command mapping and function templates

3. **src/packager.py** - Python script packaging functionality

   - `ScriptPackager` class: Bundles multiple Python files into a single executable
   - AST-based code analysis and dependency tracking

4. **src/build_release.py** - Release package building
   - `build_single_file()`: Creates single-file executable
   - `embed_erasmus()`: Embeds executable into installer
   - `convert_to_batch()`: Converts shell scripts to batch files

### Key Classes and Methods

#### Watcher Class

```python
class Watcher:
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.tasks = []
        self.context = {}

    def watch_files(self):
        """Start watching project files for changes."""

    def update_context(self):
        """Update project context based on file changes."""

    def add_task(self, description: str) -> Task:
        """Add a new task to the project."""
```

#### Task Class

```python
class Task:
    def __init__(self, id: str, description: str):
        self.id = id
        self.description = description
        self.status = TaskStatus.PENDING
        self.notes = []

    def add_note_to_task(self, note: str):
        """Add a note to the task."""
```

#### ScriptPackager Class

```python
class ScriptPackager:
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.import_set = set()
        self.script_bodies = []

    def package_scripts(self, output_path: Path | None = None) -> str:
        """Package all scripts into a single file."""
```

## Compatible IDE Environments

- **cursor** - Full support with `.cursorrules` integration
- **windsurf** - Full support with `.windsurfrules` integration

## Advanced Features

- **Atomic Git Management** - Provides structured commit messages with contextual awareness
- **Cross-Platform Support** - Works on Windows, macOS, and Linux
- **Local LLM Integration** - Can be configured to use local AI models instead of OpenAI

## Configuration

Erasmus can be configured through:

1. `.env` file (created during installation)
2. Command-line parameters
3. Interactive prompts

Key configuration variables:

```
IDE_ENV=cursor        # Your IDE environment
OPENAI_API_KEY=       # Your OpenAI API key
OPENAI_MODEL=gpt-4    # Model to use for git commit messages
```

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/bakobiibizo/erasmus.git
cd erasmus

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # Unix
.venv\Scripts\activate     # Windows

# Install dependencies
uv pip install -e .[test]
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_packager.py

# Run tests with coverage
uv run pytest --cov=src
```

### Python Script Packager

The Python Script Packager is a powerful tool that bundles Python projects into standalone executable scripts. It automatically handles dependency management using `uv`, making scripts fully portable across different environments.

#### Features

- Packages multiple Python files into a single executable script
- Automatically detects and manages dependencies using `uv`
- Cross-platform support (Linux, macOS, Windows)
- Preserves code structure and comments (optional)
- Groups imports by type (standard library, third-party, local)
- Zero setup required beyond Python installation

#### Usage

```bash
# Package a single Python file
packager package script.py -o output.py

# Package an entire project directory
packager package src/ -o bundled.py

# Package without grouping imports
packager package script.py --no-group-imports

# Package without preserving comments
packager package script.py --no-comments

# Show version information
packager version
```

#### Components

The packager consists of several key modules:

- **collector.py**: Recursively finds Python files in a project
- **parser.py**: Extracts and analyzes imports using AST
- **builder.py**: Merges code bodies and formats imports
- **mapping.py**: Maps imports to PyPI package names
- **uv_wrapper.py**: Handles cross-platform `uv` bootstrapping

#### Contributing to the Packager

1. **Setup Development Environment**

   ```bash
   # Clone the repository
   git clone https://github.com/bakobiibizo/erasmus.git
   cd erasmus

   # Install development dependencies
   uv pip install -e .[dev,test]
   ```

2. **Run Packager Tests**

   ```bash
   # Run packager-specific tests
   pytest tests/packager/

   # Run with coverage
   pytest tests/packager/ --cov=src/packager
   ```

3. **Development Guidelines**
   - Write tests for new features
   - Follow the existing code style
   - Update documentation for API changes
   - Add type hints to new functions
   - Ensure cross-platform compatibility

### Building a Release

```bash
# Build the complete release package
python main.py build

# Test the installer in Docker
python main.py test
```

## Troubleshooting

- **Permission Issues**: Run `sudo chmod +x erasmus.sh` if you encounter permission denied errors
- **OpenAI Integration**: Ensure you have valid API credentials in your `.env` file
- **Path Issues**: If `uv` is not found, try restarting your terminal or adding it to your PATH
- **Script Conversion**: If script conversion fails, check the release directory permissions
- **Package Building**: Ensure all required files exist in the correct locations before building

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to Erasmus.

> **Note:** After running `erasmus setup`, you can use the `erasmus` command directly in your shell. The setup process automatically adds an alias or function for `erasmus` to your shell configuration (e.g., `.bashrc`, `.zshrc`, or `config.fish`).

For example:

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
