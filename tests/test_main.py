"""Tests for the main script functionality."""
import os
import json
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from src.version_manager import VersionManager
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import main

@pytest.fixture
def test_env(tmp_path):
    """Set up test environment with necessary files."""
    # Create test directories
    release_dir = tmp_path / "release"
    release_dir.mkdir(exist_ok=True)
    
    # Create version-specific directory
    version_dir = release_dir / "v0.0.1"
    version_dir.mkdir(exist_ok=True)
    
    # Create mock install.sh
    install_sh = tmp_path / "install.sh"
    install_sh.write_text("#!/bin/bash\necho 'Test script'")
    
    # Create versioned shell script
    versioned_sh = version_dir / "erasmus_v0.0.1.sh"
    versioned_sh.write_text("#!/bin/bash\necho 'Versioned test script'")
    
    # Create mock version.json
    version_json = tmp_path / "version.json"
    version_data = {
        "version": "0.0.1",
        "last_updated": "2025-04-06T00:00:00Z",
        "changes": []
    }
    version_json.write_text(json.dumps(version_data))
    
    # Store original paths
    old_cwd = os.getcwd()
    old_version_file = VersionManager.VERSION_FILE
    
    # Set up test paths
    os.chdir(tmp_path)
    VersionManager.VERSION_FILE = version_json
    
    yield tmp_path
    
    # Cleanup
    os.chdir(old_cwd)
    VersionManager.VERSION_FILE = old_version_file

def test_convert_scripts(test_env):
    """Test script conversion creates versioned files."""
    version = "1.0.0"
    result = main.convert_scripts(version)
    
    assert result == 0
    assert (test_env / "release" / f"v{version}" / f"erasmus_v{version}.bat").exists()
    assert (test_env / "release" / f"v{version}" / f"erasmus_v{version}.sh").exists()

def test_convert_scripts_missing_shell(test_env):
    """Test script conversion handles missing shell script."""
    (test_env / "install.sh").unlink()
    result = main.convert_scripts("1.0.0")
    assert result == 1

@pytest.mark.parametrize("command,args,expected_version", [
    (["version", "get"], None, "0.0.1"),
    (["version", "patch"], None, "0.0.2"),
    (["version", "minor"], None, "0.1.0"),
    (["version", "major"], None, "1.0.0"),
])
def test_version_commands(test_env, command, args, expected_version):
    """Test version management commands."""
    test_args = command if args is None else command + args
    
    with patch("sys.argv", ["main.py"] + test_args):
        with patch("builtins.print") as mock_print:
            main.main()
            
            # Check if version was printed
            if command[1] == "get":
                mock_print.assert_called_with(f"Current version: {expected_version}")
            else:
                # The last print call should be the version update message
                mock_print.assert_any_call(f"Updated to version: {expected_version}")
            
            # Check version file was updated
            with open(VersionManager.VERSION_FILE) as f:
                version_data = json.load(f)
                assert version_data["version"] == expected_version

def test_version_increment_with_message(test_env):
    """Test version increment with custom message."""
    message = "Test version update"
    with patch("sys.argv", ["main.py", "version", "patch", "-m", message]):
        main.main()
        
        with open(VersionManager.VERSION_FILE) as f:
            version_data = json.load(f)
            assert len(version_data["changes"]) == 1
            assert version_data["changes"][0]["description"] == message
            assert version_data["changes"][0]["type"] == "patch"

def test_convert_command(test_env):
    """Test convert command without version change."""
    with patch("sys.argv", ["main.py", "convert"]):
        result = main.main()
        assert result == 0
        
        version = VersionManager().get_current_version()
        assert (test_env / "release" / f"v{version}" / f"erasmus_v{version}.bat").exists()
        assert (test_env / "release" / f"v{version}" / f"erasmus_v{version}.sh").exists()

def test_invalid_command(test_env):
    """Test handling of invalid or missing command."""
    with patch("sys.argv", ["main.py"]):
        with patch("argparse.ArgumentParser.print_help") as mock_help:
            result = main.main()
            assert result == 1
            mock_help.assert_called_once()
