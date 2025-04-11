"""File operation utilities."""
import contextlib
import logging
import os
import tempfile
from pathlib import Path

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
        Path(temp_path).replace(file_path)
    except Exception:
        # Clean up temp file if something goes wrong
        with contextlib.suppress(OSError):
            Path(temp_path).unlink()
        raise

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
        with file_path.open() as f:
            return f.read()
    except Exception:
        logger.exception("Error reading file %s", file_path)
        raise
