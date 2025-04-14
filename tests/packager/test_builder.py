"""
Tests for the builder module.

This module contains tests for the builder module, which is responsible for
merging stripped code bodies and imports into a single executable script.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.builder import (
    build_script,
    format_imports,
    generate_script,
    merge_code_bodies,
)


def test_format_imports():
    """Test the format_imports function."""
    # Test with empty imports
    assert format_imports(set()) == ""

    # Test with simple imports
    imports = {"numpy", "pandas"}
    formatted = format_imports(imports, group_by_type=False)
    assert "import numpy" in formatted
    assert "import pandas" in formatted

    # Test with grouped imports
    imports = {"numpy", "pandas", "os", "sys", ".local_module"}
    formatted = format_imports(imports)

    # Check that imports are grouped
    assert "# Standard library imports" in formatted
    assert "# Third-party imports" in formatted
    assert "# Local imports" in formatted

    # Check that each import is present
    assert "import numpy" in formatted
    assert "import pandas" in formatted
    assert "import os" in formatted
    assert "import sys" in formatted
    assert "import .local_module" in formatted


def test_merge_code_bodies(tmp_path):
    """Test the merge_code_bodies function."""
    # Create test files
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"

    file1.write_text("""
import os

def function1():
    print("Hello from file1")
""")

    file2.write_text("""
import sys

def function2():
    print("Hello from file2")
""")

    # Merge code bodies
    merged = merge_code_bodies([str(file1), str(file2)])

    # Check that both functions are present
    assert "def function1()" in merged
    assert "def function2()" in merged

    # Check that imports are stripped
    assert "import os" not in merged
    assert "import sys" not in merged

    # Check that file separators are added
    assert "# Code from file1.py" in merged
    assert "# Code from file2.py" in merged


def test_build_script(tmp_path):
    """Test the build_script function."""
    # Create test files
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"

    file1.write_text("""
import os

def function1():
    print("Hello from file1")
""")

    file2.write_text("""
import sys
import numpy

def function2():
    print("Hello from file2")
""")

    # Build script
    script = build_script([str(file1), str(file2)])

    # Check that the script has the correct structure
    assert "#!/usr/bin/env python" in script
    assert "# -*- coding: utf-8 -*-" in script
    assert '"""' in script
    assert "Auto-generated script by Python Script Packager" in script

    # Check that imports are formatted correctly
    assert "# Standard library imports" in script
    assert "import os" in script
    assert "import sys" in script

    assert "# Third-party imports" in script
    assert "import numpy" in script

    # Check that both functions are present
    assert "def function1()" in script
    assert "def function2()" in script


def test_generate_script_file(tmp_path):
    """Test the generate_script function with a single file."""
    # Create a test file
    input_file = tmp_path / "input.py"
    output_file = tmp_path / "output.py"

    input_file.write_text("""
import os

def main():
    print("Hello, world!")
""")

    # Generate script
    generate_script(input_file, output_file)

    # Check that the output file exists
    assert output_file.exists()

    # Check that the output file has the correct content
    output_content = output_file.read_text()
    assert "#!/usr/bin/env python" in output_content
    assert "import os" in output_content
    assert "def main()" in output_content
    assert "print('Hello, world!')" in output_content


def test_generate_script_directory(tmp_path):
    """Test the generate_script function with a directory."""
    # Create test files in a directory
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    file1 = input_dir / "file1.py"
    file2 = input_dir / "file2.py"

    file1.write_text("""
import os

def function1():
    print("Hello from file1")
""")

    file2.write_text("""
import sys
import numpy

def function2():
    print("Hello from file2")
""")

    output_file = tmp_path / "output.py"

    # Generate script
    generate_script(input_dir, output_file)

    # Check that the output file exists
    assert output_file.exists()

    # Check that the output file has the correct content
    output_content = output_file.read_text()
    assert "#!/usr/bin/env python" in output_content
    assert "import os" in output_content
    assert "import sys" in output_content
    assert "import numpy" in output_content
    assert "def function1()" in output_content
    assert "def function2()" in output_content


def test_generate_script_no_output(tmp_path):
    """Test the generate_script function without an output file."""
    # Create a test file
    input_file = tmp_path / "input.py"

    input_file.write_text("""
import os

def main():
    print("Hello, world!")
""")

    # Generate script
    script = generate_script(input_file)

    # Check that the script has the correct content
    assert "#!/usr/bin/env python" in script
    assert "import os" in script
    assert "def main()" in script
    assert "print('Hello, world!')" in script


def test_generate_script_nonexistent_input():
    """Test the generate_script function with a nonexistent input."""
    with pytest.raises(FileNotFoundError):
        generate_script("nonexistent.py")


def test_generate_script_empty_directory(tmp_path):
    """Test the generate_script function with an empty directory."""
    # Create an empty directory
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    # Generate script
    with pytest.raises(ValueError):
        generate_script(input_dir)


def test_generate_script_no_comments(tmp_path):
    """Test the generate_script function with no comments."""
    # Create a test file
    input_file = tmp_path / "input.py"
    output_file = tmp_path / "output.py"

    input_file.write_text("""
import os

# This is a comment
def main():
    # This is another comment
    print("Hello, world!")
""")

    # Generate script
    generate_script(input_file, output_file, preserve_comments=False)

    # Check that the output file has the correct content
    output_content = output_file.read_text()
    assert "#!/usr/bin/env python" in output_content
    assert "import os" in output_content
    assert "def main()" in output_content
    assert "print('Hello, world!')" in output_content
    assert "# This is a comment" not in output_content
    assert "# This is another comment" not in output_content


def test_generate_script_no_group_imports(tmp_path):
    """Test the generate_script function with no grouped imports."""
    # Create a test file
    input_file = tmp_path / "input.py"
    output_file = tmp_path / "output.py"

    input_file.write_text("""
import os
import sys
import numpy

def main():
    print("Hello, world!")
""")

    # Generate script
    generate_script(input_file, output_file, group_imports=False)

    # Check that the output file has the correct content
    output_content = output_file.read_text()
    assert "#!/usr/bin/env python" in output_content
    assert (
        "import os" in output_content
        or "import sys" in output_content
        or "import numpy" in output_content
    )
    assert "def main()" in output_content
    assert "print('Hello, world!')" in output_content

    # Check that imports are not grouped
    assert "# Standard library imports" not in output_content
    assert "# Third-party imports" not in output_content
