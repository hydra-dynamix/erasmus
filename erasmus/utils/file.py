"""
File Utility Functions
==================

This module provides utility functions for safe file operations.
"""

import shutil
from pathlib import Path


def safe_read_file(file_path: str | Path) -> str:
    """
    Safely read a file's contents.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        str: File contents, or empty string if file doesn't exist
    """
    try:
        path = Path(file_path)
        if path.exists():
            return path.read_text()
        return ""
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ""

def safe_write_file(file_path: str | Path, content: str, backup: bool = True) -> bool:
    """
    Safely write content to a file with optional backup.
    
    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        backup: Whether to create a backup before writing
        
    Returns:
        bool: True if write was successful, False otherwise
    """
    try:
        path = Path(file_path)

        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup if requested and file exists
        if backup and path.exists():
            backup_path = path.with_suffix(path.suffix + '.bak')
            shutil.copy2(path, backup_path)

        # Write the new content
        path.write_text(content)
        return True

    except Exception as e:
        print(f"Error writing file {file_path}: {e}")
        return False

def ensure_file_exists(file_path: str | Path, content: str | None = None) -> bool:
    """
    Ensure a file exists, optionally creating it with content.
    
    Args:
        file_path: Path to the file
        content: Optional content to write if file doesn't exist
        
    Returns:
        bool: True if file exists or was created, False otherwise
    """
    try:
        path = Path(file_path)

        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        if not path.exists():
            path.write_text(content or "")
        return True

    except Exception as e:
        print(f"Error ensuring file exists {file_path}: {e}")
        return False

def backup_file(file_path: str | Path, backup_suffix: str = '.bak') -> bool:
    """
    Create a backup of a file.
    
    Args:
        file_path: Path to the file to backup
        backup_suffix: Suffix to use for backup file
        
    Returns:
        bool: True if backup was successful, False otherwise
    """
    try:
        path = Path(file_path)
        if path.exists():
            backup_path = path.with_suffix(path.suffix + backup_suffix)
            shutil.copy2(path, backup_path)
            return True
        return False

    except Exception as e:
        print(f"Error backing up file {file_path}: {e}")
        return False
