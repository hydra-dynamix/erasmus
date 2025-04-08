"""Context management utilities for Erasmus."""
from pathlib import Path
import json
import shutil
import subprocess
import time
import re
import logging
from typing import Dict, Any, Optional

from rich import console
from openai import OpenAI

from ..git.manager import GitManager

# Configure logging
logger = logging.getLogger(__name__)

# Global variables
PWD = Path(__file__).parent
CLIENT = None
OPENAI_MODEL = None

def get_openai_credentials():
    """Get OpenAI credentials from environment variables."""
    import os
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_MODEL")
    return api_key, base_url, model

def extract_commit_message(message: str) -> str:
    """Extract the first line of a commit message and ensure it's properly formatted."""
    # Get the first line
    first_line = message.split('\n')[0].strip()
    
    # Remove any quotes that might have been added
    first_line = first_line.strip('"\'')
    
    # Truncate if too long
    if len(first_line) > 72:
        first_line = first_line[:69] + "..."
        
    return first_line

def determine_commit_type(diff_output: str) -> str:
    """Determine the commit type based on the diff content."""
    diff_lower = diff_output.lower()
    
    # Define patterns for different commit types
    patterns = {
        'test': ['test', 'spec', '_test.py', 'pytest'],
        'fix': ['fix', 'bug', 'error', 'issue', 'crash', 'problem'],
        'docs': ['docs', 'documentation', 'readme', 'comment'],
        'style': ['style', 'format', 'lint', 'pretty', 'whitespace'],
        'refactor': ['refactor', 'restructure', 'cleanup', 'clean up', 'simplify'],
        'feat': ['feat', 'feature', 'add', 'new', 'implement']
    }
    
    # Check each pattern
    for commit_type, keywords in patterns.items():
        if any(keyword in diff_lower for keyword in keywords):
            return commit_type
            
    # Default to chore
    return 'chore'

console = console.Console()

def read_file(path: Path) -> str:
    """Read a file and return its contents."""
    try:
        return path.read_text()
    except Exception as e:
        console.print(f"Error reading {path}: {e}", style="red")
        return ""

def write_file(path: Path, content: str, backup: bool = False) -> bool:
    """Write content to a file, optionally creating a backup."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create backup if requested and file exists
        if backup and path.exists():
            backup_path = path.parent / f"{path.name}.old"
            shutil.copy2(path, backup_path)
            console.print(f"Created backup at {backup_path}")
            
        path.write_text(content)
        return True
    except Exception as e:
        console.print(f"Error writing to {path}: {e}", style="red")
        return False

def update_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Update the context with current file contents."""
    rules_path = Path(".cursorrules")
    global_rules_path = Path("global_rules.md")
    
    # Add architecture if available
    arch_path = Path("ARCHITECTURE.md")
    if arch_path.exists():
        context["architecture"] = read_file(arch_path)
    
    # Add progress if available
    progress_path = Path("PROGRESS.md")
    if progress_path.exists():
        context["progress"] = read_file(progress_path)
    
    # Add tasks if available
    tasks_path = Path("TASKS.md")
    if tasks_path.exists():
        context["tasks"] = read_file(tasks_path)
    
    # Write updated context with backup
    write_file(rules_path, json.dumps(context, indent=2), backup=True)
    if global_rules_path.exists():
        write_file(global_rules_path, json.dumps(context, indent=2), backup=True)
    return context

def setup_project() -> None:
    """Set up a new project with necessary files."""
    # Create required files
    files = {
        "ARCHITECTURE.md": "# Project Architecture\n\nDescribe your project architecture here.",
        "PROGRESS.md": "# Development Progress\n\nTrack your development progress here.",
        "TASKS.md": "# Project Tasks\n\nList your project tasks here.",
        ".env.example": "IDE_ENV=\nOPENAI_API_KEY=\nOPENAI_BASE_URL=\nOPENAI_MODEL=",
        ".gitignore": ".env\n__pycache__/\n*.pyc\n.pytest_cache/\n",
    }
    
    for filename, content in files.items():
        path = Path(filename)
        if not path.exists():
            write_file(path, content)
            console.print(f"Created {filename}")
    
    # Initialize context
    update_context({})
    console.print("Project setup complete!")

