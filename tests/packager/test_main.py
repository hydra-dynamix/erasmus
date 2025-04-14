"""Tests for the CLI interface."""

import os
from pathlib import Path
from textwrap import dedent
from typing import List

import pytest
from typer.testing import CliRunner

from src.__main__ import app

runner = CliRunner()


@pytest.fixture
def sample_py_file(tmp_path):
    """Create a sample Python file for testing."""
    content = dedent("""
        import numpy as np
        import pandas as pd
        from matplotlib import pyplot as plt

        def main():
            data = np.random.randn(100)
            df = pd.DataFrame(data)
            plt.plot(df)
            plt.show()

        if __name__ == '__main__':
            main()
    """).strip()

    file_path = tmp_path / "script.py"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample Python project for testing."""
    # Create main script
    main_content = dedent("""
        from .utils import process_data
        import pandas as pd

        def main():
            data = pd.read_csv('data.csv')
            result = process_data(data)
            print(result)

        if __name__ == '__main__':
            main()
    """).strip()

    # Create utils module
    utils_content = dedent("""
        import numpy as np
        from scipy import stats

        def process_data(data):
            return np.mean(data) + stats.sem(data)
    """).strip()

    # Create project structure
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    main_file = project_dir / "main.py"
    main_file.write_text(main_content)

    utils_dir = project_dir / "utils"
    utils_dir.mkdir()

    utils_file = utils_dir / "__init__.py"
    utils_file.write_text(utils_content)

    return project_dir


def test_package_single_file(sample_py_file):
    """Test packaging a single Python file."""
    result = runner.invoke(app, ["package", str(sample_py_file)])
    assert result.exit_code == 0

    # Check that output contains expected content
    assert "numpy" in result.stdout
    assert "pandas" in result.stdout
    assert "matplotlib" in result.stdout
    assert "def main():" in result.stdout


def test_package_project(sample_project):
    """Test packaging a Python project."""
    result = runner.invoke(app, ["package", str(sample_project)])
    assert result.exit_code == 0

    # Check that output contains expected content
    assert "pandas" in result.stdout
    assert "numpy" in result.stdout
    assert "scipy" in result.stdout
    assert "def process_data" in result.stdout
    assert "def main():" in result.stdout


def test_package_with_output(sample_py_file, tmp_path):
    """Test packaging with output file."""
    output_file = tmp_path / "output.py"
    result = runner.invoke(app, ["package", str(sample_py_file), "-o", str(output_file)])
    assert result.exit_code == 0

    # Check that file was created
    assert output_file.exists()
    content = output_file.read_text()

    # Check file content
    assert "numpy" in content
    assert "pandas" in content
    assert "matplotlib" in content
    assert "def main():" in content


def test_package_no_group_imports(sample_py_file):
    """Test packaging without import grouping."""
    result = runner.invoke(app, ["package", str(sample_py_file), "--no-group-imports"])
    assert result.exit_code == 0

    # Check that imports are not grouped
    assert "# Standard library imports" not in result.stdout
    assert "# Third party imports" not in result.stdout


def test_package_no_comments(sample_py_file):
    """Test packaging without comments."""
    result = runner.invoke(app, ["package", str(sample_py_file), "--no-comments"])
    assert result.exit_code == 0

    # Check that comments are stripped
    assert "#" not in result.stdout or "#!/bin/bash" in result.stdout


def test_package_verbose(sample_py_file, caplog):
    """Test verbose output."""
    result = runner.invoke(app, ["package", str(sample_py_file), "--verbose"])
    assert result.exit_code == 0

    # Check for debug messages
    assert any(record.levelname == "DEBUG" for record in caplog.records)


def test_package_invalid_file():
    """Test packaging an invalid file."""
    result = runner.invoke(app, ["package", "nonexistent.py"])
    assert result.exit_code == 2
    assert "does not exist" in result.stdout.lower()


def test_package_non_python_file(tmp_path):
    """Test packaging a non-Python file."""
    text_file = tmp_path / "file.txt"
    text_file.write_text("Not a Python file")

    result = runner.invoke(app, ["package", str(text_file)])
    assert result.exit_code == 2
    assert "must be a python file" in result.stdout.lower()


def test_version():
    """Test version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Python Script Packager" in result.stdout


