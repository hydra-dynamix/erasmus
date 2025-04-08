# Erasmus: AI Context Watcher for Development

## Overview
Erasmus is a powerful context watcher that enhances your development environment by tracking project state and providing intelligent assistance through AI integration. It's designed to work with Cursor and Windsurf IDEs to provide contextual guidance during development.

## How It Works

Erasmus leverages modern IDE capabilities by utilizing their rule injection mechanisms to deliver dynamic context to AI code assistants. The system maintains three core markdown documents that drive AI-assisted development:

![process flowchart](public/flowchart.png)

### Intelligent Document Management

**ARCHITECTURE.md** serves as the project blueprint, defining goals and requirements that must be met for project completion.

**PROGRESS.md** tracks components derived from the architecture document, organizing them into a development schedule.

**TASKS.md** breaks down components into manageable sub-tasks, tracking their completion status throughout development.

### Continuous Context Synchronization

As development progresses:
1. Erasmus monitors these files in real-time
2. When file changes are detected, it updates the IDE rule files
3. The AI assistant receives the updated context immediately
4. This allows the AI to maintain awareness of current project state

This continuous context loop ensures your AI assistant always has the most current understanding of your project status, decisions, and remaining work, enabling truly intelligent assistance throughout the development lifecycle.

## Quick Installation

```bash
curl -L https://raw.githubusercontent.com/bakobiibizo/erasmus/main/release/v0.0.1/erasmus_v0.0.1.sh -o erasmus.sh && chmod +x erasmus.sh && ./erasmus.sh
```

That's it! The installer will set up everything you need.

## What Does Erasmus Do?

Erasmus sits in the background of your development environment and:

1. **Tracks Project Context** - Maintains a complete view of your codebase structure, decisions, and progress
2. **Powers IDE Context Injection** - Feeds rich context to AI code assistants in compatible IDEs
3. **Monitors Development Files** - Watches for changes in key files like architecture docs and progress tracking
4. **Creates Essential Documentation** - Automatically generates and updates project documentation

### Core Files Managed by Erasmus

- **ARCHITECTURE.md** - Project architecture documentation
- **PROGRESS.md** - Development progress tracking
- **TASKS.md** - Granular task management
- **.IDErules** - Bundled context for IDE integration

## Usage

After installation, you can:

```bash
# Start the context watcher
uv run erasmus.py --watch

# Set up a new project environment
uv run erasmus.py --setup [cursor|windsurf]

# View project status
uv run erasmus.py --status
```

## Compatible IDE Environments

- **Cursor** - Full support with `.cursorrules` integration
- **Windsurf** - Full support with `.windsurfrules` integration

## How It Works

1. Erasmus runs as a background process, monitoring your project files
2. When changes occur in tracked files, it updates the context
3. The context is injected into your IDE's AI assistant
4. Your AI assistant gains deep understanding of your project's state and goals

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
OPENAI_MODEL=gpt-4o   # Model to use for git commit messages
```

## For Contributors

If you'd like to contribute to Erasmus development, please see the [CONTRIBUTING.md](CONTRIBUTING.md) file or check the development setup instructions below.

### Development Setup
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