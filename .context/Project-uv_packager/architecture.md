# Python Script Packager with Cross-Platform `uv` Bootstrap

## Overview

The Python Script Packager is a **bundling tool** that transforms Python projects into **standalone, cross-platform executable scripts**. It automatically manages dependencies using `uv`, providing a zero-setup experience for end users.

Key Features:
- Cross-platform compatibility (Linux, macOS, Windows)
- Automatic `uv` installation and bootstrapping
- Dynamic dependency inference and installation
- Single-file output with no external requirements

---

## Goals

- Create standalone executable scripts from Python projects
- Eliminate manual dependency management
- Ensure cross-platform compatibility
- Minimize end-user setup requirements
- Leverage `uv` for fast, reliable package management

---

## Features

| Feature | Description |
|---------|-------------|
| Static Import Analysis | AST-based import detection and deduplication |
| Dependency Resolution | Automatic package inference from imports |
| Standard Library Filtering | Exclude stdlib modules from dependencies |
| Cross-Platform Bootstrap | Unified shell/batch script generation |
| Zero Configuration | No venv, requirements.txt, or pip needed |
| Clean CLI | Simple python -m interface |

---

## Architecture

```
packager/
├── __main__.py     # CLI interface and entry point
├── collector.py    # Python file discovery
├── parser.py       # Import analysis and code stripping
├── builder.py      # Script assembly and generation
├── uv_wrapper.py   # Platform-specific bootstrapping
├── mapping.py      # Import to PyPI package mapping
└── stdlib.py       # Standard library detection
```

---

## Technical Components

### Collector Module
```python
class FileCollector:
    def collect_py_files(self, base_path: str) -> List[str]:
        """Recursively find Python files in project."""
        pass

    def filter_files(self, files: List[str], exclude: List[str]) -> List[str]:
        """Filter files based on patterns."""
        pass
```

### Parser Module
```python
class ImportParser:
    def extract_imports(self, source: str) -> Set[str]:
        """Extract imports using AST."""
        pass
    
    def strip_imports(self, source: str) -> str:
        """Remove imports while preserving line numbers."""
        pass
```

### Builder Module
```python
class ScriptBuilder:
    def build_script(self, files: List[str]) -> str:
        """Generate final executable script."""
        pass
    
    def generate_bootstrap(self, imports: Set[str]) -> str:
        """Create platform-specific bootstrap code."""
        pass
```

---

## Dependencies

| Component | External Dependencies |
|-----------|---------------------|
| Core | Python 3.8+ |
| Import Analysis | `ast` (stdlib) |
| Package Management | `uv` |
| Unix Bootstrap | `curl` |
| Windows Bootstrap | `winget` |

---

## User Stories

1. As a developer, I want to bundle my Python project into a single file so that users can run it without setup
2. As an end user, I want to run Python scripts without manually installing dependencies
3. As a maintainer, I want to distribute Python tools without worrying about environment setup
4. As a user, I want the script to work on any platform without modifications

---

## Constraints

1. Must work on Python 3.8+
2. Must support Linux, macOS, and Windows
3. Must handle network-restricted environments gracefully
4. Must preserve source code line numbers for debugging
5. Must be secure and not execute arbitrary code during install

---

## Development Timeline

AI-accelerated development schedule:

| Sprint | Duration | Focus |
|--------|-----------|-------|
| Sprint 0 | 2 hours | Project setup and infrastructure |
| Sprint 1 | 4 hours | Core components (stdlib.py, collector.py) |
| Sprint 2 | 4 hours | Code analysis (parser.py, mapping.py) |
| Sprint 3 | 4 hours | Script generation (builder.py, uv_wrapper.py) |
| Sprint 4 | 2 hours | Integration and documentation |

Total development time: 16 hours (2 working days)

---

## Future Improvements

- Package metadata injection
- Code compression/minification
- GUI wrapper for non-technical users
- Environment variable handling
- Project configuration parsing
