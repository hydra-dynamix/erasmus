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
def setup_files(temp_dir: Path) -> dict[str, Path]:
    """
    Create a dictionary of test setup files.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Dict[str, Path]: Dictionary mapping file keys to their paths
    """
    files = {
        "architecture": temp_dir / ".erasmus/.architecture.md",
        "progress": temp_dir / ".progress.md",
        "tasks": temp_dir / ".tasks.md",
    }

    # Create empty files
    for path in files.values():
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
