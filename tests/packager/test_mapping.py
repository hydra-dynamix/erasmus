"""Tests for the mapping module."""

import json
import pytest
from pathlib import Path
from packager.mapping import (
    get_package_name,
    register_mapping,
    map_imports_to_packages,
    load_mappings_from_file,
    save_mappings_to_file,
    get_all_mappings,
    clear_custom_mappings,
)


def test_get_package_name():
    """Test getting package name from import name."""
    # Test common mappings
    assert get_package_name("cv2") == "opencv-python"
    assert get_package_name("PIL") == "pillow"
    assert get_package_name("numpy") == "numpy"
    assert get_package_name("pandas") == "pandas"

    # Test aliases
    assert get_package_name("np") == "numpy"
    assert get_package_name("pd") == "pandas"
    assert get_package_name("plt") == "matplotlib"

    # Test standard library modules
    assert get_package_name("os") == "os"
    assert get_package_name("sys") == "sys"
    assert get_package_name("json") == "json"

    # Test non-existent mapping (should return the import name)
    assert get_package_name("nonexistent_module") == "nonexistent_module"


def test_register_mapping():
    """Test registering custom mappings."""
    # Register a custom mapping
    register_mapping("custom_module", "custom-package")
    assert get_package_name("custom_module") == "custom-package"

    # Register another mapping
    register_mapping("another_module", "another-package")
    assert get_package_name("another_module") == "another-package"

    # Override an existing mapping
    register_mapping("numpy", "custom-numpy")
    assert get_package_name("numpy") == "custom-numpy"

    # Clear custom mappings for other tests
    clear_custom_mappings()


def test_map_imports_to_packages():
    """Test mapping multiple imports to packages."""
    imports = {"cv2", "numpy", "pandas", "os", "custom_module"}

    # Register a custom mapping
    register_mapping("custom_module", "custom-package")

    # Map imports to packages
    package_map = map_imports_to_packages(imports)

    # Check the results
    assert package_map["cv2"] == "opencv-python"
    assert package_map["numpy"] == "numpy"
    assert package_map["pandas"] == "pandas"
    assert package_map["os"] == "os"
    assert package_map["custom_module"] == "custom-package"

    # Clear custom mappings for other tests
    clear_custom_mappings()


def test_load_and_save_mappings(tmp_path):
    """Test loading and saving mappings from/to a file."""
    # Create a temporary JSON file
    json_file = tmp_path / "mappings.json"

    # Create some custom mappings
    custom_mappings = {
        "test_module": "test-package",
        "another_module": "another-package",
    }

    # Save mappings to file
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(custom_mappings, f)

    # Load mappings from file
    load_mappings_from_file(json_file)

    # Check that mappings were loaded
    assert get_package_name("test_module") == "test-package"
    assert get_package_name("another_module") == "another-package"

    # Create a new file to save mappings to
    save_file = tmp_path / "saved_mappings.json"

    # Save current mappings
    save_mappings_to_file(save_file)

    # Check that the file was created
    assert save_file.exists()

    # Load the saved mappings into a new dictionary
    with open(save_file, "r", encoding="utf-8") as f:
        saved_mappings = json.load(f)

    # Check that the saved mappings match our custom mappings
    assert saved_mappings == custom_mappings

    # Clear custom mappings for other tests
    clear_custom_mappings()


def test_get_all_mappings():
    """Test getting all mappings."""
    # Get all mappings
    all_mappings = get_all_mappings()

    # Check that default mappings are included
    assert "cv2" in all_mappings
    assert "PIL" in all_mappings
    assert "numpy" in all_mappings

    # Register a custom mapping
    register_mapping("custom_module", "custom-package")

    # Get mappings again
    updated_mappings = get_all_mappings()

    # Check that custom mapping is included
    assert "custom_module" in updated_mappings
    assert updated_mappings["custom_module"] == "custom-package"

    # Clear custom mappings for other tests
    clear_custom_mappings()


def test_clear_custom_mappings():
    """Test clearing custom mappings."""
    # Register some custom mappings
    register_mapping("custom_module", "custom-package")
    register_mapping("another_module", "another-package")

    # Check that mappings were registered
    assert get_package_name("custom_module") == "custom-package"
    assert get_package_name("another_module") == "another-package"

    # Clear custom mappings
    clear_custom_mappings()

    # Check that custom mappings were cleared
    assert get_package_name("custom_module") == "custom_module"
    assert get_package_name("another_module") == "another_module"

    # Check that default mappings are still available
    assert get_package_name("cv2") == "opencv-python"
    assert get_package_name("PIL") == "pillow"


def test_load_nonexistent_file(tmp_path):
    """Test loading mappings from a nonexistent file."""
    # Try to load from a nonexistent file
    nonexistent_file = tmp_path / "nonexistent.json"
    load_mappings_from_file(nonexistent_file)

    # No exception should be raised, and no mappings should be loaded
    assert get_package_name("test_module") == "test_module"


def test_save_to_nonexistent_directory(tmp_path):
    """Test saving mappings to a nonexistent directory."""
    # Register a custom mapping
    register_mapping("test_module", "test-package")

    # Try to save to a nonexistent directory
    nonexistent_dir = tmp_path / "nonexistent_dir"
    save_file = nonexistent_dir / "mappings.json"

    # This should raise an exception
    with pytest.raises(Exception):
        save_mappings_to_file(save_file)

    # Clear custom mappings for other tests
    clear_custom_mappings()
