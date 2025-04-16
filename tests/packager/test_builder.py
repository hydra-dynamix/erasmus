"""
Tests for the builder module.

This module contains tests for the builder module, which is responsible for
merging stripped code bodies and imports into a single executable script.
"""

import os
import tempfile
from pathlib import Path

import pytest

from packager.builder import build_script, format_imports, generate_script, extract_code_body
from packager.parser import ImportSet


def test_format_imports():
    """Test the format_imports function."""
    # Test with empty ImportSet
    empty_imports = ImportSet()
    assert format_imports(empty_imports) == ""

    # Test with simple imports
    imports = ImportSet()
    imports.add_import("numpy")
    imports.add_import("pandas")
    formatted = format_imports(imports, group_imports=False)
    assert "import numpy" in formatted
    assert "import pandas" in formatted

    # Test with grouped imports
    imports = ImportSet()
    imports.add_import("os")
    imports.add_import("sys")
    imports.add_import("numpy")
    imports.add_import("pandas")
    imports.add_import(".local_module")
    formatted = format_imports(imports)

    # Check that imports are grouped
    assert "# Standard library imports" in formatted
    assert "# Third-party imports" in formatted
    assert "# Relative imports" in formatted

    # Check that each import is present in the correct section
    assert "import os" in formatted
    assert "import sys" in formatted
    assert "import numpy" in formatted
    assert "import pandas" in formatted
    assert "from .local_module import *" in formatted

    # Verify order
    lines = formatted.split("\n")
    stdlib_idx = lines.index("# Standard library imports")
    thirdparty_idx = lines.index("# Third-party imports")
    relative_idx = lines.index("# Relative imports")

    assert stdlib_idx < thirdparty_idx < relative_idx


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
    merged = extract_code_body([str(file1), str(file2)])

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
    """Test building a script from multiple files."""
    # Create test files
    file1 = tmp_path / "test1.py"
    file2 = tmp_path / "test2.py"

    file1.write_text("""
import os
from pathlib import Path

def func1():
    print("Hello")
""")

    file2.write_text("""
import sys
from .local import something

def func2():
    print("World")
""")

    # Build script
    imports, script = build_script([file1, file2], tmp_path)

    # Verify imports
    assert "os" in imports.stdlib
    assert "pathlib" in imports.stdlib
    assert "sys" in imports.stdlib
    assert ".local" in imports.relative

    # Verify script content
    assert "#!/usr/bin/env python3" in script
    assert "# -*- coding: utf-8 -*-" in script
    assert "Auto-generated script by Python Script Packager" in script
    assert "import os" in script
    assert "from pathlib import Path" in script
    assert "import sys" in script
    assert "from .local import something" in script
    assert "def func1():" in script
    assert "def func2():" in script
    assert "# Code from test1.py" in script
    assert "# Code from test2.py" in script


def test_generate_script_file(tmp_path):
    """Test generating a script from a single file."""
    # Create test file
    file1 = tmp_path / "test1.py"
    file1.write_text("""
import os
from pathlib import Path

def func1():
    print("Hello")
""")

    # Generate script
    script = generate_script([file1], tmp_path)

    # Verify script content
    assert "#!/usr/bin/env python3" in script
    assert "# -*- coding: utf-8 -*-" in script
    assert "Auto-generated script by Python Script Packager" in script
    assert "import os" in script
    assert "from pathlib import Path" in script
    assert "def func1():" in script
    assert 'print("Hello")' in script
    assert "# Code from test1.py" in script


def test_generate_script_directory(tmp_path):
    """Test generating a script from a directory of files."""
    # Create test directory structure
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    file1 = src_dir / "test1.py"
    file2 = src_dir / "test2.py"

    file1.write_text("""
import os
from pathlib import Path

def func1():
    print("Hello")
""")

    file2.write_text("""
import sys
from .local import something

def func2():
    print("World")
""")

    # Generate script
    script = generate_script([file1, file2], tmp_path)

    # Verify script content
    assert "#!/usr/bin/env python3" in script
    assert "# -*- coding: utf-8 -*-" in script
    assert "Auto-generated script by Python Script Packager" in script
    assert "import os" in script
    assert "from pathlib import Path" in script
    assert "import sys" in script
    assert "from .local import something" in script
    assert "def func1():" in script
    assert "def func2():" in script
    assert 'print("Hello")' in script
    assert 'print("World")' in script
    assert "# Code from test1.py" in script
    assert "# Code from test2.py" in script


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
    assert 'print("Hello, world!")' in script or "print('Hello, world!')" in script


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
    """Test generating a script without comments."""
    # Create test files
    file1 = tmp_path / "test1.py"
    file2 = tmp_path / "test2.py"

    file1.write_text("""
import os
from pathlib import Path

def func1():
    print("Hello")
""")

    file2.write_text("""
import sys
from .local import something

def func2():
    print("World")
""")

    # Generate script without comments
    script = generate_script([file1, file2], tmp_path, preserve_comments=False)

    # Verify script content
    assert "#!/usr/bin/env python3" in script
    assert "# -*- coding: utf-8 -*-" in script
    assert "Auto-generated script by Python Script Packager" in script
    assert "import os" in script
    assert "from pathlib import Path" in script
    assert "import sys" in script
    assert "from .local import something" in script
    assert "def func1():" in script
    assert "def func2():" in script
    assert 'print("Hello")' in script
    assert 'print("World")' in script
    assert "# Code from test1.py" not in script
    assert "# Code from test2.py" not in script


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
    assert 'print("Hello, world!")' in output_content or "print('Hello, world!')" in output_content

    # Check that imports are not grouped
    assert "# Standard library imports" not in output_content
    assert "# Third-party imports" not in output_content


