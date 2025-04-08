"""
Context Management System
======================

This module provides classes for managing context files and rules
in the Erasmus project.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Union, Optional, Any

class ContextValidationError(Exception):
    """Raised when context file validation fails."""
    pass

class ContextFileHandler:
    """Handles reading, writing, and validation of context files."""
    
    def __init__(self, workspace_root: Union[str, Path]):
        """Initialize the context file handler.
        
        Args:
            workspace_root: Path to the workspace root directory
        """
        self.workspace_root = Path(workspace_root)
        self.context_dir = self.workspace_root / ".erasmus"
        self.rules_file = self.context_dir / "rules.md"
        self.global_rules_file = self.context_dir / "global_rules.md"
        self.context_file = self.context_dir / "context.json"
        
        # Create context directory if it doesn't exist
        self.context_dir.mkdir(exist_ok=True)
    
    def _parse_markdown_rules(self, content: str) -> Dict[str, Union[List[str], Dict[str, List[str]]]]:
        """Parse markdown content into a rules dictionary.
        
        Args:
            content: Markdown content to parse
            
        Returns:
            Dict containing parsed rules
            
        Raises:
            ContextValidationError: If the content is not valid markdown rules
        """
        if not content.strip():
            raise ContextValidationError("Empty rules content")
        
        rules: Dict[str, Union[List[str], Dict[str, List[str]]]] = {}
        current_section = None
        current_subsection = None
        has_title = False
        has_section = False
        
        try:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Title (#)
                if line.startswith('# '):
                    if has_title:
                        raise ContextValidationError("Multiple titles found")
                    has_title = True
                    continue
                
                # Main section (##)
                elif line.startswith('## '):
                    current_section = line[3:].strip()
                    current_subsection = None
                    rules[current_section] = []
                    has_section = True
                
                # Subsection (###)
                elif line.startswith('### '):
                    if current_section is None:
                        raise ContextValidationError("Subsection without section")
                    current_subsection = line[4:].strip()
                    if isinstance(rules[current_section], list):
                        rules[current_section] = {}
                    rules[current_section][current_subsection] = []  # type: ignore
                
                # List item
                elif line.startswith('- '):
                    if current_section is None:
                        raise ContextValidationError("List item without section")
                    item = line[2:].strip()
                    if current_subsection is None:
                        if isinstance(rules[current_section], dict):
                            raise ContextValidationError("Mixed section types")
                        rules[current_section].append(item)  # type: ignore
                    else:
                        if not isinstance(rules[current_section], dict):
                            raise ContextValidationError("Mixed section types")
                        rules[current_section][current_subsection].append(item)  # type: ignore
                
                # Invalid content
                else:
                    raise ContextValidationError(f"Invalid line format: {line}")
            
            # Validate structure
            if not has_title:
                raise ContextValidationError("Missing title (# heading)")
            if not has_section:
                raise ContextValidationError("No sections found (## headings)")
            if not rules:
                raise ContextValidationError("No rules found")
            
            return rules
            
        except ContextValidationError:
            raise
        except Exception as e:
            raise ContextValidationError(f"Failed to parse rules: {str(e)}")
    
    def read_rules(self) -> Dict[str, Union[List[str], Dict[str, List[str]]]]:
        """Read and parse the project rules file.
        
        Returns:
            Dict containing parsed rules
            
        Raises:
            ContextValidationError: If the rules file is invalid
        """
        try:
            content = self.rules_file.read_text()
            return self._parse_markdown_rules(content)
        except FileNotFoundError:
            return {}
        except Exception as e:
            raise ContextValidationError(f"Failed to read rules file: {str(e)}")
    
    def read_global_rules(self) -> Dict[str, Union[List[str], Dict[str, List[str]]]]:
        """Read and parse the global rules file.
        
        Returns:
            Dict containing parsed global rules
            
        Raises:
            ContextValidationError: If the global rules file is invalid
        """
        try:
            content = self.global_rules_file.read_text()
            return self._parse_markdown_rules(content)
        except FileNotFoundError:
            return {}
        except Exception as e:
            raise ContextValidationError(f"Failed to read global rules file: {str(e)}")
    
    def read_context(self) -> Dict[str, Any]:
        """Read and parse the context file.
        
        Returns:
            Dict containing context configuration
            
        Raises:
            ContextValidationError: If the context file is invalid
        """
        try:
            if not self.context_file.exists():
                return {
                    "project_root": str(self.workspace_root),
                    "active_rules": [],
                    "global_rules": [],
                    "file_patterns": ["*.py", "*.md"],
                    "excluded_paths": ["venv/", "__pycache__/"]
                }
            
            content = self.context_file.read_text()
            context = json.loads(content)
            
            # Validate required fields
            required_fields = ["project_root", "active_rules", "global_rules", 
                             "file_patterns", "excluded_paths"]
            missing_fields = [f for f in required_fields if f not in context]
            if missing_fields:
                raise ContextValidationError(f"Missing required fields: {', '.join(missing_fields)}")
            
            return context
            
        except json.JSONDecodeError as e:
            raise ContextValidationError(f"Invalid JSON in context file: {str(e)}")
        except Exception as e:
            raise ContextValidationError(f"Failed to read context file: {str(e)}")
    
    def update_context(self, new_context: Dict[str, Any], partial: bool = False) -> None:
        """Update the context file.
        
        Args:
            new_context: New context configuration
            partial: If True, only update specified fields
            
        Raises:
            ContextValidationError: If the new context is invalid
        """
        try:
            if partial:
                current_context = self.read_context()
                current_context.update(new_context)
                new_context = current_context
            
            # Validate required fields
            required_fields = ["project_root", "active_rules", "global_rules", 
                             "file_patterns", "excluded_paths"]
            missing_fields = [f for f in required_fields if f not in new_context]
            if missing_fields:
                raise ContextValidationError(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Write the updated context
            self.context_file.write_text(json.dumps(new_context, indent=2))
            
        except Exception as e:
            raise ContextValidationError(f"Failed to update context: {str(e)}")
    
    def backup_rules(self) -> None:
        """Create backups of rules files.
        
        Creates .bak files for both rules.md and global_rules.md if they exist.
        """
        try:
            if self.rules_file.exists():
                shutil.copy2(self.rules_file, self.rules_file.with_suffix('.md.bak'))
            
            if self.global_rules_file.exists():
                shutil.copy2(self.global_rules_file, self.global_rules_file.with_suffix('.md.bak'))
                
        except Exception as e:
            raise ContextValidationError(f"Failed to create backups: {str(e)}")
