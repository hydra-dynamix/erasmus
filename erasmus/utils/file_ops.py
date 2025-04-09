"""File operation utilities."""
import os
import tempfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def safe_write_file(file_path: Path, content: str) -> None:
    """
    Safely write content to a file using a temporary file to ensure atomic writes.
    
    Args:
        file_path: Path to the target file
        content: Content to write to the file
    """
    # Create parent directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create a temporary file in the same directory
    temp_fd, temp_path = tempfile.mkstemp(dir=str(file_path.parent))
    try:
        with os.fdopen(temp_fd, 'w') as f:
            f.write(content)
        
        # On Windows, we need to remove the target file first
        if os.name == 'nt' and file_path.exists():
            file_path.unlink()
            
        # Rename temporary file to target file (atomic on Unix)
        os.replace(temp_path, file_path)
    except Exception as e:
        # Clean up temp file if something goes wrong
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise e

def safe_read_file(file_path: Path) -> str:
    """
    Safely read content from a file.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        The content of the file as a string
        
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise 