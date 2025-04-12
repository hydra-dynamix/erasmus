"""
Tests for the collector module.

This module contains tests for the file collection functionality.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add the src directory to the path so we can import the collector module
sys.path.insert(0, "src")

from collector import (
    collect_py_files,
    collect_files_with_extensions,
    collect_files_with_filter,
    get_relative_paths,
)


class TestCollectorModule(unittest.TestCase):
    """Test cases for the collector module."""

    def setUp(self):
        """Set up a temporary directory structure for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = self.temp_dir.name

        # Create a simple directory structure with various file types
        self.create_test_files()

    def tearDown(self):
        """Clean up the temporary directory."""
        self.temp_dir.cleanup()

    def create_test_files(self):
        """Create a test directory structure with various files."""
        # Main Python files
        self.create_file("main.py", "print('Main module')")
        self.create_file("utils.py", "def util_func(): pass")
        
        # Subdirectory with Python files
        os.mkdir(os.path.join(self.base_path, "subdir"))
        self.create_file("subdir/module.py", "def module_func(): pass")
        self.create_file("subdir/another.py", "class AnotherClass: pass")
        
        # Non-Python files
        self.create_file("README.md", "# Test Project")
        self.create_file("config.json", "{}")
        
        # Files that should be excluded
        os.mkdir(os.path.join(self.base_path, "__pycache__"))
        self.create_file("__pycache__/module.cpython-39.pyc", "# Compiled")
        
        # Another subdirectory with mixed files
        os.mkdir(os.path.join(self.base_path, "src"))
        self.create_file("src/core.py", "# Core module")
        self.create_file("src/helpers.js", "// JavaScript helpers")
        self.create_file("src/styles.css", "/* CSS styles */")

    def create_file(self, relative_path, content):
        """Helper to create a file with content in the test directory."""
        full_path = os.path.join(self.base_path, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)

    def test_collect_py_files(self):
        """Test collecting Python files."""
        py_files = collect_py_files(self.base_path)
        
        # We should find 5 Python files
        self.assertEqual(len(py_files), 5)
        
        # Check that all collected files have .py extension
        for file in py_files:
            self.assertTrue(file.endswith('.py'))
        
        # Check that specific files are included
        expected_files = [
            os.path.join(self.base_path, "main.py"),
            os.path.join(self.base_path, "utils.py"),
            os.path.join(self.base_path, "subdir/module.py"),
            os.path.join(self.base_path, "subdir/another.py"),
            os.path.join(self.base_path, "src/core.py"),
        ]
        
        # Convert to sets for comparison (order doesn't matter)
        self.assertEqual(set(py_files), set(expected_files))

    def test_collect_files_with_extensions(self):
        """Test collecting files with specific extensions."""
        # Test with multiple extensions
        js_css_files = collect_files_with_extensions(
            self.base_path, extensions=['.js', '.css']
        )
        
        # We should find 2 files (.js and .css)
        self.assertEqual(len(js_css_files), 2)
        
        # Check that specific files are included
        expected_files = [
            os.path.join(self.base_path, "src/helpers.js"),
            os.path.join(self.base_path, "src/styles.css"),
        ]
        
        # Convert to sets for comparison (order doesn't matter)
        self.assertEqual(set(js_css_files), set(expected_files))

    def test_collect_files_with_filter(self):
        """Test collecting files using a custom filter function."""
        # Filter function to find files containing 'module' in their name
        def filter_func(file_path):
            return 'module' in os.path.basename(file_path).lower()
        
        module_files = collect_files_with_filter(
            self.base_path, filter_func=filter_func
        )
        
        # We should find 1 file with 'module' in their name (the .pyc file is excluded)
        self.assertEqual(len(module_files), 1)
        
        # Check that specific files are included
        expected_files = [
            os.path.join(self.base_path, "subdir/module.py"),
            # The .pyc file should be excluded by default patterns
        ]
        
        # Convert to sets for comparison (order doesn't matter)
        self.assertEqual(set(module_files), set(expected_files))

    def test_get_relative_paths(self):
        """Test converting absolute paths to relative paths."""
        absolute_paths = [
            os.path.join(self.base_path, "main.py"),
            os.path.join(self.base_path, "subdir/module.py"),
            os.path.join(self.base_path, "src/core.py"),
        ]
        
        relative_paths = get_relative_paths(absolute_paths, self.base_path)
        
        expected_relative_paths = [
            "main.py",
            os.path.join("subdir", "module.py"),
            os.path.join("src", "core.py"),
        ]
        
        self.assertEqual(relative_paths, expected_relative_paths)

    def test_exclusion_patterns(self):
        """Test that exclusion patterns work correctly."""
        # Create a directory that should be excluded
        os.mkdir(os.path.join(self.base_path, ".git"))
        self.create_file(".git/config", "# Git config")
        self.create_file(".git/HEAD", "ref: refs/heads/main")
        
        # Create a file that should be excluded
        self.create_file("temp.pyc", "# Compiled Python")
        
        py_files = collect_py_files(self.base_path)
        
        # The .git directory and .pyc file should be excluded
        for file in py_files:
            self.assertFalse(".git" in file)
            self.assertFalse(file.endswith(".pyc"))

    def test_nonexistent_directory(self):
        """Test behavior with a nonexistent directory."""
        with self.assertRaises(FileNotFoundError):
            collect_py_files(os.path.join(self.base_path, "nonexistent"))

    def test_file_as_base_path(self):
        """Test behavior when a file is provided as the base path."""
        file_path = os.path.join(self.base_path, "main.py")
        with self.assertRaises(NotADirectoryError):
            collect_py_files(file_path)


if __name__ == '__main__':
    unittest.main()
