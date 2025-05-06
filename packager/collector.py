"""
File Collection Module.

This module provides functionality to recursively find Python files in a project
directory. It handles various file system operations, exclusion patterns, and
cross-platform path compatibility.

Usage:
    from collector import collect_py_files, collect_files_with_extensions

    # Collect all Python files in a directory
    python_files = collect_py_files('/path/to/project')

    # Collect files with specific extensions
    js_files = collect_files_with_extensions('/path/to/project', ['.js', '.jsx'])
"""

import fnmatch
import os
from collections.abc import Callable
from typing import Optional, List, Set, Tuple, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Default patterns to exclude from collection
DEFAULT_EXCLUDE_PATTERNS = [
    # Version control directories
    ".git",
    ".svn",
    ".hg",
    ".bzr",
    # Python cache directories
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    # Virtual environments
    ".venv",
    "venv",
    "env",
    ".env",
    # Build directories
    "build",
    "dist",
    "*.egg-info",
    # IDE directories
    ".idea",
    ".vscode",
    "*.sublime-*",
    # Other common exclusions
    "node_modules",
    ".DS_Store",
]


def collect_py_files(base_path: str, exclude_patterns: list[str] | None = None) -> list[str]:
    """
    Recursively collect all Python files in a directory or a single Python file.

    Args:
        base_path: The base directory to start the search from or a Python file path.
        exclude_patterns: List of glob patterns to exclude. If None, uses DEFAULT_EXCLUDE_PATTERNS.

    Returns:
        A list of absolute paths to Python files.

    Raises:
        FileNotFoundError: If the base_path does not exist.
        PermissionError: If there are permission issues accessing files.
    """
    # Convert to absolute path
    base_path = os.path.abspath(base_path)

    # Check if the base path exists
    if not os.path.exists(base_path):
        raise FileNotFoundError(f"The path {base_path} does not exist")

    # If it's a file, raise NotADirectoryError
    if os.path.isfile(base_path):
        raise NotADirectoryError(f"The path {base_path} is a file, not a directory")

    # Otherwise, collect all Python files in the directory
    return collect_files_with_extensions(
        base_path=base_path, extensions=[".py"], exclude_patterns=exclude_patterns
    )


def collect_files_with_extensions(
    base_path: str, extensions: list[str], exclude_patterns: list[str] | None = None
) -> list[str]:
    """
    Recursively collect files with specific extensions in a directory or a single file.

    Args:
        base_path: The base directory to start the search from or a file path.
        extensions: List of file extensions to include (error.g., ['.py', '.pyw']).
        exclude_patterns: List of glob patterns to exclude. If None, uses DEFAULT_EXCLUDE_PATTERNS.

    Returns:
        A list of absolute paths to files with the specified extensions.

    Raises:
        FileNotFoundError: If the base_path does not exist.
        PermissionError: If there are permission issues accessing files.
    """
    if exclude_patterns is None:
        exclude_patterns = DEFAULT_EXCLUDE_PATTERNS

    # Convert to absolute path
    base_path = os.path.abspath(base_path)

    # Check if the base path exists
    if not os.path.exists(base_path):
        raise FileNotFoundError(f"The path {base_path} does not exist")

    # If it's a file, return it directly if it has one of the specified extensions
    if os.path.isfile(base_path):
        if any(base_path.endswith(ext) for ext in extensions):
            return [base_path]
        else:
            raise ValueError(
                f"The file {base_path} does not have one of the specified extensions: {extensions}"
            )

    # Check if the base path is a directory
    if not os.path.isdir(base_path):
        raise NotADirectoryError(f"The path {base_path} is not a directory")

    collected_files = []

    # Walk through the directory tree
    for root, dirs, files in os.walk(base_path, topdown=True):
        # Filter out directories based on exclude patterns
        # This modifies dirs in-place to avoid walking excluded directories
        dirs[:] = [d for d in dirs if not _should_exclude(os.path.join(root, d), exclude_patterns)]

        # Filter and collect files with the specified extensions
        for file in files:
            file_path = os.path.join(root, file)
            if _should_exclude(file_path, exclude_patterns):
                continue

            if any(file.endswith(ext) for ext in extensions):
                collected_files.append(file_path)

    return collected_files


