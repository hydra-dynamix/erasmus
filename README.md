# Erasmus: Context Watcher for Development Environment Setup

## Project Overview
Erasmus is a single-file context watcher designed to streamline project initialization, development tracking, and version management across different IDE environments.

## Quick Installation

### Option 1: Direct Download and Run
1. Download the appropriate installer from the `release/` directory:
   - For Windows: Download the `.bat` file
   - For macOS/Linux: Download the `.sh` file

2. Run the installer:
   - Windows: Double-click the `.bat` file or run it from Command Prompt
   - macOS/Linux: Make the script executable and run it
     ```bash
     chmod +x erasmus_v*.sh
     ./erasmus_v*.sh
     ```

3. When prompted for configuration variables:
   - Enter your preferred values, or
   - Press Enter to accept the defaults (configured for OpenAI)

### Option 2: One-Line Installation (Linux/macOS)
```bash
curl -fsSL https://raw.githubusercontent.com/Bakobiibizo/erasmus/main/release/v0.0.1/erasmus_v0.0.1.sh | bash
```

## Features
- Automated project initialization with essential documentation
- IDE context injection for Cursor and Windsurf
- Git management with atomic commits
- Environment setup for Python, Node, and Rust projects
- Cross-platform compatibility

## Development Setup
For contributors who want to work on Erasmus itself:

### Prerequisites
- Python 3.8+
- uv package manager

### Setup for Development
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
pytest
```

## Troubleshooting
- Ensure you have the correct permissions to execute the installer
- Check that Python 3.8+ is installed on your system
- For OpenAI integration, ensure you have valid API credentials
- If using a local LLM, verify the base URL is correctly formatted