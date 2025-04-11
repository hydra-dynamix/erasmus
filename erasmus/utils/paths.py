"""Path management for Erasmus project files."""
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Dict
import os

class FilePaths(BaseModel):
    
    @classmethod
    def set_attribute(cls, name, value):
        if hasattr(cls, name):
            setattr(cls, name, value)
        else:
            raise AttributeError(f"{name} is not a valid attribute")
    
    @classmethod
    def model_dump(cls):
        """Base model_dump method to be overridden by subclasses."""
        return {}

    def __str__(self):
        return str(self.model_dump())
        

class MarkdownPaths(FilePaths):
    _architecture: Path = Field(
        default=Path().cwd() / "architecture.md",
        description="Architecture design document",
        default_factory=Path
    )
    _progress: Path = Field(
        default=Path().cwd() / "progress.md",
        description="Progress tracker for the project",
        default_factory=Path
    )
    _tasks: Path = Field(
        default=Path().cwd() / "tasks.md",
        description="Task tracker for the project",
        default_factory=Path
    )
    
    @property
    def architecture(self):
        return self._architecture
    
    @architecture.setter
    def architecture(self, value):
        self._architecture = value
    
    @property
    def progress(self):
        return self._progress
    
    @progress.setter
    def progress(self, value):
        self._progress = value
    
    @property
    def tasks(self):
        return self._tasks
    
    @tasks.setter
    def tasks(self, value):
        self._tasks = value
        
    def model_dump(self):
        base_dump = super().model_dump()
        return {
            **base_dump,
            "architecture": self._architecture,
            "progress": self._progress,
            "tasks": self._tasks
        }
    

class RulesPaths(FilePaths):
    _cursor: Path = Field(
        default=Path().cwd() / ".cursorrules",
        description="Cursor rules file",
        default_factory=Path
    )
    _cursor_global: Path = Field(
        default=Path().cwd() / "global_rules.md",
        description="Cursor global rules file",
        default_factory=Path
    )
    _windsurf: Path = Field(
        default=Path().cwd() / ".windsurfrules",
        description="Windsurf rules file",
        default_factory=Path
    )
    _windsurf_global: Path = Field(
        default=Path.home() / ".codeium" / "windsurf" / "memories" / "global_rules.md",
        description="Windsurf global rules file",
        default_factory=Path
    )

    @property
    def cursor(self):
        return self._cursor
    
    @cursor.setter
    def cursor(self, value):
        self._cursor = value
    
    @property
    def cursor_global(self):
        return self._cursor_global
    
    @cursor_global.setter
    def cursor_global(self, value):
        self._cursor_global = value
    
    @property
    def windsurf(self):
        return self._windsurf
    
    @windsurf.setter
    def windsurf(self, value):
        self._windsurf = value
    
    @property
    def windsurf_global(self):
        return self._windsurf_global
    
    @windsurf_global.setter
    def windsurf_global(self, value):
        self._windsurf_global = value
        
    def model_dump(self):
        base_dump = super().model_dump()
        return {
            **base_dump,
            "cursor": self._cursor,
            "cursor_global": self._cursor_global,
            "windsurf": self._windsurf,
            "windsurf_global": self._windsurf_global
        }

class ScriptPaths(FilePaths):
    _script: Path = Field(
        default=Path().cwd() / "erasmus.py",
        description="Script file to watch",
        default_factory=Path
    )

    @property
    def script(self):
        return self._script
    
    @script.setter
    def script(self, value):
        self._script = value
        
    def model_dump(self):
        base_dump = super().model_dump()
        return {
            **base_dump,
            "script": self._script
        }

class SetupPaths(FilePaths):
    """Manages paths for project files and watchers."""
    _rules_file: Path = Field(
        default=Path().cwd() / ".cursorrules",
        description="Rules file path",
        default_factory=Path
    )
    _project_root: Path = Field(
        default=Path().cwd(), 
        description="Root of the directory", 
        default_factory=Path
    )
    _markdown_files: MarkdownPaths = Field(
        default_factory=MarkdownPaths,
        description="Markdown file paths"
    )
    _script_files: ScriptPaths = Field(
        default_factory=ScriptPaths,
        description="Script file paths"
    )
          
    @property
    def rules_file(self) -> Path:
        """Get the rules file path based on IDE environment."""
        ide_env = os.getenv("IDE_ENV", "").lower()
        if ide_env.startswith("w"):
            self._rules_file = self._project_root / ".windsurfrules"
        elif ide_env.startswith("c"):
            self._rules_file = self._project_root / ".cursorrules"
        else:
            self._rules_file = self._project_root / ".cursorrules"  # Default
        return self._rules_file
    
    @rules_file.setter
    def rules_file(self, value):
        self._rules_file = value
        
    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        return self._project_root
    
    @project_root.setter
    def project_root(self, value):
        self._project_root = value
    
    @property
    def markdown_files(self):
        return self._markdown_files
    
    @markdown_files.setter
    def markdown_files(self, value):
        self._markdown_files = value
    
    @property
    def script_files(self):
        return self._script_files
    
    @script_files.setter
    def script_files(self, value):
        self._script_files = value

    @property
    def all_watch_paths(self) -> Dict[str, Path]:
        """Get all paths that should be watched."""
        return {
            **self.markdown_files.model_dump(),
            **self.script_files.model_dump()
        }
        
    def model_dump(self):
        return {
            "rules_file": self._rules_file,
            "project_root": self._project_root,
            "markdown_files": self._markdown_files.model_dump(),
            "script_files": self._script_files.model_dump()
        }
    
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
