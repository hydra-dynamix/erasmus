"""Tests for the Python script packager."""
import os
import ast
import sys
import pytest
from pathlib import Path
from src.packager import ScriptPackager

@pytest.fixture
def test_files(tmp_path):
    """Create test Python files for packaging."""
    # Create a simple module
    module_path = tmp_path / "module.py"
    module_path.write_text("""
import os
import sys
from pathlib import Path

def helper():
    return "helper function"
""")
    
    # Create a main script that imports the module
    main_path = tmp_path / "main.py"
    main_path.write_text("""
import os
import sys
from pathlib import Path
from module import helper

def main():
    print(helper())
    return 0

if __name__ == '__main__':
    sys.exit(main())
""")
    
    return tmp_path

def test_extract_imports():
    """Test import extraction from source code."""
    code = """
import os
import sys
from pathlib import Path
from module import helper
"""
    packager = ScriptPackager(Path())
    imports = packager.extract_imports(code)
    assert imports == {"os", "sys", "pathlib", "module"}

def test_strip_imports():
    """Test stripping imports while preserving code."""
    code = """
import os
import sys

def main():
    print("Hello")
    return 0

if __name__ == '__main__':
    sys.exit(main())
"""
    packager = ScriptPackager(Path())
    stripped = packager.strip_imports(code)
    assert "import" not in stripped
    assert "def main():" in stripped
    assert "if __name__ ==" in stripped
    assert "__main__" in stripped
    assert "sys.exit(main())" in stripped

def test_collect_python_files(test_files):
    """Test Python file collection."""
    packager = ScriptPackager(test_files)
    files = list(packager.collect_python_files())
    assert len(files) == 2
    assert any(f.name == "module.py" for f in files)
    assert any(f.name == "main.py" for f in files)

def test_process_file(test_files):
    """Test processing a single Python file."""
    packager = ScriptPackager(test_files)
    module_path = test_files / "module.py"
    packager.process_file(module_path)
    
    assert packager.import_set == {"os", "sys", "pathlib"}
    assert len(packager.script_bodies) == 2  # Source comment and code
    assert "def helper():" in packager.script_bodies[1]

def test_generate_uv_bootstrap():
    """Test uv bootstrap code generation."""
    packager = ScriptPackager(Path())
    packager.requirements = {"requests", "pytest"}
    bootstrap = packager.generate_uv_bootstrap()
    
    assert "def bootstrap_uv():" in bootstrap
    assert "write_requirements()" in bootstrap
    assert "subprocess.run" in bootstrap
    assert "requirements.txt" in bootstrap

def test_package_scripts(test_files):
    """Test complete script packaging."""
    packager = ScriptPackager(test_files)
    output_path = test_files / "dist" / "packaged.py"
    
    # Package the scripts
    result = packager.package_scripts(output_path)
    
    # Verify the output
    assert output_path.exists()
    content = output_path.read_text()
    
    # Check structure
    assert "#!/usr/bin/env python3" in content
    assert "import os" in content
    assert "import sys" in content
    assert "def helper():" in content
    assert "def main():" in content
    assert "bootstrap_uv()" in content
    
    # Check file permissions
    assert os.access(output_path, os.X_OK)  # Should be executable

def test_package_scripts_no_output():
    """Test packaging without writing to file."""
    packager = ScriptPackager(Path())
    result = packager.package_scripts()
    
    assert isinstance(result, str)
    assert "#!/usr/bin/env python3" in result
    assert "import sys" in result

def test_package_scripts_invalid_path():
    """Test packaging with invalid output path."""
    packager = ScriptPackager(Path())
    invalid_path = Path("/nonexistent/directory/script.py")
    
    with pytest.raises(Exception):
        packager.package_scripts(invalid_path) 