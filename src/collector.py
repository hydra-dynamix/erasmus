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
from typing import Optional


# Default patterns to exclude from collection
DEFAULT_EXCLUDE_PATTERNS = [
    # Version control directories
    '.git', '.svn', '.hg', '.bzr',
    # Python cache directories
    '__pycache__', '*.pyc', '*.pyo', '*.pyd',
    # Virtual environments
    '.venv', 'venv', 'env', '.env',
    # Build directories
    'build', 'dist', '*.egg-info',
    # IDE directories
    '.idea', '.vscode', '*.sublime-*',
    # Other common exclusions
    'node_modules', '.DS_Store',
]


def collect_py_files(base_path: str, 
                     exclude_patterns: Optional[list[str]] = None) -> list[str]:
    """
    Recursively collect all Python files in a directory.

    Args:
        base_path: The base directory to start the search from.
        exclude_patterns: List of glob patterns to exclude. If None, uses DEFAULT_EXCLUDE_PATTERNS.

    Returns:
        A list of absolute paths to Python files.

    Raises:
        FileNotFoundError: If the base_path does not exist.
        PermissionError: If there are permission issues accessing files.
    """
    return collect_files_with_extensions(
        base_path=base_path,
        extensions=['.py'],
        exclude_patterns=exclude_patterns
    )


def collect_files_with_extensions(base_path: str,
                                 extensions: list[str],
                                 exclude_patterns: Optional[list[str]] = None) -> list[str]:
    """
    Recursively collect files with specific extensions in a directory.

    Args:
        base_path: The base directory to start the search from.
        extensions: List of file extensions to include (e.g., ['.py', '.pyw']).
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
    
    # Check if the base path is a directory
    if not os.path.isdir(base_path):
        raise NotADirectoryError(f"The path {base_path} is not a directory")
    
    collected_files = []
    
    # Walk through the directory tree
    for root, dirs, files in os.walk(base_path, topdown=True):
        # Filter out directories based on exclude patterns
        # This modifies dirs in-place to avoid walking excluded directories
        dirs[:] = [d for d in dirs if not _should_exclude(d, exclude_patterns)]
        
        # Filter and collect files with the specified extensions
        for file in files:
            if _should_exclude(file, exclude_patterns):
                continue
                
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                collected_files.append(file_path)
    
    return collected_files


def collect_files_with_filter(base_path: str,
                             filter_func: Callable[[str], bool],
                             exclude_patterns: Optional[list[str]] = None) -> list[str]:
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
        dirs[:] = [d for d in dirs if not _should_exclude(d, exclude_patterns)]
        
        # Filter and collect files that pass the filter function
        for file in files:
            if _should_exclude(file, exclude_patterns):
                continue
                
            file_path = os.path.join(root, file)
            if filter_func(file_path):
                collected_files.append(file_path)
    
    return collected_files


def _should_exclude(name: str, exclude_patterns: list[str]) -> bool:
    """
    Check if a file or directory name matches any of the exclude patterns.

    Args:
        name: The file or directory name to check.
        exclude_patterns: List of glob patterns to exclude.

    Returns:
        True if the name matches any of the exclude patterns, False otherwise.
    """
    return any(fnmatch.fnmatch(name, pattern) for pattern in exclude_patterns)


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


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        path = sys.argv[1]
        try:
            py_files = collect_py_files(path)
            print(f"Found {len(py_files)} Python files in {path}:")
            for file in py_files:
                print(f"  {file}")
        except (FileNotFoundError, NotADirectoryError, PermissionError) as e:
            print(f"Error: {e}")
    else:
        print("Usage: python collector.py <directory_path>")
