import os
import shutil
from pathlib import Path
from typing import Optional

def get_project_root() -> Path:
    """Get the root directory of the project."""
    return Path.cwd()

def backup_rules_file(file_path: Path) -> None:
    """Create a backup of a rules file if it exists."""
    if file_path.exists():
        backup_path = file_path.parent / f"{file_path.name}.old"
        shutil.copy2(file_path, backup_path)

def cleanup_project() -> None:
    """Remove generated files and create backups of rules files."""
    root = get_project_root()
    
    # Backup rules files if they exist
    rules_file = root / "rules.md"
    global_rules_file = root / "global_rules.md"
    
    backup_rules_file(rules_file)
    backup_rules_file(global_rules_file)
    
    # List of patterns/files to clean up
    cleanup_patterns = [
        "*.pyc",
        "__pycache__",
        ".pytest_cache",
        ".coverage",
        "htmlcov",
        "dist",
        "build",
        "*.egg-info",
    ]
    
    for pattern in cleanup_patterns:
        for path in root.rglob(pattern):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)