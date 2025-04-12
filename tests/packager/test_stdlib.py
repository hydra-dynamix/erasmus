"""
Tests for the stdlib module.

This module contains tests for the standard library detection functionality.
"""

import sys
import unittest

# Add the src directory to the path so we can import the stdlib module
sys.path.insert(0, "src")

from stdlib import StdlibDetector, filter_stdlib_imports, is_stdlib_module


class TestStdlibModule(unittest.TestCase):
    """Test cases for the stdlib module."""

    def test_is_stdlib_module_basic(self):
        """Test basic standard library module detection."""
        # These should be recognized as standard library modules
        stdlib_modules = ['os', 'sys', 'json', 'pathlib', 'unittest']
        for module in stdlib_modules:
            with self.subTest(module=module):
                assert is_stdlib_module(module), f"{module} should be recognized as stdlib"

    def test_is_stdlib_module_third_party(self):
        """Test third-party module detection."""
        # These should be recognized as third-party modules
        third_party_modules = ['requests', 'numpy', 'pandas', 'tensorflow', 'django']
        for module in third_party_modules:
            with self.subTest(module=module):
                assert not is_stdlib_module(module), f"{module} should be recognized as third-party"

    def test_is_stdlib_module_submodules(self):
        """Test standard library submodule detection."""
        # These should be recognized as standard library submodules
        stdlib_submodules = ['os.path', 'urllib.parse', 'email.mime', 'xml.etree']
        for module in stdlib_submodules:
            with self.subTest(module=module):
                assert is_stdlib_module(module), f"{module} should be recognized as stdlib"

    def test_filter_stdlib_imports(self):
        """Test filtering standard library imports from a set."""
        # Mix of standard library and third-party modules
        imports = {'os', 'sys', 'json', 'requests', 'numpy'}
        # Expected result after filtering
        expected = {'requests', 'numpy'}
        # Actual result
        result = filter_stdlib_imports(imports)
        assert result == expected

    def test_custom_stdlib_detection(self):
        """Test custom stdlib detection with a manually configured detector."""
        # Create a detector with a custom set of stdlib modules
        detector = StdlibDetector()
        detector._stdlib_modules = {'os', 'sys', 'json'}
        detector._stdlib_prefixes = []
        detector._initialized = True
        # Test the detector with known stdlib modules
        assert detector.is_stdlib_module('os')
        assert detector.is_stdlib_module('sys')
        assert detector.is_stdlib_module('json')
        # Test with a non-existent module name
        # This should return False since it's not in our custom stdlib list
        # and we're using a name that definitely won't be importable
        assert not detector.is_stdlib_module('nonexistent_test_module_xyz')
    
    def test_detector_methods(self):
        """Test the detector's methods with a real instance."""
        # Create a real detector instance
        detector = StdlibDetector()
        detector.initialize()
        # The detector should be initialized
        assert detector._initialized
        # The stdlib modules set should not be empty
        assert detector._stdlib_modules is not None
        assert len(detector._stdlib_modules) > 0
        # Test filtering a set of imports
        imports = {'os', 'sys', 'requests', 'numpy'}
        filtered = detector.filter_stdlib_imports(imports)
        # The standard library modules should be filtered out
        assert 'os' not in filtered
        assert 'sys' not in filtered
        # Third-party modules should remain
        assert 'requests' in filtered
        assert 'numpy' in filtered


if __name__ == '__main__':
    unittest.main()
