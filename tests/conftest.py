"""
Test Configuration and Fixtures
=============================

This module provides pytest fixtures and utilities for testing the Erasmus project.
"""

import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from erasmus.utils.paths import SetupPaths

# Add the src directory to the Python path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for test files.

    Yields:
        Path: Path to the temporary directory

    Note:
        The directory is automatically cleaned up after the test.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def setup_paths(temp_dir: Path) -> SetupPaths:
    """
    Create a SetupPaths instance for testing.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        SetupPaths: Configured SetupPaths instance
    """
    return SetupPaths.with_project_root(temp_dir)


@pytest.fixture
def setup_files(temp_dir: Path, setup_paths: SetupPaths) -> dict[str, Path]:
    """
    Create a dictionary of test setup files.

    Args:
        temp_dir: Temporary directory fixture
        setup_paths: SetupPaths fixture

    Returns:
        Dict[str, Path]: Dictionary mapping file keys to their paths
    """
    # Use SetupPaths for file paths
    files = {
        "architecture": setup_paths.markdown_files["architecture"],
        "progress": setup_paths.markdown_files["progress"],
        "tasks": setup_paths.markdown_files["tasks"],
    }

    # Create empty files
    for path in files.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    return files


@pytest.fixture
def test_script(temp_dir: Path) -> Path:
    """
    Create a test script file.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path: Path to the test script
    """
    script_path = temp_dir / "test_script.py"
    script_path.write_text("print('Hello, World!')")
    return script_path
