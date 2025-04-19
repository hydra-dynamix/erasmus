"""
Standard Library Detection Module.

This module provides functionality to detect whether a given module name
belongs to the Python standard library. It's used to filter out standard
library imports from the list of dependencies that need to be installed.

The module supports multiple detection methods:
1. Using sys.stdlib_module_names (Python 3.10+)
2. Using a built-in list of standard library modules
3. Using the stdlib_list package if available

Usage:
    from stdlib import StdlibDetector, is_stdlib_module, filter_stdlib_imports

    # Check if a module is part of the standard library
    if is_stdlib_module('os'):
        print('os is a standard library module')

    # Filter out standard library modules from a set of imports
    third_party_imports = filter_stdlib_imports({'os', 'sys', 'requests', 'numpy'})
    # Returns {'requests', 'numpy'}
"""

import sys
import importlib.util
import logging
from typing import Set, Dict, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Cache of stdlib modules for the current Python version
_STDLIB_MODULES: Optional[Set[str]] = None

# Additional modules that are part of stdlib but may not be detected automatically
ADDITIONAL_STDLIB = {
    "argparse",
    "ast",
    "asyncio",
    "collections",
    "concurrent",
    "contextlib",
    "copy",
    "dataclasses",
    "datetime",
    "decimal",
    "enum",
    "functools",
    "glob",
    "importlib",
    "inspect",
    "io",
    "itertools",
    "json",
    "logging",
    "math",
    "multiprocessing",
    "operator",
    "os",
    "pathlib",
    "pickle",
    "platform",
    "queue",
    "re",
    "shutil",
    "signal",
    "socket",
    "sqlite3",
    "string",
    "subprocess",
    "sys",
    "tempfile",
    "threading",
    "time",
    "traceback",
    "types",
    "typing",
    "unittest",
    "urllib",
    "uuid",
    "warnings",
    "weakref",
    "xml",
    "zipfile",
}


class StdlibDetector:
    """Class for detecting standard library modules.

    This class provides methods to detect whether a module belongs to the
    Python standard library. It uses multiple detection methods and caches
    the results for better performance.
    """

    def __init__(self):
        """Initialize the StdlibDetector."""
        self._stdlib_modules: Optional[Set[str]] = None
        self.initialize()

    def initialize(self) -> None:
        """Initialize the stdlib module cache."""
        self._stdlib_modules = _get_stdlib_modules()
        logger.info(f"Initialized StdlibDetector with {len(self._stdlib_modules)} modules")

    def is_stdlib_module(self, module_name: str) -> bool:
        """Check if a module is part of the Python standard library.

        Args:
            module_name: Name of the module to check

        Returns:
            True if the module is part of the standard library, False otherwise
        """
        # Get the top-level module name
        top_module = module_name.split(".")[0]

        # Check if it's in our stdlib set
        if self._stdlib_modules and top_module in self._stdlib_modules:
            return True

        # Try to find the module spec
        try:
            spec = importlib.util.find_spec(top_module)
            if spec is None:
                return False

            # If the module is in the standard library directory, it's stdlib
            if spec.origin and Path(spec.origin).is_relative_to(sys.prefix):
                return True
        except (ImportError, AttributeError, ValueError):
            pass

        return False

    def filter_stdlib_imports(self, imports: Set[str]) -> Set[str]:
        """Filter out standard library modules from a set of imports.

        Args:
            imports: A set of module names to filter

        Returns:
            A set containing only the third-party (non-stdlib) module names
        """
        return {imp for imp in imports if not self.is_stdlib_module(imp)}


def _get_stdlib_modules() -> Set[str]:
    """Get a set of all standard library module names for the current Python version.

    This function uses various methods to build a comprehensive list of stdlib modules:
    1. Checks sys.stdlib_module_names if available (Python 3.10+)
    2. Scans the standard library directory
    3. Includes additional known stdlib modules

    Returns:
        Set of standard library module names
    """
    global _STDLIB_MODULES

    if _STDLIB_MODULES is not None:
        return _STDLIB_MODULES

    stdlib_modules = set()

    # Method 1: Use sys.stdlib_module_names if available (Python 3.10+)
    if hasattr(sys, "stdlib_module_names"):
        stdlib_modules.update(sys.stdlib_module_names)

    # Method 2: Scan the standard library directory
    stdlib_dir = Path(sys.prefix) / "Lib"
    if stdlib_dir.exists():
        # Add .py files in stdlib_dir
        stdlib_modules.update(f.stem for f in stdlib_dir.glob("*.py") if f.stem != "__init__")

        # Add directories that are packages
        stdlib_modules.update(
            d.name for d in stdlib_dir.iterdir() if d.is_dir() and (d / "__init__.py").exists()
        )

    # Method 3: Add additional known stdlib modules
    stdlib_modules.update(ADDITIONAL_STDLIB)

    # Cache the result
    _STDLIB_MODULES = stdlib_modules
    return stdlib_modules


def is_stdlib_module(module_name: str) -> bool:
    """Check if a module is part of the Python standard library.

    Args:
        module_name: Name of the module to check

    Returns:
        True if the module is part of the standard library, False otherwise
    """
    # Get the top-level module name
    top_module = module_name.split(".")[0]

    # Check if it's in our stdlib set
    if top_module in _get_stdlib_modules():
        return True

    # Try to find the module spec
    try:
        spec = importlib.util.find_spec(top_module)
        if spec is None:
            return False

        # If the module is in the standard library directory, it's stdlib
        if spec.origin and Path(spec.origin).is_relative_to(sys.prefix):
            return True
    except (ImportError, AttributeError, ValueError):
        pass

    return False


def filter_stdlib_imports(imports: set[str]) -> set[str]:
    """Filter out standard library modules from a set of imports.

    This is a convenience function that uses the singleton StdlibDetector.

    Args:
        imports: A set of module names to filter.

    Returns:
        A set containing only the third-party (non-stdlib) module names.
    """
    return {imp for imp in imports if not is_stdlib_module(imp)}


if __name__ == "__main__":
    # Simple test function to check if a module is in the standard library
    import sys

    if len(sys.argv) > 1:
        for module_name in sys.argv[1:]:
            result = is_stdlib_module(module_name)
            print(f"{module_name}: {'Standard library' if result else 'Third-party'}")
    else:
        print("Usage: python stdlib.py <module_name> [<module_name> ...]")
        print("Example: python stdlib.py os requests numpy")
