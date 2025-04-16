"""Tests for the collector module."""
import os
import pytest
from packager.collector import (
    DEFAULT_EXCLUDE_PATTERNS,
    collect_files_with_extensions,
    collect_files_with_filter,
    collect_py_files,
    get_relative_paths
)


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure for testing."""
    # Create main project directory
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create some Python files
    (project_dir / "main.py").write_text("print('main')")
    (project_dir / "utils.py").write_text("print('utils')")

    # Create a subdirectory with more files
    src_dir = project_dir / "src"
    src_dir.mkdir()
    (src_dir / "core.py").write_text("print('core')")
    (src_dir / "helpers.py").write_text("print('helpers')")

    # Create some non-Python files
    (project_dir / "README.md").write_text("# Test Project")
    (project_dir / "config.json").write_text("{}")

    # Create some files that should be excluded
    venv_dir = project_dir / ".venv"
    venv_dir.mkdir()
    (venv_dir / "lib.py").write_text("print('venv')")

    git_dir = project_dir / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("git config")

    # Create __pycache__ directory
    cache_dir = project_dir / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "main.cpython-39.pyc").write_text("cache")

    yield project_dir


def test_collect_py_files_basic(temp_project):
    """Test basic Python file collection."""
    files = collect_py_files(str(temp_project))

    # Should find 4 .py files (main.py, utils.py, src/core.py, src/helpers.py
    assert len(files) == 4

    # Check specific files
    filenames = {os.path.basename(f) for f in files}
    assert filenames == {"main.py", "utils.py", "core.py", "helpers.py"}


def test_collect_py_files_with_custom_exclude(temp_project):
    """Test Python file collection with custom exclude patterns."""
    # Use both default patterns and custom patterns
    exclude_patterns = DEFAULT_EXCLUDE_PATTERNS + ["src/**/*"]
    files = collect_py_files(str(temp_project), exclude_patterns=exclude_patterns)

    # Should only find 2 .py files (main.py, utils.py
    assert len(files) == 2

    # Check specific files
    filenames = {os.path.basename(f) for f in files}
    assert filenames == {"main.py", "utils.py"}

    # Verify excluded files are not included
    for file in files:
        assert "src/" not in file
        assert ".venv/" not in file
        assert ".git/" not in file
        assert "__pycache__/" not in file


def test_collect_files_with_extensions(temp_project):
    """Test collection of files with specific extensions."""
    extensions = [".md", ".json"]
    files = collect_files_with_extensions(str(temp_project), extensions=extensions)

    # Should find 2 files (README.md, config.json
    assert len(files) == 2

    # Check specific files
    filenames = {os.path.basename(f) for f in files}
    assert filenames == {"README.md", "config.json"}


def test_collect_files_with_filter(temp_project):
    """Test collection of files using a custom filter function."""

    # Filter function that only accepts files larger than 10 bytes
    def size_filter(file_path: str) -> bool:
        return os.path.getsize(file_path) > 10

    files = collect_files_with_filter(str(temp_project), filter_func=size_filter)

    # All our test files should be included as they're all > 10 bytes
    assert len(files) > 0
    for file in files:
        assert os.path.getsize(file) > 10


def test_default_exclude_patterns(temp_project):
    """Test that default exclude patterns work correctly."""
    files = collect_py_files(str(temp_project))

    # Check that excluded directories are not included
    for file in files:
        assert ".venv" not in file
        assert ".git" not in file
        assert "__pycache__" not in file


def test_get_relative_paths(temp_project):
    """Test conversion of absolute paths to relative paths."""
    abs_files = collect_py_files(str(temp_project))
    rel_files = get_relative_paths(abs_files, str(temp_project))

    # Check that all paths are relative
    for file in rel_files:
        assert not os.path.isabs(file)
        assert not file.startswith(str(temp_project))


def test_nonexistent_directory():
    """Test handling of nonexistent directories."""
    with pytest.raises(FileNotFoundError):
        collect_py_files("/nonexistent/directory")


def test_file_as_base_path(temp_project):
    """Test handling when base_path is a file instead of directory."""
    file_path = temp_project / "main.py"
    with pytest.raises(NotADirectoryError):
        collect_py_files(str(file_path))


def test_empty_directory(tmp_path):
    """Test handling of empty directories."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    files = collect_py_files(str(empty_dir))
    assert len(files) == 0


def test_symlink_handling(temp_project):
    """Test handling of symbolic links."""
    # Create a symlink to src directory
    symlink_dir = temp_project / "symlink"
    src_dir = temp_project / "src"

    try:
        os.symlink(src_dir, symlink_dir)
    except OSError:
        pytest.skip("Symlink creation not supported on this platform")

    files = collect_py_files(str(symlink_dir))

    # Should find 2 .py files (core.py, helpers.py
    assert len(files) == 2
    filenames = {os.path.basename(f) for f in files}
    assert filenames == {"core.py", "helpers.py"}
