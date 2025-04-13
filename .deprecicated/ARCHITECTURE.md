# Context Watcher: Automated Development Environment Setup and Management

## Overview
A single-file context watcher for cursor and windsurf, designed to streamline project initialization, development tracking, and version management.

## Key Components
- `watcher.py`: Main application orchestrating project setup and management
- `src/git_manager.py`: Atomic commit git management system
- `.cursorrules` and `.windsurfrules`: Context injection files for respective IDEs

## Technology Stack

### Prerequisites
- **Windows**
  - winget (Microsoft App Installer)
  - Python 3.8+
- **macOS**
  - Homebrew
  - Python 3.8+
- **Linux**
  - curl
  - Python 3.8+

### Package Management
- **Python: `uv` package manager**
  - Windows: Installed via winget
  - macOS: Installed via Homebrew
  - Linux: Installed via curl script
  - Dependency management directly in `watcher.py`
  - Single-script dependency tracking

- **Development Tools**
  - Logging: Rich logging with clear terminal output
  - File Watching: `watchdog` for monitoring context files
  - AI Integration: Local OpenAI client for commit message generation

## Workflow Stages

### 1. Project Initialization
- Create essential project files and directories:
  - `.erasmus/architecture.md`: Project architecture documentation
  - `progress.md`: Development progress tracking
  - `tasks.md`: Granular task management
  - `.IDErules`: Bundled context for IDE integration
  - `global_rules.md`: Global development guidelines
  - `context_watcher.log`: Comprehensive project logs

### 2. Environment Setup
- Virtual Environment Configuration
  - Python:
    - `uv` as package manager
    - `pytest` for comprehensive testing
  - Node:
    - `pnpm` as package manager
    - `jest` for testing
    - `puppeteer` for E2E testing
  - Rust:
    - `cargo` as package manager
    - Native Rust testing framework
    - `mockito` for mocking

- Environment Variable Management
  - Generate `.env.example`
  - Create `.env` with placeholder values

### 3. Development Workflow
- Automated Development Cycle:
  1. Generate tests for current task
  2. Implement task code
  3. Run and validate tests
  4. Iterative error correction
  5. Update task and progress status
  6. Proceed to next component

### 4. Packaging and Distribution
- Single File Installer Requirements
  - All dependencies recorded via `uv`
  - Initialization via `uv run watcher.py --setup IDE_ENVIRONMENT`
  - Cross-platform installation scripts
    - `.sh` for Unix-like systems
    - `.bat` for Windows

### 5. Version Control and Validation
- Repository: https://github.com/bakobiibizo/erasmus
- Versioning system with cryptographic hash validation
- Separate build and release directories

## IDE Compatibility
- cursor: `.cursorrules` context injection
- windsurf: `.windsurfrules` context injection
- Global rules configurable in respective IDE settings

## Project Goal
Consolidate git management into a single, portable `watcher.py` that simplifies project setup and management across different development environments.

## Future Considerations
- Expand IDE compatibility
- Enhance AI-driven development workflows
- Improve cross-platform support