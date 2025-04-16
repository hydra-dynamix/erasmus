"""Tests for the uv_wrapper module."""

import os
import platform
import pytest
from pathlib import Path
from packager.uv_wrapper import (
    generate_unix_bootstrap,
    generate_windows_bootstrap,
    generate_script,
    save_script,
)


def test_generate_unix_bootstrap():
    """Test generating Unix bootstrap code."""
    imports = {"typer", "requests"}
    bootstrap = generate_unix_bootstrap(imports)

    # Check for key components
    assert "#!/bin/bash" in bootstrap
    assert "uv add requests typer" in bootstrap
    assert 'uv run "$0" "$@"' in bootstrap
    assert "curl -LsSf https://astral.sh/uv/install.sh" in bootstrap


def test_generate_windows_bootstrap():
    """Test generating Windows bootstrap code."""
    imports = {"typer", "requests"}
    bootstrap = generate_windows_bootstrap(imports)

    # Check for key components
    assert "@echo off" in bootstrap
    assert "uv add requests typer" in bootstrap
    assert 'uv run "%~f0" %*' in bootstrap
    assert "winget install --id=astral-sh.uv" in bootstrap


def test_generate_script_unix(monkeypatch):
    """Test generating script on Unix systems."""
    # Mock platform.system to return 'Linux'
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    imports = {"typer", "requests"}
    code = 'print("Hello, world!")'
    script = generate_script(imports, code)

    # Check for key components
    assert "#!/bin/bash" in script
    assert "uv add requests typer" in script
    assert 'print("Hello, world!")' in script


def test_generate_script_windows(monkeypatch):
    """Test generating script on Windows systems."""
    # Mock platform.system to return 'Windows'
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    imports = {"typer", "requests"}
    code = 'print("Hello, world!")'
    script = generate_script(imports, code)

    # Check for key components
    assert "@echo off" in script
    assert "uv add requests typer" in script
    assert 'print("Hello, world!")' in script


def test_generate_script_unsupported(monkeypatch):
    """Test generating script on unsupported systems."""
    # Mock platform.system to return an unsupported system
    monkeypatch.setattr(platform, "system", lambda: "Unsupported")

    imports = {"typer"}
    code = 'print("Hello")'

    with pytest.raises(RuntimeError, match="Unsupported operating system"):
        generate_script(imports, code)


def test_save_script(tmp_path):
    """Test saving script to file."""
    script = 'print("Hello, world!")'
    output_path = tmp_path / "test_script.py"

    save_script(script, str(output_path))

    # Check file exists and has correct content
    assert output_path.exists()
    assert output_path.read_text() == script

    # Check file permissions on Unix systems
    if platform.system().lower() in ("linux", "darwin"):
        assert os.access(output_path, os.X_OK)


def test_package_ordering():
    """Test that packages are consistently ordered in bootstrap code."""
    # Test with unordered imports
    imports = {"requests", "typer", "click", "rich"}
    expected_packages = "click requests rich typer"

    # Check Unix bootstrap
    unix_bootstrap = generate_unix_bootstrap(imports)
    assert f"uv add {expected_packages}" in unix_bootstrap

    # Check Windows bootstrap
    windows_bootstrap = generate_windows_bootstrap(imports)
    assert f"uv add {expected_packages}" in windows_bootstrap