def test_extract_code_body_single_file(tmp_path):
    # Create a test file
    test_file = tmp_path / "test.py"
    test_file.write_text("""
import os
import sys
from pathlib import Path

def main():
    print("Hello")
    return 0

if __name__ == "__main__":
    main()
""")

    # Extract code body
    code_body = extract_code_body([test_file])

    # Verify imports are removed but code is preserved
    assert "import os" not in code_body
    assert "import sys" not in code_body
    assert "from pathlib import Path" not in code_body
    assert "def main():" in code_body
    assert 'print("Hello")' in code_body
    assert "return 0" in code_body
    assert 'if __name__ == "__main__":' in code_body


def test_extract_code_body_multiple_files(tmp_path):
    # Create test files
    file1 = tmp_path / "file1.py"
    file1.write_text("""
import os

def func1():
    return 1
""")

    file2 = tmp_path / "file2.py"
    file2.write_text("""
import sys

def func2():
    return 2
""")

    # Extract code body
    code_body = extract_code_body([file1, file2])

    # Verify both files are included with proper headers
    assert "# Code from file1.py" in code_body
    assert "# Code from file2.py" in code_body
    assert "def func1():" in code_body
    assert "def func2():" in code_body
    assert "import os" not in code_body
    assert "import sys" not in code_body


def test_generate_script_single_file(tmp_path):
    # Create a test file
    test_file = tmp_path / "test.py"
    test_file.write_text("""
import os
import sys
from pathlib import Path

def main():
    print("Hello")
    return 0

if __name__ == "__main__":
    main()
""")

    # Generate script
    output_file = tmp_path / "output.py"
    generate_script(test_file, output_file)

    # Verify output
    content = output_file.read_text()
    assert "#!/usr/bin/env python3" in content
    assert "import os" in content
    assert "import sys" in content
    assert "from pathlib import Path" in content
    assert "def main():" in content
    assert 'print("Hello")' in content
    assert "return 0" in content
    assert 'if __name__ == "__main__":' in content


def test_generate_script_multiple_files(tmp_path):
    # Create test files
    file1 = tmp_path / "file1.py"
    file1.write_text("""
import os

def func1():
    return 1
""")

    file2 = tmp_path / "file2.py"
    file2.write_text("""
import sys

def func2():
    return 2
""")

    # Generate script
    output_file = tmp_path / "output.py"
    generate_script(tmp_path, output_file)

    # Verify output
    content = output_file.read_text()
    assert "#!/usr/bin/env python3" in content
    assert "import os" in content
    assert "import sys" in content
    assert "# Code from file1.py" in content
    assert "# Code from file2.py" in content
    assert "def func1():" in content
    assert "def func2():" in content


def test_generate_script(tmp_path):
    """Test generating a script with various options."""
    # Create test files
    file1 = tmp_path / "test1.py"
    file2 = tmp_path / "test2.py"

    file1.write_text("""
import os
from pathlib import Path

def func1():
    print("Hello")
""")

    file2.write_text("""
import sys
from .local import something

def func2():
    print("World")
""")

    # Test with default options
    script = generate_script([file1, file2], tmp_path)
    assert "#!/usr/bin/env python3" in script
    assert "# -*- coding: utf-8 -*-" in script
    assert "Auto-generated script by Python Script Packager" in script
    assert "import os" in script
    assert "from pathlib import Path" in script
    assert "import sys" in script
    assert "from .local import something" in script
    assert "def func1():" in script
    assert "def func2():" in script
    assert "# Code from test1.py" in script
    assert "# Code from test2.py" in script

    # Test with no comments
    script = generate_script([file1, file2], tmp_path, preserve_comments=False)
    assert "#!/usr/bin/env python3" in script
    assert "# -*- coding: utf-8 -*-" in script
    assert "Auto-generated script by Python Script Packager" in script
    assert "import os" in script
    assert "from pathlib import Path" in script
    assert "import sys" in script
    assert "from .local import something" in script
    assert "def func1():" in script
    assert "def func2():" in script
    assert "# Code from test1.py" not in script
    assert "# Code from test2.py" not in script

    # Test with no import grouping
    script = generate_script([file1, file2], tmp_path, group_imports=False)
    assert "#!/usr/bin/env python3" in script
    assert "# -*- coding: utf-8 -*-" in script
    assert "Auto-generated script by Python Script Packager" in script
    assert "import os" in script
    assert "from pathlib import Path" in script
    assert "import sys" in script
    assert "from .local import something" in script
    assert "def func1():" in script
    assert "def func2():" in script
    assert "# Code from test1.py" in script
    assert "# Code from test2.py" in script
