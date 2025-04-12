#  Python Script Packager with Cross-Platform `uv` Bootstrap

##  Overview

This tool is a **Python script bundler** that packages a project into a **single, standalone executable script**. It recursively gathers `.py` files, merges them into one file, collects all `import` statements, and **bootstraps runtime dependencies using [uv](https://github.com/astral-sh/uv)**.

The final output is a **platform-aware, cross-compatible script** that:
- Works on **Linux, macOS, and Windows**
- **Installs `uv` automatically** if missing
- Infers and installs required packages using `uv add`
- Runs itself using `uv run`
- Requires **no virtual environments, no `requirements.txt`, and no pip**

---

##  Goals

-  Convert a Python project into a single executable script
-  Automatically infer external dependencies from imports
-  Use `uv` to install and run dependencies in a temporary env
-  Support both Unix (bash) and Windows (batch) execution
-  Guarantee zero setup beyond Python and basic tools (`curl`, `winget`)

---

##  Features

| Feature                            | Description |
|------------------------------------|-------------|
|  Static import parsing            | Detects and de-duplicates imports using `ast` |
|  Dependency inference             | Resolves which packages are required from imports |
|  Standard lib filtering           | Excludes stdlib modules from `uv add` |
|  No extra files                   | No `venv`, no `requirements.txt`, no pip needed |
|  Clean CLI                        | Use `python -m packager` to bundle |
|  Cross-platform bootstrapping     | Works with Bash (Linux/macOS) and Batch (Windows) |
|  Single script output             | One file with shell header, dependency install, and Python code |

---

##  Architecture

```
packager/
 __main__.py         # CLI interface
 collector.py        # Recursively finds Python files
 parser.py           # Parses imports using AST
 builder.py          # Merges stripped code bodies and imports
 uv_wrapper.py       # Adds OS-aware shell and batch bootstrap
 mapping.py          # Optional import-to-PyPI mapping
 stdlib.py           # Contains stdlib detection for filtering
```

---

##  Detailed Component Design

### `collector.py`
```python
def collect_py_files(base_path: str) -> List[str]:
    # Recursively yield all .py files
```

---

### `parser.py`
```python
def extract_imports(source: str) -> Set[str]:
    # Uses ast to extract 'import x' and 'from x import y'

def strip_imports(source: str) -> str:
    # Removes import lines, returns only the executable code
```

---

### `mapping.py` (Optional)
```python
# Maps import names to PyPI packages
PYPI_MAP = {
    "cv2": "opencv-python",
    "PIL": "pillow",
}
```

---

### `stdlib.py`
```python
# Uses sys.stdlib_module_names or external stdlib-list
def is_stdlib_module(name: str) -> bool:
    return name in stdlib_modules
```

---

### `builder.py`
```python
def build_script(files: List[str]) -> Tuple[Set[str], str]:
    # Combines:
    # 1. Unique import names (stripped of stdlib)
    # 2. Combined code body with imports removed
```

---

### `uv_wrapper.py`
```python
def generate_script(imports: Set[str], code: str) -> str:
    # Returns final script string with:
    # - Shebang
    # - OS check (bash or batch)
    # - uv install logic (curl or winget)
    # - uv add <packages>
    # - uv run path-to-script
    # - Embedded Python code
```

---

### `__main__.py`
```python
# CLI wrapper
# Usage: python -m packager --input src/ --output packed.sh
```

---

##  Output Script Structure

```bash
#!/bin/bash
# Cross-platform uv bootstrap
OS=$(uname -s)

if [[ "$OS" == "Linux" || "$OS" == "Darwin" ]]; then
  if ! command -v uv >/dev/null; then
    echo "Installing uv..."
    if ! command -v curl >/dev/null; then
      echo "Missing 'curl'. Please install it."
      exit 1
    fi
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
  fi

  uv add rich typer requests
  uv run "$0" "$@"
  exit $?
fi

REM Windows fallback
@echo off
where uv >nul 2>nul
if %errorlevel% neq 0 (
  echo Installing uv using winget...
  winget install --id=astral-sh.uv -e
)

uv add rich typer requests
uv run "%~f0" %*
exit /b
```

_Followed by Python code:_

```python
#!/usr/bin/env python
import typer
import requests

def main():
    print("Hello from bundled script!")

if __name__ == "__main__":
    main()
```

---

##  Testing Strategy
test
Test Cases:

| Scenario                    | Linux | macOS | Windows |
|----------------------------|-------|-------|---------|
| No `uv` installed          |     |     |       |
| No `curl`                  |     |     | N/A     |
| No `winget`                | N/A   | N/A   |       |
| Missing dependency         |     |     |       |
| Nested import structure    |     |     |       |
| Works with entrypoint code |     |     |       |

---

##  Requirements

| Tool     | Use                |
|----------|--------------------|
| `ast`    | Static parsing     |
| `uv`     | Runtime environment |
| `curl`   | Unix installer     |
| `winget` | Windows installer  |
| Python 3.8+ | Runtime & toolchain |

---

##  Future Improvements

- Package metadata injection (name/version/help)
- GUI/UX wrapper for non-devs
- Compression/minification support
- Add support for `.env` or config files
- Optional `pyproject.toml` parser for metadata

---

##  Summary

This Python packager is a **fully cross-platform script bundler** that requires:
- No setup
- No environments
- No external files

It outputs a **single script** that:
- Bootstraps its dependencies using `uv`
- Installs `uv` if necessary
- Runs itself cleanly on any modern system
