"""Cross-platform bootstrapping for uv dependency management.

This module provides functionality to generate platform-aware scripts that:
1. Install uv if not present
2. Install required dependencies
3. Run the packaged Python code
"""

import os
import platform
from typing import Set, Optional


def generate_unix_bootstrap(imports: Set[str]) -> str:
    """Generate Unix (bash) bootstrap code.

    Args:
        imports: Set of required package names

    Returns:
        Bash script for Unix systems
    """
    # Convert imports to space-separated string with consistent ordering
    packages = " ".join(sorted(imports, key=str.lower))

    return f"""#!/bin/bash
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

  uv add {packages}
  uv run "$0" "$@"
  exit $?
fi

exit 1  # Unsupported OS
"""


def generate_windows_bootstrap(imports: Set[str]) -> str:
    """Generate Windows (batch) bootstrap code.

    Args:
        imports: Set of required package names

    Returns:
        Batch script for Windows systems
    """
    # Convert imports to space-separated string with consistent ordering
    packages = " ".join(sorted(imports, key=str.lower))

    return f"""@echo off
REM Windows uv bootstrap
where uv >nul 2>nul
if %errorlevel% neq 0 (
  echo Installing uv using winget...
  winget install --id=astral-sh.uv -e
)

uv add {packages}
uv run "%~f0" %*
exit /b
"""


def generate_script(imports: Set[str], code: str) -> str:
    """Generate a platform-aware script with uv bootstrapping.

    Args:
        imports: Set of required package names
        code: Python code to execute

    Returns:
        Complete script with bootstrap code and Python code
    """
    # Determine platform and generate appropriate bootstrap
    system = platform.system().lower()

    if system in ("linux", "darwin"):
        bootstrap = generate_unix_bootstrap(imports)
    elif system == "windows":
        bootstrap = generate_windows_bootstrap(imports)
    else:
        raise RuntimeError(f"Unsupported operating system: {system}")

    # Combine bootstrap and Python code
    script = f"{bootstrap}\n\n{code}"

    return script


def save_script(script: str, output_path: str) -> None:
    """Save the generated script to a file.

    Args:
        script: Complete script content
        output_path: Path to save the script
    """
    # Ensure the script is executable on Unix systems
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(script)

    # Make executable on Unix systems
    if platform.system().lower() in ("linux", "darwin"):
        os.chmod(output_path, 0o755)
