"""Tests for the uv_wrapper module."""

import os
import platform
import pytest
from pathlib import Path

from src.uv_wrapper import (
    generate_unix_script,
    generate_windows_script,
    generate_script,
)


@pytest.fixture
def sample_imports():
    """Sample imports for testing."""
    return {"numpy", "pandas", "requests"}


@pytest.fixture
def sample_code():
    """Sample Python code for testing."""
    return """def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
"""


def test_generate_unix_script(sample_imports, sample_code):
    """Test Unix script generation."""
    script = generate_unix_script(sample_imports, sample_code)

    # Check script header
    assert script.startswith("#!/bin/bash")
    assert "# Cross-platform uv bootstrap" in script

    # Check uv installation
    assert "if ! command -v uv >/dev/null" in script
    assert "curl -LsSf https://astral.sh/uv/install.sh" in script

    # Check package installation
    assert "uv add numpy pandas requests" in script

    # Check Python code
    assert sample_code in script


def test_generate_windows_script(sample_imports, sample_code):
    """Test Windows script generation."""
    script = generate_windows_script(sample_imports, sample_code)

    # Check script header
    assert script.startswith("@echo off")
    assert "REM Cross-platform uv bootstrap" in script

    # Check uv installation
    assert "where uv >nul 2>nul" in script
    assert "winget install --id=astral-sh.uv -e" in script

    # Check package installation
    assert "uv add numpy pandas requests" in script

    # Check Python code
    assert sample_code in script


def test_generate_script_with_entry_point(sample_imports, sample_code):
    """Test script generation with entry point."""
    entry_point = "main"
    script = generate_script(sample_imports, sample_code, entry_point)

    # Check entry point
    assert 'if __name__ == "__main__":' in script
    assert "    main()" in script


def test_generate_script_os_detection(sample_imports, sample_code):
    """Test OS detection in script generation."""
    script = generate_script(sample_imports, sample_code)

    if platform.system().lower() in ("linux", "darwin"):
        assert script.startswith("#!/bin/bash")
    elif platform.system().lower() == "windows":
        assert script.startswith("@echo off")
    else:
        pytest.skip("Unsupported operating system")


def test_generate_script_invalid_os(monkeypatch, sample_imports, sample_code):
    """Test script generation with invalid OS."""
    monkeypatch.setattr(platform, "system", lambda: "InvalidOS")

    with pytest.raises(OSError, match="Unsupported operating system"):
        generate_script(sample_imports, sample_code)


def test_script_execution_order(sample_imports, sample_code):
    """Test that script components are in the correct order."""
    script = generate_script(sample_imports, sample_code)
    lines = script.split("\n")

    # Find key components
    uv_check_idx = next(
        i for i, line in enumerate(lines) if "command -v uv" in line or "where uv" in line
    )
    uv_install_idx = next(i for i, line in enumerate(lines) if "curl" in line or "winget" in line)
    package_install_idx = next(i for i, line in enumerate(lines) if "uv add" in line)
    python_code_idx = next(i for i, line in enumerate(lines) if "#!/usr/bin/env python" in line)

    # Verify order
    assert uv_check_idx < uv_install_idx
    assert uv_install_idx < package_install_idx
    assert package_install_idx < python_code_idx
