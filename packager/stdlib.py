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

import importlib.util
import sys
from typing import Optional


class StdlibDetector:
    """Class for detecting standard library modules."""

    def __init__(self):
        """Initialize the StdlibDetector with empty caches."""
        self._stdlib_modules: Optional[set[str]] = None
        self._stdlib_prefixes: list[str] = []
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the set of standard library modules.

        This method populates the _stdlib_modules cache using the best
        available method for the current Python version.
        """
        # Method 1: Use sys.stdlib_module_names (Python 3.10+)
        if hasattr(sys, "stdlib_module_names"):
            self._stdlib_modules = set(sys.stdlib_module_names)
            self._initialized = True
            return

        # Method 2: Try to use stdlib_list package if available
        try:
            import stdlib_list

            version = f"{sys.version_info.major}.{sys.version_info.minor}"
            self._stdlib_modules = set(stdlib_list.stdlib_list(version))
            self._initialized = True
            return
        except ImportError:
            # Continue to fallback method
            pass

        # Method 3: Use a built-in list of common standard library modules
        # This is a fallback method and may not be comprehensive
        self._stdlib_modules = {
            # Basic modules
            "abc",
            "argparse",
            "array",
            "ast",
            "asyncio",
            "base64",
            "binascii",
            "builtins",
            "calendar",
            "cmath",
            "collections",
            "concurrent",
            "configparser",
            "contextlib",
            "copy",
            "csv",
            "ctypes",
            "datetime",
            "decimal",
            "difflib",
            "dis",
            "email",
            "enum",
            "errno",
            "fcntl",
            "filecmp",
            "fnmatch",
            "fractions",
            "ftplib",
            "functools",
            "gc",
            "getopt",
            "getpass",
            "gettext",
            "glob",
            "gzip",
            "hashlib",
            "heapq",
            "hmac",
            "html",
            "http",
            "imaplib",
            "importlib",
            "inspect",
            "io",
            "ipaddress",
            "itertools",
            "json",
            "keyword",
            "linecache",
            "locale",
            "logging",
            "lzma",
            "math",
            "mimetypes",
            "mmap",
            "multiprocessing",
            "netrc",
            "numbers",
            "operator",
            "os",
            "pathlib",
            "pickle",
            "pkgutil",
            "platform",
            "plistlib",
            "poplib",
            "posix",
            "pprint",
            "profile",
            "pstats",
            "pwd",
            "py_compile",
            "pyclbr",
            "queue",
            "random",
            "re",
            "reprlib",
            "resource",
            "runpy",
            "sched",
            "secrets",
            "select",
            "selectors",
            "shelve",
            "shlex",
            "shutil",
            "signal",
            "site",
            "smtplib",
            "socket",
            "socketserver",
            "sqlite3",
            "ssl",
            "stat",
            "statistics",
            "string",
            "struct",
            "subprocess",
            "sys",
            "sysconfig",
            "tarfile",
            "tempfile",
            "textwrap",
            "threading",
            "time",
            "timeit",
            "token",
            "tokenize",
            "trace",
            "traceback",
            "tracemalloc",
            "types",
            "typing",
            "unicodedata",
            "unittest",
            "urllib",
            "uuid",
            "venv",
            "warnings",
            "wave",
            "weakref",
            "webbrowser",
            "winreg",
            "wsgiref",
            "xml",
            "xmlrpc",
            "zipapp",
            "zipfile",
            "zipimport",
            "zlib",
            # Modules that might be confused with third-party packages
            "distutils",
            "setuptools",
            "pip",
            "pkg_resources",
        }

        # Common prefixes for standard library modules
        self._stdlib_prefixes = [
            "collections.",
            "concurrent.",
            "ctypes.",
            "email.",
            "html.",
            "http.",
            "importlib.",
            "logging.",
            "multiprocessing.",
            "os.",
            "unittest.",
            "urllib.",
            "xml.",
            "xmlrpc.",
        ]

        self._initialized = True

    def is_stdlib_module(self, name: str) -> bool:
        """Check if a module name belongs to the Python standard library.

        Args:
            name: The name of the module to check.

        Returns:
            True if the module is part of the standard library, False otherwise.
        """
        # Initialize if not already done
        if not self._initialized:
            self.initialize()

        # Direct match in the standard library modules set
        if name in self._stdlib_modules:
            return True

        # Check if it's a submodule of a standard library module
        for prefix in self._stdlib_prefixes:
            if name.startswith(prefix):
                return True

        # Check if it's importable without installing anything
        # This is a last resort and might not be reliable in all environments
        try:
            spec = importlib.util.find_spec(name)
            if spec is not None and spec.origin is not None:
                # Exclude modules from site-packages or dist-packages
                site_pkgs = ("site-packages", "dist-packages")
                return not any(site_pkg in spec.origin for site_pkg in site_pkgs)
        except (ImportError, AttributeError, ValueError):
            pass

        return False

    def filter_stdlib_imports(self, imports: set[str]) -> set[str]:
        """Filter out standard library modules from a set of imports.

        Args:
            imports: A set of module names to filter.

        Returns:
            A set containing only the third-party (non-stdlib) module names.
        """
        return {imp for imp in imports if not self.is_stdlib_module(imp)}


# Create a singleton instance
_detector = StdlibDetector()
_detector.initialize()


def is_stdlib_module(name: str) -> bool:
    """Check if a module name belongs to the Python standard library.

    This is a convenience function that uses the singleton StdlibDetector.

    Args:
        name: The name of the module to check.

    Returns:
        True if the module is part of the standard library, False otherwise.
    """
    return _detector.is_stdlib_module(name.lower())


def filter_stdlib_imports(imports: set[str]) -> set[str]:
    """Filter out standard library modules from a set of imports.

    This is a convenience function that uses the singleton StdlibDetector.

    Args:
        imports: A set of module names to filter.

    Returns:
        A set containing only the third-party (non-stdlib) module names.
    """
    return _detector.filter_stdlib_imports(imports)


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
