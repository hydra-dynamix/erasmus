import os
from pathlib import Path

import pytest

from erasmus.utils.context import backup_rules_file, cleanup_project


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with test files."""
    # Create test files and directories
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "test.pyc").write_text("test")
    (tmp_path / ".cursorrules").write_text("test rules")
    (tmp_path / "global_rules.md").write_text("global rules")
    (tmp_path / "test.py").write_text("print('test')")

    # Change to temp directory for test
    original_dir = Path.cwd()
    os.chdir(tmp_path)

    yield tmp_path

    # Cleanup and restore original directory
    os.chdir(original_dir)


def test_backup_rules_file(temp_project_dir):
    """Test that backup_rules_file creates backups correctly."""
    rules_file = temp_project_dir / ".cursorrules"
    backup_rules_file(rules_file)

    backup_path = temp_project_dir / ".cursorrules.old"
    assert backup_path.exists()
    assert backup_path.read_text() == "test rules"


def test_cleanup_project(temp_project_dir):
    """Test that cleanup_project removes generated files and creates backups."""
    cleanup_project()

    # Check that backups were created
    assert (temp_project_dir / ".cursorrules.old").exists()
    assert (temp_project_dir / "global_rules.md.old").exists()

    # Check that original files were removed
    assert not (temp_project_dir / ".cursorrules").exists()
    assert not (temp_project_dir / "global_rules.md").exists()

    # Check that generated files were removed
    assert not (temp_project_dir / "__pycache__").exists()
    assert not (temp_project_dir / "__pycache__" / "test.pyc").exists()

    # Check that non-generated files were preserved
    assert (temp_project_dir / "test.py").exists()
