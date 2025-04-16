"""Tests for the Typer-based CLI interface."""

import os
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from packager.__main__ import app

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
def temp_py_dir(tmp_path):
    """Create a temporary directory with Python files."""
    # Create a simple module
    module_dir = tmp_path / "mymodule"
    module_dir.mkdir()

    # Create __init__.py
    init_file = module_dir / "__init__.py"
    init_file.write_text("")

    # Create main.py
    main_file = module_dir / "main.py"
    main_file.write_text(
        dedent("""
        def greet(name="World"):
            return f"Hello, {name}!"

        if __name__ == '__main__':
            print(greet())
    """).strip()
    )

    return module_dir


def test_package_single_file(sample_py_file, tmp_path):
    """Test packaging a single Python file."""
    output_path = tmp_path / "output.py"
    result = runner.invoke(app, ["package", str(sample_py_file), "-o", str(output_path)])

    assert result.exit_code == 0
    assert "Successfully packaged" in result.stdout
    assert output_path.exists()
    assert "numpy" in output_path.read_text()
    assert "pandas" in output_path.read_text()
    assert "matplotlib" in output_path.read_text()


def test_package_directory(temp_py_dir, tmp_path):
    """Test packaging a directory."""
    output_path = tmp_path / "output.py"
    result = runner.invoke(app, ["package", str(temp_py_dir), "-o", str(output_path)])

    assert result.exit_code == 0
    assert "Successfully packaged" in result.stdout
    assert output_path.exists()
    assert "greet" in output_path.read_text()
    assert "Hello, World" in output_path.read_text()


def test_package_no_output(sample_py_file, tmp_path):
    """Test packaging without specifying output path."""
    result = runner.invoke(app, ["package", str(sample_py_file)])

    assert result.exit_code == 0
    assert "Successfully packaged" in result.stdout

    # Check if file was created in build directory
    build_dir = Path("build")
    assert build_dir.exists()
    assert any(build_dir.glob("*_packed.py"))


def test_package_no_comments(sample_py_file, tmp_path):
    """Test packaging with --no-comments flag."""
    output_path = tmp_path / "output.py"
    result = runner.invoke(
        app, ["package", str(sample_py_file), "-o", str(output_path), "--no-comments"]
    )

    assert result.exit_code == 0
    assert "Successfully packaged" in result.stdout
    assert output_path.exists()

    # Comments should be stripped
    content = output_path.read_text()
    assert "# This is a comment" not in content


def test_package_custom_build_dir(sample_py_file, tmp_path):
    """Test packaging with custom build directory."""
    build_dir = tmp_path / "custom_build"
    result = runner.invoke(app, ["package", str(sample_py_file), "--build-dir", str(build_dir)])

    assert result.exit_code == 0
    assert "Successfully packaged" in result.stdout
    assert build_dir.exists()
    assert any(build_dir.glob("*_packed.py"))


def test_package_invalid_input():
    """Test packaging with invalid input path."""
    result = runner.invoke(app, ["package", "nonexistent.py"])

    assert result.exit_code == 1
    assert "Error" in result.stdout


def test_list_files(temp_py_dir):
    """Test listing Python files in a directory."""
    result = runner.invoke(app, ["list-files", str(temp_py_dir)])

    assert result.exit_code == 0
    assert "__init__.py" in result.stdout
    assert "main.py" in result.stdout
    assert "Total:" in result.stdout


def test_list_files_empty_dir(tmp_path):
    """Test listing Python files in an empty directory."""
    result = runner.invoke(app, ["list-files", str(tmp_path)])

    assert result.exit_code == 0
    assert "No Python files found" in result.stdout


def test_list_files_invalid_dir():
    """Test listing files with invalid directory."""
    result = runner.invoke(app, ["list-files", "nonexistent"])

    assert result.exit_code == 1
    assert "Error" in result.stdout
