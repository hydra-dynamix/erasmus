"""Tests for the parser module."""

import pytest
from pathlib import Path
from src.parser import (
    normalize_import_name,
    extract_imports,
    strip_imports,
    parse_file,
    parse_multiple_files,
)


def test_normalize_import_name():
    """Test import name normalization."""
    assert normalize_import_name("numpy>=1.20.0") == "numpy"
    assert normalize_import_name("pandas<=2.0.0") == "pandas"
    assert normalize_import_name("requests==2.28.0") == "requests"
    assert normalize_import_name("  scipy  ") == "scipy"


def test_extract_imports():
    """Test import extraction from source code."""
    source = """
    import os
    from sys import version
    from pathlib import Path as P
    from .utils import helper
    import numpy as np
    from pandas import DataFrame
    """

    imports = extract_imports(source)
    expected = {"os", "sys", "pathlib", "numpy", "pandas"}
    assert imports == expected


def test_extract_imports_with_errors():
    """Test import extraction with syntax errors."""
    source = """
    import os
    from sys import version
    def broken_function(
    """

    imports = extract_imports(source)
    assert "os" in imports
    assert "sys" in imports


def test_strip_imports():
    """Test stripping imports from source code."""
    source = """
    import os
    from sys import version
    
    def main():
        print(os.getcwd())
        print(version)
    """

    stripped = strip_imports(source)
    assert "import os" not in stripped
    assert "from sys import version" not in stripped
    assert "def main():" in stripped
    assert "print(os.getcwd())" in stripped
    assert "print(version)" in stripped


def test_strip_imports_preserve_comments():
    """Test stripping imports while preserving comments."""
    source = """
    # This is a comment
    import os
    from sys import version
    
    def main():
        # Another comment
        print(os.getcwd())
    """

    stripped = strip_imports(source, preserve_comments=True)
    assert "# This is a comment" in stripped
    assert "# Another comment" in stripped
    assert "import os" not in stripped


def test_parse_file(tmp_path):
    """Test parsing a Python file."""
    # Create a temporary Python file
    file_path = tmp_path / "test.py"
    file_path.write_text("""
    import os
    from sys import version
    
    def main():
        print(os.getcwd())
    """)

    imports, stripped = parse_file(file_path)
    assert "os" in imports
    assert "sys" in imports
    assert "def main():" in stripped


def test_parse_multiple_files(tmp_path):
    """Test parsing multiple Python files."""
    # Create temporary Python files
    file1 = tmp_path / "test1.py"
    file2 = tmp_path / "test2.py"

    file1.write_text("""
    import os
    from sys import version
    """)

    file2.write_text("""
    import numpy as np
    from pandas import DataFrame
    """)

    imports, stripped_files = parse_multiple_files([file1, file2])
    expected = {"os", "sys", "numpy", "pandas"}
    assert imports == expected
    assert len(stripped_files) == 2


def test_parse_file_not_found():
    """Test parsing a non-existent file."""
    with pytest.raises(FileNotFoundError):
        parse_file("nonexistent.py")


def test_parse_multiple_files_with_errors(tmp_path):
    """Test parsing multiple files with some errors."""
    # Create one valid and one invalid file
    file1 = tmp_path / "test1.py"
    file2 = tmp_path / "test2.py"

    file1.write_text("import os")
    file2.write_text("def broken_function(")  # Invalid syntax

    imports, stripped_files = parse_multiple_files([file1, file2])
    assert "os" in imports
    assert len(stripped_files) == 1  # Only one file should be processed successfully
