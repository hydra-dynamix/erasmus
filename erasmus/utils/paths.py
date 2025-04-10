"""Path management for Erasmus project files."""
from pathlib import Path
from typing import Dict
import os

class SetupPaths:
    """Manages paths for project files and watchers."""
    
    def __init__(self, project_root: Path):
        """Initialize paths relative to project root.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
        self.markdown_files = {
            'architecture': project_root / 'architecture.md',
            'progress': project_root / 'progress.md',
            'tasks': project_root / 'tasks.md'
        }
        self.script_files = {
            'script': project_root / 'erasmus.py'
        }
        
    @property
    def rules_file(self) -> Path:
        """Get the rules file path based on IDE environment."""
        ide_env = os.getenv("IDE_ENV", "").lower()
        if ide_env.startswith("w"):
            return self.project_root / ".windsurfrules"
        elif ide_env.startswith("c"):
            return self.project_root / ".cursorrules"
        return self.project_root / ".cursorrules"  # Default
    
    @property
    def all_watch_paths(self) -> Dict[str, Path]:
        """Get all paths that should be watched."""
        return {**self.markdown_files, **self.script_files}
    
    def validate_paths(self) -> None:
        """Validate that required files exist.
        
        Raises:
            FileNotFoundError: If a required file is missing
        """
        for name, path in self.markdown_files.items():
            if not path.exists():
                raise FileNotFoundError(f"Required file {name} not found at {path}")
        
        for name, path in self.script_files.items():
            if not path.exists():
                raise FileNotFoundError(f"Required file {name} not found at {path}")