@pytest.fixture
def temp_py_file(tmp_path) -> Path:
    """Create a temporary Python file."""
    content = '''
def hello():
    """Say hello."""
    print("Hello, world!")

if __name__ == "__main__":
    hello()
'''
    file_path = tmp_path / "test.py"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def temp_py_dir(tmp_path) -> Path:
    """Create a temporary directory with Python files."""
    # Create main file
    main_content = """
from .utils import greet

def main():
    greet("World")

if __name__ == "__main__":
    main()
"""
    main_file = tmp_path / "main.py"
    main_file.write_text(main_content)

    # Create utils file
    utils_content = '''
def greet(name: str) -> None:
    """Greet someone."""
    print(f"Hello, {name}!")
'''
    utils_dir = tmp_path / "utils"
    utils_dir.mkdir()
    utils_file = utils_dir / "__init__.py"
    utils_file.write_text(utils_content)

    return tmp_path


def test_package_file(temp_py_file: Path, tmp_path: Path):
    """Test packaging a single file."""
    output_path = tmp_path / "output.py"
    result = runner.invoke(app, ["package", str(temp_py_file), "-o", str(output_path)])

    assert result.exit_code == 0
    assert "Successfully packaged" in result.stdout
    assert output_path.exists()
    assert "Hello, world!" in output_path.read_text()


def test_package_directory(temp_py_dir: Path, tmp_path: Path):
    """Test packaging a directory."""
    output_path = tmp_path / "output.py"
    result = runner.invoke(app, ["package", str(temp_py_dir), "-o", str(output_path)])

    assert result.exit_code == 0
    assert "Successfully packaged" in result.stdout
    assert output_path.exists()
    assert "greet" in output_path.read_text()
    assert "Hello, World" in output_path.read_text()


def test_package_no_output(temp_py_file: Path):
    """Test packaging without specifying output."""
    result = runner.invoke(app, ["package", str(temp_py_file)])

    assert result.exit_code == 0
    assert "Successfully packaged" in result.stdout
    packed_file = temp_py_file.parent / f"{temp_py_file.stem}_packed{temp_py_file.suffix}"
    assert packed_file.exists()


def test_package_no_group_imports(temp_py_file: Path, tmp_path: Path):
    """Test packaging without grouping imports."""
    output_path = tmp_path / "output.py"
    result = runner.invoke(
        app, ["package", str(temp_py_file), "-o", str(output_path), "--no-group-imports"]
    )

    assert result.exit_code == 0
    assert "Successfully packaged" in result.stdout
    assert output_path.exists()


def test_package_no_comments(temp_py_file: Path, tmp_path: Path):
    """Test packaging without preserving comments."""
    output_path = tmp_path / "output.py"
    result = runner.invoke(
        app, ["package", str(temp_py_file), "-o", str(output_path), "--no-comments"]
    )

    assert result.exit_code == 0
    assert "Successfully packaged" in result.stdout
    assert output_path.exists()
    assert '"""Say hello."""' not in output_path.read_text()


def test_list_files(temp_py_dir: Path):
    """Test listing Python files in a directory."""
    result = runner.invoke(app, ["list-files", str(temp_py_dir)])

    assert result.exit_code == 0
    assert "main.py" in result.stdout
    assert "utils/__init__.py" in result.stdout
    assert "Total: 2 files" in result.stdout


def test_list_files_empty_dir(tmp_path: Path):
    """Test listing Python files in an empty directory."""
    result = runner.invoke(app, ["list-files", str(tmp_path)])

    assert result.exit_code == 0
    assert "No Python files found" in result.stdout


def test_package_invalid_input():
    """Test packaging with invalid input path."""
    result = runner.invoke(app, ["package", "nonexistent.py"])

    assert result.exit_code == 2
    assert "does not exist" in result.stdout.lower()


def test_list_files_invalid_dir():
    """Test listing files with invalid directory."""
    result = runner.invoke(app, ["list-files", "nonexistent"])

    assert result.exit_code == 2
    assert "does not exist" in result.stdout.lower()
