import os
import sys
from pathlib import Path
from typing import List, Optional


def list_files(directory: str) -> list[str]:
    """List all files in a directory."""
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]


def get_file_size(file_path: str) -> Optional[int]:
    """Get the size of a file in bytes."""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory = sys.argv[1]
        files = list_files(directory)
        for file in files:
            size = get_file_size(os.path.join(directory, file))
            print(f"{file}: {size} bytes")