def update_specific_file(file_type: str, content: str) -> None:
    """Update a specific project file."""
    file_map = {
        "architecture": "ARCHITECTURE.md",
        "progress": "PROGRESS.md",
        "tasks": "TASKS.md",
        "context": ".cursorrules"
    }
    
    if file_type.lower() not in file_map:
        console.print(f"Invalid file type: {file_type}", style="red")
        return
    
    path = Path(file_map[file_type.lower()])
    if write_file(path, content, backup=True):
        console.print(f"Updated {path}")
        if file_type != "context":
            update_context({})

def cleanup_project() -> None:
    """Remove all generated files and restore backups if available."""
    files_to_remove = [
        "ARCHITECTURE.md",
        "PROGRESS.md",
        "TASKS.md",
        ".cursorrules",
        "global_rules.md",
    ]
    
    for filename in files_to_remove:
        path = Path(filename)
        backup_path = path.parent / f"{path.name}.old"
        
        # Remove the current file
        if path.exists():
            try:
                path.unlink()
                console.print(f"Removed {path}")
            except Exception as e:
                console.print(f"Error removing {path}: {e}", style="red")
        
        # Restore backup if it exists
        if backup_path.exists():
            try:
                shutil.move(backup_path, path)
                console.print(f"Restored backup for {path}")
            except Exception as e:
                console.print(f"Error restoring backup for {path}: {e}", style="red")

def check_creds():
    """Check if OpenAI credentials are valid for API calls."""
    api_key, base_url, model = get_openai_credentials()
    
    # Skip API call if using default key or OpenAI base URL
    if api_key == "sk-1234" or "api.openai.com" in base_url.lower():
        return False
    return True

def make_atomic_commit():
    """Makes an atomic commit with AI-generated commit message or falls back to diff-based message."""
    # Initialize GitManager with current directory
    git_manager = GitManager(PWD)
    
    # Stage all changes
    if not git_manager.stage_all_changes():
        logger.warning("No changes to commit or staging failed.")
        return False
    
    try:
        # Get the diff output
        diff_output = subprocess.check_output(
            ["git", "diff", "--staged"], 
            cwd=PWD, 
            text=True,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'  # Replace undecodable bytes
        )
        
        # Truncate diff if it's too long
        max_diff_length = 4000
        if len(diff_output) > max_diff_length:
            diff_output = diff_output[:max_diff_length] + "... (diff truncated)"
        
        # Sanitize diff output
        diff_output = ''.join(char for char in diff_output if ord(char) < 128)
        
        # Determine commit type programmatically
        commit_type = determine_commit_type(diff_output)
        
        # If we can use OpenAI, generate a message
        if check_creds() and CLIENT is not None:
            prompt = f"""Generate a concise, descriptive commit message for the following git diff.
The commit type has been determined to be '{commit_type}'.

Diff:
{diff_output}

Guidelines:
- Use the format: {commit_type}: description
- Keep message under 72 characters
- Be specific about the changes
- Prefer imperative mood"""
            
            try:
                response = CLIENT.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a git commit message generator."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=100
                )
                
                # Sanitize commit message
                raw_message = response.choices[0].message.content
                commit_message = ''.join(char for char in raw_message if ord(char) < 128)
                
                # Ensure commit message starts with the determined type
                if not commit_message.startswith(f"{commit_type}:"):
                    commit_message = f"{commit_type}: {commit_message}"
                
                commit_message = extract_commit_message(commit_message)
            except Exception as e:
                logger.warning(f"Failed to generate commit message via API: {e}")
                commit_message = None
        else:
            commit_message = None
            
        # If we don't have a commit message, generate one from the diff
        if not commit_message:
            # Get the first line of the diff that shows a file change
            diff_lines = diff_output.split('\n')
            file_change = next((line for line in diff_lines if line.startswith('diff --git')), '')
            if file_change:
                # Extract the file name from the diff line
                file_name = file_change.split(' b/')[-1]
            else:
                file_name = "project files"
            
            # Create a simple commit message based on the type and changed files
            commit_message = f"{commit_type}: Update {file_name}"
        
        # Validate commit message
        is_valid, validation_message = git_manager.validate_commit_message(commit_message)
        
        if not is_valid:
            logger.warning(f"Generated commit message invalid: {validation_message}")
            commit_message = f"{commit_type}: Update project files ({time.strftime('%Y-%m-%d')})"
        
        # Commit changes
        if git_manager.commit_changes(commit_message):
            logger.info(f"Committed changes: {commit_message}")
            return True
        else:
            logger.error("Commit failed")
            return False
    
    except Exception as e:
        logger.error(f"Error in atomic commit: {e}")
        return False 