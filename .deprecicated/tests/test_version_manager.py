"""Tests for the version manager module."""
import pytest
from pathlib import Path
from erasmus.version_manager import VersionManager

@pytest.fixture
def version_manager(tmp_path):
    """Create a version manager instance with temporary file path."""
    original_file = VersionManager.VERSION_FILE
    VersionManager.VERSION_FILE = tmp_path / "version.json"
    vm = VersionManager()
    yield vm
    VersionManager.VERSION_FILE = original_file

def test_initial_version(version_manager):
    """Test initial version is 0.0.1."""
    assert version_manager.get_current_version() == "0.0.1"

def test_version_parsing(version_manager):
    """Test version string parsing."""
    assert version_manager.parse_version("1.2.3") == (1, 2, 3)
    assert version_manager.parse_version("invalid") is None

def test_version_increment(version_manager):
    """Test version incrementing."""
    # Test patch increment
    assert version_manager.increment_version("patch") == "0.0.2"
    
    # Test minor increment
    assert version_manager.increment_version("minor") == "0.1.0"
    
    # Test major increment
    assert version_manager.increment_version("major") == "1.0.0"

def test_add_change(version_manager):
    """Test adding changes and updating version."""
    version_manager.add_change("Test change", "minor")
    changelog = version_manager.get_changelog()
    
    assert len(changelog) == 1
    assert changelog[0]["description"] == "Test change"
    assert changelog[0]["type"] == "minor"
    assert version_manager.get_current_version() == "0.1.0"

def test_version_persistence(tmp_path):
    """Test version data persists between instances."""
    VersionManager.VERSION_FILE = tmp_path / "version.json"
    
    # First instance
    vm1 = VersionManager()
    vm1.add_change("Test change", "minor")
    
    # Second instance should load the saved data
    vm2 = VersionManager()
    assert vm2.get_current_version() == "0.1.0"
    assert len(vm2.get_changelog()) == 1
