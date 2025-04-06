# Erasmus: Context Watcher Testing Framework

## Project Overview
Erasmus is a comprehensive testing framework for the Context Watcher project, designed to ensure robust and reliable functionality.

## Prerequisites
- Python 3.13+
- uv package manager

## Setup and Installation
1. Clone the repository
2. Create a virtual environment
3. Install dependencies

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # Unix
.venv\Scripts\activate     # Windows

# Install dependencies
uv pip install -e .[test]
```

## Running Tests
To run the full test suite with coverage:

```bash
pytest
```

### Test Coverage
- Generates a coverage report
- Highlights untested code paths
- Helps improve code quality

## Test Modules
- `test_git_manager.py`: Tests for Git management functionality
- `test_watcher.py`: Tests for core watcher functionality

## Continuous Integration
- Automated tests run on every commit
- Comprehensive test coverage required for merging

## Troubleshooting
- Ensure all dependencies are installed
- Check Python version compatibility
- Verify virtual environment activation