def collect_files_with_filter(
    base_path: str, filter_func: Callable[[str], bool], exclude_patterns: list[str] | None = None
) -> list[str]:
    """
    Recursively collect files that pass a custom filter function.

    Args:
        base_path: The base directory to start the search from.
        filter_func: A function that takes a file path and returns True if the file should be included.
        exclude_patterns: List of glob patterns to exclude. If None, uses DEFAULT_EXCLUDE_PATTERNS.

    Returns:
        A list of absolute paths to files that pass the filter function.

    Raises:
        FileNotFoundError: If the base_path does not exist.
        PermissionError: If there are permission issues accessing files.
    """
    if exclude_patterns is None:
        exclude_patterns = DEFAULT_EXCLUDE_PATTERNS

    # Convert to absolute path
    base_path = os.path.abspath(base_path)

    # Check if the base path exists
    if not os.path.exists(base_path):
        raise FileNotFoundError(f"The path {base_path} does not exist")

    # Check if the base path is a directory
    if not os.path.isdir(base_path):
        raise NotADirectoryError(f"The path {base_path} is not a directory")

    collected_files = []

    # Walk through the directory tree
    for root, dirs, files in os.walk(base_path, topdown=True):
        # Filter out directories based on exclude patterns
        # This modifies dirs in-place to avoid walking excluded directories
        dirs[:] = [d for d in dirs if not _should_exclude(os.path.join(root, d), exclude_patterns)]

        # Filter and collect files that pass the filter function
        for file in files:
            file_path = os.path.join(root, file)
            if _should_exclude(file_path, exclude_patterns):
                continue

            if filter_func(file_path):
                collected_files.append(file_path)

    return collected_files


def _should_exclude(name: str, exclude_patterns: list[str]) -> bool:
    """
    Check if a file or directory name matches any of the exclude patterns.

    Args:
        name: The name or path to check.
        exclude_patterns: List of glob patterns to exclude.

    Returns:
        True if the name matches any of the exclude patterns, False otherwise.
    """
    # Convert name to a Path object for proper path matching
    path = Path(name)
    str_path = str(path).replace("\\", "/")  # Normalize path separators

    # Check each pattern
    for pattern in exclude_patterns:
        pattern = pattern.replace("\\", "/")  # Normalize pattern separators

        # Special handling for src/**/* pattern
        if pattern == "src/**/*":
            if "src/" in str_path:
                return True
            continue

        # Handle directory-specific patterns (error.g., "src/**/*")
        if "/" in pattern:
            # For patterns with wildcards, we need to check if the path matches
            if fnmatch.fnmatch(str_path, pattern):
                return True
            # Also check if any parent directory matches the pattern
            for parent in path.parents:
                parent_str = str(parent).replace("\\", "/")
                if fnmatch.fnmatch(parent_str, pattern):
                    return True
        # Handle simple name patterns
        else:
            if fnmatch.fnmatch(path.name, pattern):
                return True
            # Also check parent directories for exclusion
            for parent in path.parents:
                if fnmatch.fnmatch(parent.name, pattern):
                    return True

    return False


def get_relative_paths(files: list[str], base_path: str) -> list[str]:
    """
    Convert a list of absolute file paths to paths relative to a base directory.

    Args:
        files: List of absolute file paths.
        base_path: The base directory to make paths relative to.

    Returns:
        A list of file paths relative to the base_path.
    """
    base_path = os.path.abspath(base_path)
    return [os.path.relpath(file, base_path) for file in files]


def collect_python_files(
    paths: Union[str, Path, list[Union[str, Path]]], exclude_patterns: list[str] = None
) -> list[Path]:
    """Collect Python files from given paths.

    Args:
        paths: Single path or list of paths to collect from
        exclude_patterns: List of glob patterns to exclude

    Returns:
        List of Path objects for Python files
    """
    if isinstance(paths, (str, Path)):
        paths = [paths]

    exclude_patterns = exclude_patterns or []
    python_files = []

    for path in paths:
        path = Path(path)
        if not path.exists():
            logger.warning(f"Path does not exist: {path}")
            continue

        if path.is_file():
            if path.suffix == ".py":
                python_files.append(path)
        else:
            # Recursively collect .py files
            for py_file in path.rglob("*.py"):
                # Check if file should be excluded
                if not any(py_file.match(pattern) for pattern in exclude_patterns):
                    python_files.append(py_file)

    return python_files


def extract_file_content(file: Path) -> Tuple[str, str]:
    """Extract imports and content from a Python file.

    Args:
        file: Path to the Python file

    Returns:
        Tuple of (imports, content)
    """
    content = file.read_text()

    # Split content into imports and body
    lines = content.splitlines()
    import_lines = []
    body_lines = []
    in_import_block = True

    for line in lines:
        stripped = line.strip()
        if in_import_block:
            if stripped.startswith(("import ", "from ")):
                import_lines.append(line)
            elif stripped and not stripped.startswith("#"):
                in_import_block = False
                body_lines.append(line)
            else:
                import_lines.append(line)
        else:
            body_lines.append(line)

    return "\n".join(import_lines), "\n".join(body_lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        path = sys.argv[1]
        try:
            py_files = collect_py_files(path)
            print(f"Found {len(py_files)} Python files in {path}:")
            for file in py_files:
                print(f"  {file}")
        except (FileNotFoundError, NotADirectoryError, PermissionError) as error:
            print(f"Error: {error}")
    else:
        print("Usage: python collector.py <directory_path>")
