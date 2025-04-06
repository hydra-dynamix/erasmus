#!/usr/bin/uv run -S 
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "openai",
#     "python-dotenv",
#     "rich",
#     "watchdog",
# ]
# ///

import os
import json
import time
import argparse
import subprocess
import re
import sys
from pathlib import Path
from rich import console
from rich.logging import RichHandler
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from threading import Thread
from openai import OpenAI
from dotenv import load_dotenv
from getpass import getpass
import logging
from typing import Optional, List, Dict, Tuple

# === Task Tracking ===
class TaskStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    NOT_STARTED = "not_started"

class Task:
    def __init__(self, id: str, description: str):
        self.id = id
        self.description = description
        self.status = TaskStatus.NOT_STARTED
        self.created_at = time.time()
        self.updated_at = time.time()
        self.completion_time = None
        self.notes = []
        
    def to_dict(self) -> dict:
        """Convert task to dictionary"""
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completion_time": self.completion_time,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        """Create a task from dictionary"""
        task = cls(data["id"], data["description"])
        task.status = data["status"]
        task.created_at = data["created_at"]
        task.updated_at = data["updated_at"]
        task.completion_time = data["completion_time"]
        task.notes = data["notes"]
        return task

class TaskManager:
    def __init__(self, tasks: dict = None):
        self.tasks = {}
        if tasks:
            self.tasks = {
                task_id: Task.from_dict(task_data) if isinstance(task_data, dict) else task_data
                for task_id, task_data in tasks.items()
            }
        
    def add_task(self, description: str) -> Task:
        """Add a new task"""
        task_id = str(len(self.tasks) + 1)
        task = Task(task_id, description)
        self.tasks[task_id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.tasks.get(task_id)
    
    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        """List all tasks, optionally filtered by status"""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """Update a task's status"""
        if task := self.get_task(task_id):
            task.status = status
    
    def add_note_to_task(self, task_id: str, note: str) -> None:
        """Add a note to a task"""
        if task := self.get_task(task_id):
            task.notes.append(note)
    
    @classmethod
    def from_dict(cls, data):
        """Create a TaskManager from a dictionary"""
        manager = cls()
        if isinstance(data, dict):
            manager.tasks = {
                task_id: Task.from_dict(task_data)
                for task_id, task_data in data.items()
            }
        return manager

def is_valid_url(url: str) -> bool:
    """Basic URL validation using regex."""
    logger.debug(f"Validating URL: {url}")
    https_pattern = re.match(r'^https?://', url)
    logger.debug(f"https_pattern: {https_pattern}")
    http_pattern = re.match(r'^http?://', url)
    logger.debug(f"http_pattern: {http_pattern}")
    return https_pattern or http_pattern

# === OpenAI Configuration ===


def is_valid_url(url: str) -> bool:
    """Basic URL validation using regex."""
    # Accept localhost URLs and standard http/https URLs
    if not url:
        return False
    
    # Check for localhost or 127.0.0.1
    localhost_pattern = re.match(r'^https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(?:/.*)?$', url)
    if localhost_pattern:
        return True
        
    # Check for standard http/https URLs
    standard_pattern = re.match(r'^https?://[\w\.-]+(?::\d+)?(?:/.*)?$', url)
    return bool(standard_pattern)

def detect_ide_environment() -> str:
    """
    Detect the current IDE environment.
    
    Returns:
        str: Detected IDE environment ('WINDSURF', 'CURSOR', or '')
    """
    # Check environment variable first
    ide_env = os.getenv('IDE_ENV', '').upper()
    if ide_env:
        return 'WINDSURF' if ide_env.startswith('W') else 'CURSOR'
    
    # Try to detect based on current working directory or known IDE paths
    cwd = Path.cwd()
    
    # Windsurf-specific detection
    windsurf_markers = [
        Path.home() / '.codeium' / 'windsurf',
        cwd / '.windsurfrules'
    ]
    
    # Cursor-specific detection
    cursor_markers = [
        cwd / '.cursorrules',
        Path.home() / '.cursor'
    ]
    
    # Check Windsurf markers
    for marker in windsurf_markers:
        if marker.exists():
            return 'WINDSURF'
    
    # Check Cursor markers
    for marker in cursor_markers:
        if marker.exists():
            return 'CURSOR'
    
    # Default fallback
    return 'WINDSURF'


def prompt_openai_credentials(env_path=".env"):
    """Prompt user for OpenAI credentials and save to .env"""
    api_key = getpass("Enter your OPENAI_API_KEY (input hidden): ")

    base_url = input("Enter your OPENAI_BASE_URL (default: https://api.openai.com/v1): ").strip()
    if not is_valid_url(base_url):
        print("Invalid URL or empty. Defaulting to https://api.openai.com/v1")
        base_url = "https://api.openai.com/v1"

    model = input("Enter your OPENAI_MODEL (default: gpt-4o): ").strip()
    if not model:
        model = "gpt-4o"
        
    # Detect IDE environment and save it to the .env file
    ide_env = detect_ide_environment()
    
    env_content = (
        f"OPENAI_API_KEY={api_key}\n"
        f"OPENAI_BASE_URL={base_url}\n"
        f"OPENAI_MODEL={model}\n"
        f"IDE_ENV={ide_env}\n"
    )

    Path(env_path).write_text(env_content)
    print(f"✅ OpenAI credentials saved to {env_path}")

# === Configuration and Setup ===
load_dotenv()

# Configure rich console and logging
console = console.Console()
logging_handler = RichHandler(
    console=console,
    show_time=True,
    show_path=False,
    rich_tracebacks=True,
    tracebacks_show_locals=True
)

# Set up logging configuration
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(message)s",
    datefmt="[%X]",
    handlers=[logging_handler]
)

# Create logger instance
logger = logging.getLogger("context_watcher")

# Add file handler for persistent logging
try:
    file_handler = logging.FileHandler("context_watcher.log")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
except Exception as e:
    logger.warning(f"Could not set up file logging: {e}")

def get_openai_credentials():
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    model = os.environ.get("OPENAI_MODEL")
    return api_key, base_url, model

# --- OpenAI Client Initialization ---
def init_openai_client():
    """Initialize and return OpenAI client configuration"""
    try:
        api_key, base_url, model = get_openai_credentials()
        if not api_key or not is_valid_url(base_url) or not model:
            logger.warning("Missing OpenAI credentials. Prompting for input...")
            prompt_openai_credentials()
            api_key, base_url, model = get_openai_credentials()
            if not api_key or not model or not base_url:
                logger.error("Failed to initialize OpenAI client: missing credentials")
                return None, None
        
        client = OpenAI(api_key=api_key, base_url=base_url)
        return client, model
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return None, None

# Global variables
CLIENT, OPENAI_MODEL = init_openai_client()
PWD = Path(__file__).parent

# === Argument Parsing ===
def parse_arguments():
    parser = argparse.ArgumentParser(description="Update script for project")
    parser.add_argument("--watch", action="store_true", help="Enable file watching")
    parser.add_argument("--update", choices=["architecture", "progress", "tasks", "context"], 
                      help="File to update")
    parser.add_argument("--update-value", help="New value to write to the specified file")
    parser.add_argument("--setup", choices=["cursor", "windsurf"], help="Setup project", default="cursor")
    parser.add_argument("--type", choices=["cursor", "windsurf"], help="Project type", default="cursor")
    
    # Task management arguments
    task_group = parser.add_argument_group("Task Management")
    task_group.add_argument("--task-action", choices=["add", "update", "note", "list", "get"],
                           help="Task management action")
    task_group.add_argument("--task-id", help="Task ID for update/note/get actions")
    task_group.add_argument("--task-description", help="Task description for add action")
    task_group.add_argument("--task-status", choices=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS, 
                                                     TaskStatus.COMPLETED, TaskStatus.BLOCKED],
                           help="Task status for update action")
    task_group.add_argument("--task-note", help="Note content for note action")
    
    # Git management arguments
    git_group = parser.add_argument_group("Git Management")
    git_group.add_argument("--git-repo", help="Path to git repository")
    git_group.add_argument("--git-action", choices=["status", "branch", "commit", "push", "pull"],
                          help="Git action to perform")
    git_group.add_argument("--commit-message", help="Commit message for git commit action")
    git_group.add_argument("--branch-name", help="Branch name for git branch action")
    
    return parser.parse_args()

# Global rules content for project setup
GLOBAL_RULES = """
# 🧠 Lead Developer – Prompt Context

## 🎯 OBJECTIVE

You are a **Lead Developer** working alongside a human project owner. Your role is to implement high-quality code based on **requirements** and **architecture** documentation, following best practices:

- Use strong typing and inline documentation.
- Prioritize clarity and production-readiness over unnecessary abstraction.
- Optimize thoughtfully, without sacrificing maintainability.
- Avoid sloppy or undocumented implementations.

You are encouraged to **critically evaluate designs** and improve them where appropriate. When in doubt, **ask questions** — clarity is more valuable than assumptions.

---

## 🛠️ TOOLS

You will be given access to various development tools. Use them as appropriate. Additional **MCP server tools** may be introduced later, with usage instructions appended here.

---

## 📚 DOCUMENTATION

Your workspace root contains three key documents:

- **ARCHITECTURE.md**  
  Primary source of truth. Contains all major components and their requirements.  
  → If missing, ask the user for requirements and generate this document.

- **PROGRESS.md**  
  Tracks major components and organizes them into a development schedule.  
  → If missing, generate from `ARCHITECTURE.md`.

- **TASKS.md**  
  Contains action-oriented tasks per component, small enough to develop and test independently.  
  → If missing, select the next component from `PROGRESS.md` and break it into tasks.

---

## 🔁 WORKFLOW

```mermaid
flowchart TD
    Start([Start])
    CheckArchitecture{ARCHITECTURE exists?}
    AskRequirements["Ask user for requirements"]
    CheckProgress{PROGRESS exists?}
    BreakDownArch["Break ARCHITECTURE into major components"]
    DevSchedule["Organize components into a dev schedule"]
    CheckTasks{TASKS exist?}
    CreateTasks["Break next component into individual tasks"]
    ReviewTasks["Review TASKS"]
    DevTask["Develop a task"]
    TestTask["Test the task until it passes"]
    UpdateTasks["Update TASKS"]
    IsProgressComplete{All PROGRESS completed?}
    LoopBack["Loop"]
    Done([✅ Success])

    Start --> CheckArchitecture
    CheckArchitecture -- Yes --> CheckProgress
    CheckArchitecture -- No --> AskRequirements --> CheckProgress
    CheckProgress -- Yes --> DevSchedule
    CheckProgress -- No --> BreakDownArch --> DevSchedule
    DevSchedule --> CheckTasks
    CheckTasks -- No --> CreateTasks --> ReviewTasks
    CheckTasks -- Yes --> ReviewTasks
    ReviewTasks --> DevTask --> TestTask --> UpdateTasks --> IsProgressComplete
    IsProgressComplete -- No --> LoopBack --> CheckTasks
    IsProgressComplete -- Yes --> Done
```

---

## 🧩 CORE PRINCIPLES

1. **Assume limited context**  
   When unsure, preserve existing functionality and avoid destructive edits.

2. **Improve the codebase**  
   Enhance clarity, performance, and structure — but incrementally, not at the cost of stability.

3. **Adopt best practices**  
   Use typing, structure, and meaningful naming. Write clear, testable, and maintainable code.

4. **Test driven development**
  Use tests to validate code generations. A component is not complete with out accompanying tests. 

4. **Ask questions**  
   If anything is unclear, *ask*. Thoughtful questions lead to better outcomes.

## 🗃️ MEMORY MANAGEMENT

### Browser IDE Memory Rules
1. **Global Context Only**
   - Only store information that is globally required regardless of project
   - Examples: coding standards, common patterns, general preferences
   - Do NOT store project-specific implementation details

2. **Memory Types**
   - User Preferences: coding style, documentation format, testing approaches
   - Common Patterns: reusable design patterns, best practices
   - Tool Usage: common tool configurations and usage patterns
   - Error Handling: standard error handling approaches

3. **Memory Updates**
   - Only update when encountering genuinely new global patterns
   - Do not duplicate project-specific implementations
   - Focus on patterns that apply across multiple projects

4. **Project-Specific Information**
   - Use ARCHITECTURE.md for project structure
   - Use PROGRESS.md for development tracking
   - Use TASKS.md for granular task management
   - Use local documentation for project-specific patterns

---

## KNOWN ISSUES

### Command Execution

Your shell command execution output is running into issues with the markdown interpreter and command interpreter when running multiple test cases in a single command. The issue specifically occurs when trying to run multiple space-separated test names in a single `cargo test` command, as the interpreter mistakes it for XML-like syntax.

**PROBLEMATIC COMMAND** (causes truncation/error):
```xml
  <function_calls>
    <invoke name="run_terminal_cmd">
      <parameter name="command">cargo test test_task_cancellation_basic test_task_cancellation_with_cleanup</parameter>
      <parameter name="explanation">Run multiple tests</parameter>
      <parameter name="is_background">false</parameter>
    </invoke>
  </function_calls>
```

WORKING COMMAND FORMAT:
```xml
  <function_calls>
    <invoke name="run_terminal_cmd">
      <parameter name="command">cargo test test_task_cancellation_basic</parameter>
      <parameter name="explanation">Run single test</parameter>
      <parameter name="is_background">false</parameter>
    </invoke>
  </function_calls>
``` 

To avoid this issue:
1. Run one test case per command
2. If multiple tests need to be run:
   - Either run them in separate sequential commands
   - Or use a pattern match (e.g., `cargo test test_task_executor_` to run all executor tests)
3. Never combine multiple test names with spaces in a single command
4. Keep test commands simple and avoid additional flags when possible
5. If you need flags like `--nocapture`, add them in a separate command
6. Directory changes should be made in separate commands before running tests

Example of correct approach for multiple tests:
```xml
# Run first test
<function_calls>
<invoke name="run_terminal_cmd">
<parameter name="command">cargo test test_task_cancellation_basic</parameter>
<parameter name="explanation">Run first test</parameter>
<parameter name="is_background">false</parameter>
</invoke>
</function_calls>

# Run second test
<function_calls>
<invoke name="run_terminal_cmd">
<parameter name="command">cargo test test_task_cancellation_with_cleanup</parameter>
<parameter name="explanation">Run second test</parameter>
<parameter name="is_background">false</parameter>
</invoke>
</function_calls>
```

This refinement:
1. Clearly identifies the specific trigger (multiple space-separated test names)
2. Shows exactly what causes the XML-like interpretation
3. Provides concrete examples of both problematic and working formats
4. Gives specific solutions and alternatives
5. Includes a practical example of how to run multiple tests correctly


DO NOT `cd` BEFORE A COMMAND
Use your context to track your folder location. Chaining commands is causing an issue with your xml parser

"""


ARGS = parse_arguments()
KEY_NAME = "WINDSURF" if ARGS.setup and ARGS.setup.startswith("w") or ARGS.type and ARGS.type.startswith("w") else "CURSOR"

# === File Paths Configuration ===


def get_rules_file_path(context_type='global') -> Path:
    """
    Determine the appropriate rules file path based on IDE environment.
    
    Args:
        context_type (str): Type of rules file, either 'global' or 'context'
    
    Returns:
        Path: Resolved path to the appropriate rules file
    """
    # Detect IDE environment
    ide_env = detect_ide_environment()
    
    # Mapping for rules file paths using Path for robust resolution
    rules_paths = {
        'WINDSURF': {
            'global': Path.home() / '.codeium' / 'windsurf' / 'memories' / 'global_rules.md',
            'context': Path.cwd() / '.windsurfrules'
        },
        'CURSOR': {
            'global': Path.cwd() / 'global_rules.md',  # User must manually set in Cursor settings
            'context': Path.cwd() / '.cursorrules'
        }
    }
    
    # Get the appropriate path and resolve it
    path = rules_paths[ide_env].get(context_type, Path.cwd() / '.windsurfrules')
    
    # Ensure the directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Return the fully resolved absolute path
    return path.resolve()

def save_global_rules(rules_content):
    """
    Save global rules to the appropriate location based on IDE environment.
    
    Args:
        rules_content (str): Content of the global rules
    """
    global_rules_path = get_rules_file_path('global')
    
    # Special handling for Cursor
    if detect_ide_environment() == 'CURSOR':
        logger.warning(
            "Global rules must be manually saved in Cursor settings. "
            "Please copy the following content to your global rules:"
        )
        print(rules_content)
        return
    
    try:
        with open(global_rules_path, 'w') as f:
            f.write(rules_content)
        logger.info(f"Global rules saved to {global_rules_path}")
    except Exception as e:
        logger.error(f"Failed to save global rules: {e}")

def save_context_rules(context_content):
    """
    Save context-specific rules to the appropriate location.
    
    Args:
        context_content (str): Content of the context rules
    """
    context_rules_path = get_rules_file_path('context')
    
    try:
        with open(context_rules_path, 'w') as f:
            f.write(context_content)
        logger.info(f"Context rules saved to {context_rules_path}")
    except Exception as e:
        logger.error(f"Failed to save context rules: {e}")

# Update global variables to use resolved paths
GLOBAL_RULES_PATH = get_rules_file_path('global')
CONTEXT_RULES_PATH = get_rules_file_path('context')

# === Project Setup ===
def setup_project():
    """Setup the project with necessary files"""
    
    # Create all required files
    for file in [GLOBAL_RULES_PATH, CONTEXT_RULES_PATH]:
        ensure_file_exists(file)
    
    # Write global rules to global_rules.md
    if not safe_read_file(GLOBAL_RULES_PATH):
        save_global_rules(GLOBAL_RULES)
        logger.info(f"Created global rules at {GLOBAL_RULES_PATH}")
        logger.info("Please add the contents of global_rules.md to your IDE's global rules section")
    
    # Initialize cursor rules file if empty
    if not safe_read_file(CONTEXT_RULES_PATH):
        # Initialize with current architecture, progress and tasks
        context = {
            "architecture": safe_read_file(ARCHITECTURE_PATH),
            "progress": safe_read_file(PROGRESS_PATH),
            "tasks": safe_read_file(TASKS_PATH),
        }
        update_context(context)
    
    # Ensure context file exists but don't overwrite it
    ensure_file_exists(CONTEXT_RULES_PATH)
    
    # Ensure IDE_ENV is set in .env file
    env_path = Path(".env")
    if env_path.exists():
        env_content = env_path.read_text()
        if "IDE_ENV=" not in env_content:
            # Append IDE_ENV to existing .env file
            ide_env = detect_ide_environment()
            with open(env_path, "a") as f:
                f.write(f"\nIDE_ENV={ide_env}\n")
            logger.info(f"Added IDE_ENV={ide_env} to .env file")

    # Ensure the git repo is initialized
    subprocess.run(["git", "init"], check=True)

def update_context(context):
    """Update the cursor rules file with current context"""
    content = {}
    
    # Add architecture if available
    if context.get("architecture"):
        content["architecture"] = context["architecture"]
    else:
        if ARCHITECTURE_PATH.exists():
            content["architecture"] = safe_read_file(ARCHITECTURE_PATH)
        else:
            content["architecture"] = ""
    
    # Add progress if available
    if context.get("progress"):
        content["progress"] = context["progress"]
    else:
        if PROGRESS_PATH.exists():
            content["progress"] = safe_read_file(PROGRESS_PATH)
        else:
            content["progress"] = ""
    
    # Add tasks section
    if context.get("tasks"):
        content["tasks"] = context["tasks"]
    else:
        if TASKS_PATH.exists():
            content["tasks"] = safe_read_file(TASKS_PATH)
        else:
            content["tasks"] = ""
            
    # Write to context file
    safe_write_file(CONTEXT_RULES_PATH, json.dumps(content, indent=2))
    make_atomic_commit()
    
    return content


def update_specific_file(file_type, content):
    """Update a specific file with the given content"""
    file_type = file_type.upper()
    
    if file_type == "CONTEXT":
        # Special case to update entire context
        update_context({})
    elif file_type in SETUP_FILES:
        # Update specific setup file
        file_path = SETUP_FILES[file_type]
        if safe_write_file(file_path, content):
            update_context()
            make_atomic_commit()
    else:
        logger.error(f"Invalid file type: {file_type}")

# === Git Operations ===
class GitManager:
    """Lightweight Git repository management."""
    
    def __init__(self, repo_path: str | Path):
        """Initialize GitManager with repository path."""
        self.repo_path = Path(repo_path).resolve()
        if not self._is_git_repo():
            self._init_git_repo()
            
    def _is_git_repo(self) -> bool:
        """Check if the path is a git repository."""
        try:
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _init_git_repo(self):
        """Initialize a new git repository if one doesn't exist."""
        try:
            subprocess.run(
                ["git", "init"],
                cwd=self.repo_path,
                check=True
            )
            # Configure default user
            subprocess.run(
                ["git", "config", "user.name", "Context Watcher"],
                cwd=self.repo_path,
                check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "context.watcher@local"],
                cwd=self.repo_path,
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to initialize git repository: {e}")
            
    def _run_git_command(self, command: List[str]) -> Tuple[str, str]:
        """Run a git command and return stdout and stderr."""
        try:
            result = subprocess.run(
                ["git"] + command,
                cwd=self.repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return result.stdout.strip(), result.stderr.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e}")
            return "", e.stderr.strip()
    
    def stage_all_changes(self) -> bool:
        """Stage all changes in the repository."""
        try:
            self._run_git_command(["add", "-A"])
            return True
        except:
            return False
    
    def commit_changes(self, message: str) -> bool:
        """Commit staged changes with a given message."""
        try:
            self._run_git_command(["commit", "-m", message])
            return True
        except:
            return False
    
    def validate_commit_message(self, message: str) -> Tuple[bool, str]:
        """Validate a commit message against conventions."""
        if not message:
            return False, "Commit message cannot be empty"
        
        # Check length
        if len(message) > 72:
            return False, "Commit message is too long (max 72 characters)"
        
        # Check format (conventional commits)
        conventional_types = {"feat", "fix", "docs", "style", "refactor", "test", "chore"}
        first_line = message.split("\n")[0]
        
        if ":" in first_line:
            type_ = first_line.split(":")[0]
            if type_ not in conventional_types:
                return False, f"Invalid commit type. Must be one of: {', '.join(conventional_types)}"
        
        return True, "Commit message is valid"

def determine_commit_type(diff_output: str) -> str:
    """
    Programmatically determine the most appropriate commit type based on diff content.
    
    Conventional commit types:
    - feat: new feature
    - fix: bug fix
    - docs: documentation changes
    - style: formatting, missing semi colons, etc
    - refactor: code restructuring without changing functionality
    - test: adding or modifying tests
    - chore: maintenance tasks, updates to build process, etc
    """
    # Convert diff to lowercase for case-insensitive matching
    diff_lower = diff_output.lower()
    
    # Prioritize specific patterns
    if 'test' in diff_lower or 'pytest' in diff_lower or '_test.py' in diff_lower:
        return 'test'
    
    if 'fix' in diff_lower or 'bug' in diff_lower or 'error' in diff_lower:
        return 'fix'
    
    if 'docs' in diff_lower or 'readme' in diff_lower or 'documentation' in diff_lower:
        return 'docs'
    
    if 'style' in diff_lower or 'format' in diff_lower or 'lint' in diff_lower:
        return 'style'
    
    if 'refactor' in diff_lower or 'restructure' in diff_lower:
        return 'refactor'
    
    # Check for new feature indicators
    if 'def ' in diff_lower or 'class ' in diff_lower or 'new ' in diff_lower:
        return 'feat'
    
    # Default to chore for miscellaneous changes
    return 'chore'

def make_atomic_commit():
    """Makes an atomic commit with AI-generated commit message."""
    # Initialize GitManager with current directory
    git_manager = GitManager(PWD)
    
    # Stage all changes
    if not git_manager.stage_all_changes():
        logger.warning("No changes to commit or staging failed.")
        return False
    
    # Generate commit message using OpenAI
    try:
        # Use universal newlines and explicit encoding to handle cross-platform diffs
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
        
        # Sanitize diff output to remove potentially problematic characters
        diff_output = ''.join(char for char in diff_output if ord(char) < 128)
        
        # Determine commit type programmatically
        commit_type = determine_commit_type(diff_output)
        
        prompt = f"""Generate a concise, descriptive commit message for the following git diff.
The commit type has been determined to be '{commit_type}'.

Diff:
{diff_output}

Guidelines:
- Use the format: {commit_type}: description
- Keep message under 72 characters
- Be specific about the changes
- Prefer imperative mood"""
        
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

def extract_commit_message(response: str) -> str:
    """
    Extract commit message from AI response, handling markdown blocks and ensuring conciseness.
    
    Args:
        response: Raw response from AI
    
    Returns:
        Extracted commit message, trimmed to 72 characters
    """
    # Remove leading/trailing whitespace
    response = response.strip()
    
    # Extract from markdown code block
    code_block_match = re.search(r'```(?:markdown|commit)?(.+?)```', response, re.DOTALL)
    if code_block_match:
        response = code_block_match.group(1).strip()
    
    # Extract from markdown inline code
    inline_code_match = re.search(r'`(.+?)`', response)
    if inline_code_match:
        response = inline_code_match.group(1).strip()
    
    # Remove any leading type if already present
    type_match = re.match(r'^(feat|fix|docs|style|refactor|test|chore):\s*', response, re.IGNORECASE)
    if type_match:
        response = response[type_match.end():]
    
    # Trim to 72 characters, respecting word boundaries
    if len(response) > 72:
        response = response[:72].rsplit(' ', 1)[0] + '...'
    
    return response.strip()

def restart_program():
    """Restart the current program."""
    logger.info("Restarting the program...")
    python = sys.executable
    os.execv(python, [python] + sys.argv)
    
class BaseWatcher(FileSystemEventHandler):
    """
    A base file watcher that accepts a dictionary of file paths and a callback.
    The callback is executed whenever one of the watched files is modified.
    """
    def __init__(self, file_paths: dict, callback):
        """
        file_paths: dict mapping file paths (as strings) to a file key/identifier.
        callback: a callable that takes the file key as an argument.
        """
        super().__init__()
        # Normalize and store the file paths
        self.file_paths = {str(Path(fp).resolve()): key for fp, key in file_paths.items()}
        self.callback = callback
        logger.info(f"Watching files: {list(self.file_paths.values())}")

    def on_modified(self, event):
        path = str(Path(event.src_path).resolve())
        if path in self.file_paths:
            file_key = self.file_paths[path]
            logger.info(f"Detected update in {file_key}")
            self.callback(file_key)


class MarkdownWatcher(BaseWatcher):
    """
    Watcher subclass that monitors markdown/setup files.
    When any of the files change, it updates context and commits the changes.
    """
    def __init__(self):
        # Build the file mapping from SETUP_FILES:
        # SETUP_FILES is assumed to be a dict mapping keys (e.g., "ARCHITECTURE") to Path objects.
        file_mapping = {str(path.resolve()): name for name, path in SETUP_FILES.items()}
        super().__init__(file_mapping, self.markdown_callback)

    def markdown_callback(self, file_key):
        # Handle markdown file updates:
        logger.info(f"Processing update from {file_key}")
        update_context({})
        make_atomic_commit()


class ScriptWatcher(BaseWatcher):
    """
    Watcher subclass that monitors the script file for changes.
    When the script file is modified, it triggers a self-restart.
    """
    def __init__(self, script_path):
        # We only want to watch the script file itself.
        file_mapping = {os.path.abspath(script_path): "Script File"}
        super().__init__(file_mapping, self.script_callback)

    def script_callback(self, file_key):
        logger.info(f"Detected change in {file_key}. Restarting the script...")
        time.sleep(1)  # Allow time for the file write to complete.
        restart_program()

def run_observer(observer: Observer):
    """Helper to run an observer in a thread."""
    observer.start()
    observer.join()
    
def main():
    """Main function to handle arguments and execute appropriate actions"""
    try:
        if ARGS.setup:
            # Normalize the setup argument to uppercase
            ide_env = ARGS.setup.upper()
            os.environ['IDE_ENV'] = ide_env
            setup_project()
            if not ARGS.watch:
                return 0

        if ARGS.update and ARGS.update_value:
            update_specific_file(ARGS.update, ARGS.update_value)
            if not ARGS.watch:
                return 0
                
        # Handle task management actions
        if ARGS.task_action:
            kwargs = {}
            if ARGS.task_description:
                kwargs["description"] = ARGS.task_description
            if ARGS.task_id:
                kwargs["task_id"] = ARGS.task_id
            if ARGS.task_status:
                kwargs["status"] = ARGS.task_status
            if ARGS.task_note:
                kwargs["note"] = ARGS.task_note
                
            result = manage_task(ARGS.task_action, **kwargs)
            if result:
                if isinstance(result, list):
                    for task in result:
                        logger.info(json.dumps(task.to_dict(), indent=2))
                else:
                    logger.info(json.dumps(result.to_dict(), indent=2))
            if not ARGS.watch:
                return 0
                
        # Handle git management actions
        if ARGS.git_action:
            context = read_context_file()
            git_manager = context.get("git_manager")
            
            if not git_manager and ARGS.git_repo:
                try:
                    git_manager = GitManager(ARGS.git_repo)
                    context["git_manager"] = git_manager
                    context["repo_path"] = str(Path(ARGS.git_repo).resolve())
                    write_context_file(context)
                except Exception as e:
                    logger.error(f"Failed to initialize git manager: {e}")
                    return 1
            
            if not git_manager:
                logger.error("No git repository configured. Use --git-repo to specify one.")
                return 1
            
            try:
                if ARGS.git_action == "status":
                    state = git_manager.get_repository_state()
                    logger.info(json.dumps(state, indent=2))
                elif ARGS.git_action == "branch":
                    if ARGS.branch_name:
                        git_manager._run_git_command(["checkout", "-b", ARGS.branch_name])
                        logger.info(f"Created and switched to branch: {ARGS.branch_name}")
                    else:
                        logger.info(f"Current branch: {git_manager.get_current_branch()}")
                elif ARGS.git_action == "commit":
                    if not ARGS.commit_message:
                        logger.error("Commit message required")
                        return 1
                    if git_manager.commit_changes(ARGS.commit_message):
                        logger.info("Changes committed successfully")
                    else:
                        logger.error("Failed to commit changes")
                elif ARGS.git_action == "push":
                    stdout, stderr = git_manager._run_git_command(["push"])
                    if stdout:
                        logger.info(stdout)
                    if stderr:
                        logger.error(stderr)
                elif ARGS.git_action == "pull":
                    stdout, stderr = git_manager._run_git_command(["pull"])
                    if stdout:
                        logger.info(stdout)
                    if stderr:
                        logger.error(stderr)
            except Exception as e:
                logger.error(f"Git action failed: {e}")
                return 1
                
            if not ARGS.watch:
                return 0

        if ARGS.watch:
            update_context({})

            # === Setup Markdown Watcher ===
            markdown_watcher = MarkdownWatcher()
            markdown_observer = Observer()
            markdown_observer.schedule(markdown_watcher, str(PWD), recursive=False)

            # === Setup Script Watcher ===
            script_watcher = ScriptWatcher(__file__)
            script_observer = Observer()
            script_observer.schedule(script_watcher, os.path.dirname(os.path.abspath(__file__)), recursive=False)

            # === Start Both Observers in Separate Threads ===
            t1 = Thread(target=run_observer, args=(markdown_observer,), daemon=True)
            t2 = Thread(target=run_observer, args=(script_observer,), daemon=True)
            t1.start()
            t2.start()

            logger.info("Watching project files and script for changes. Press Ctrl+C to stop...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                markdown_observer.stop()
                script_observer.stop()
                t1.join()
                t2.join()
                return 0

        # Default: just update the context
        update_context({})
        return 0

    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}", exc_info=True)
        return 1


# Add new function to manage tasks
def manage_task(action: str, **kwargs):
    """
    Manage tasks in the context
    
    Args:
        action: One of 'add', 'update', 'note', 'list', 'get'
        **kwargs: Additional arguments based on action
    """
    context = read_context_file()
    if "tasks" not in context:
        context["tasks"] = {}
    task_manager = TaskManager(context["tasks"])
    
    result = None
    if action == "add":
        result = task_manager.add_task(kwargs["description"])
        sys.stderr.write("\nCreated new task:\n")
        sys.stderr.write(json.dumps(result.to_dict(), indent=2) + "\n")
        sys.stderr.flush()
        context["tasks"] = task_manager.tasks
        # Update tasks in cursor rules
        rules_content = safe_read_file(GLOBAL_RULES_PATH)
        if not rules_content:
            rules_content = "# Tasks"
        # Check if Tasks section exists
        if "# Tasks" not in rules_content:
            rules_content += "\n\n# Tasks"
        # Find the Tasks section and append the new task
        lines = rules_content.split("\n")
        tasks_section_idx = -1
        for i, line in enumerate(lines):
            if line.strip() == "# Tasks":
                tasks_section_idx = i
                break
        
        if tasks_section_idx >= 0:
            # Find where to insert the new task (after the last task or after the Tasks header)
            insert_idx = tasks_section_idx + 1
            for i in range(tasks_section_idx + 1, len(lines)):
                if lines[i].startswith("### Task"):
                    insert_idx = i + 1
                    # Skip past the task's content
                    while i + 1 < len(lines) and (lines[i + 1].startswith("Status:") or lines[i + 1].startswith("Note:")):
                        i += 1
                        insert_idx = i + 1
            
            # Insert task at the correct position
            task_content = [
                f"\n### Task {result.id}: {result.description}",
                f"Status: {result.status}"
            ]
            lines[insert_idx:insert_idx] = task_content
            rules_content = "\n".join(lines)
        else:
            # Append to the end
            rules_content += f"\n\n### Task {result.id}: {result.description}\n"
            rules_content += f"Status: {result.status}\n"
        
        save_rules(context_content=rules_content)
        sys.stderr.write("\nTask added to .cursorrules file\n")
        sys.stderr.flush()
        
        # If git manager exists, create a branch for the task
        if context.get("git_manager"):
            try:
                branch_name = f"task/{result.id}-{kwargs['description'].lower().replace(' ', '-')}"
                context["git_manager"]._run_git_command(["checkout", "-b", branch_name])
                sys.stderr.write(f"\nCreated branch {branch_name} for task {result.id}\n")
                sys.stderr.flush()
            except Exception as e:
                logger.error(f"Failed to create branch for task: {e}")
    elif action == "update":
        task_manager.update_task_status(kwargs["task_id"], kwargs["status"])
        result = task_manager.get_task(kwargs["task_id"])
        sys.stderr.write("\nUpdated task:\n")
        sys.stderr.write(json.dumps(result.to_dict(), indent=2) + "\n")
        sys.stderr.flush()
        context["tasks"] = task_manager.tasks
        # Update task status in cursor rules
        rules_content = safe_read_file(GLOBAL_RULES_PATH)
        if rules_content:
            # Find and update the task status
            lines = rules_content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith(f"### Task {kwargs['task_id']}:"):
                    for j in range(i+1, len(lines)):
                        if lines[j].startswith("Status:"):
                            lines[j] = f"Status: {kwargs['status']}"
                            break
                    break
            rules_content = "\n".join(lines)
            save_rules(context_content=rules_content)
            sys.stderr.write("\nTask status updated in .cursorrules file\n")
            sys.stderr.flush()
        # If task is completed and git manager exists, try to merge the task branch
        if kwargs["status"] == TaskStatus.COMPLETED and context.get("git_manager"):
            try:
                context["git_manager"]._run_git_command(["checkout", "main"])
                context["git_manager"]._run_git_command(["merge", f"task/{kwargs['task_id']}"])
                sys.stderr.write(f"\nMerged task branch for task {kwargs['task_id']}\n")
                sys.stderr.flush()
            except Exception as e:
                logger.error(f"Failed to merge task branch: {e}")
    elif action == "note":
        task_manager.add_note_to_task(kwargs["task_id"], kwargs["note"])
        result = task_manager.get_task(kwargs["task_id"])
        sys.stderr.write("\nAdded note to task:\n")
        sys.stderr.write(json.dumps(result.to_dict(), indent=2) + "\n")
        sys.stderr.flush()
        context["tasks"] = task_manager.tasks
        # Add note to cursor rules
        rules_content = safe_read_file(GLOBAL_RULES_PATH)
        if rules_content:
            # Find the task and add the note
            lines = rules_content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith(f"### Task {kwargs['task_id']}:"):
                    # Find the end of the task section
                    for j in range(i+1, len(lines)):
                        if j == len(lines)-1 or lines[j+1].startswith("### Task"):
                            lines.insert(j+1, f"Note: {kwargs['note']}\n")
                            break
                    break
            rules_content = "\n".join(lines)
            save_rules(context_content=rules_content)

            sys.stderr.write("\nNote added to  file\n")
            sys.stderr.flush()
    elif action == "list":
        result = task_manager.list_tasks(kwargs.get("status"))
        if result:
            sys.stderr.write("\nTasks:\n")
            for task in result:
                sys.stderr.write(json.dumps(task.to_dict(), indent=2) + "\n")
            sys.stderr.flush()
        else:
            sys.stderr.write("\nNo tasks found\n")
            sys.stderr.flush()
    elif action == "get":
        result = task_manager.get_task(kwargs["task_id"])
        if result:
            sys.stderr.write("\nTask details:\n")
            sys.stderr.write(json.dumps(result.to_dict(), indent=2) + "\n")
            sys.stderr.flush()
        else:
            sys.stderr.write(f"\nTask {kwargs['task_id']} not found\n")
            sys.stderr.flush()
        
    write_context_file(context)
    return result

def read_context_file() -> dict:
    """Read the context file"""
    try:
        if os.path.exists(CONTEXT_RULES_PATH):
            with open(CONTEXT_RULES_PATH, "r") as f:
                context = json.load(f)
                if "tasks" not in context:
                    context["tasks"] = {}
                return context
    except Exception as e:
        logger.error(f"Error reading existing context: {e}")
    return {
        "tasks": {},
        "repo_path": str(Path.cwd()),
        "git_manager": None
    }

def write_context_file(context: dict) -> None:
    """Write the context file"""
    try:
        # Convert tasks to dict format
        if "tasks" in context:
            context["tasks"] = {
                task_id: task.to_dict() if isinstance(task, Task) else task
                for task_id, task in context["tasks"].items()
            }
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(CONTEXT_RULES_PATH), exist_ok=True)
        with open(CONTEXT_RULES_PATH, "w") as f:
            json.dump(context, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing context file: {e}")

def update_file_content(context, key, file_path):
    """Update context with file content for a specific key"""
    if file_path.exists():
        content = safe_read_file(file_path)
        if content == "":
            context[key.lower()] = f"{file_path.name} is empty. Please update it."
        else:
            context[key.lower()] = content
    else:
        context[key.lower()] = f"{file_path.name} does not exist. Please create it."
    return context

def extract_project_name(content):
    """Extract project name from architecture content"""
    if not content:
        return ""
    
    for line in content.split('\n'):
        if line.startswith("# "):
            return line[2:].strip()
    return ""

SETUP_FILES = {
    "ARCHITECTURE": Path("ARCHITECTURE.md").resolve(),
    "PROGRESS": Path("PROGRESS.md").resolve(),
    "TASKS": Path("TASKS.md").resolve(),
}

ARCHITECTURE_PATH = SETUP_FILES["ARCHITECTURE"]
PROGRESS_PATH = SETUP_FILES["PROGRESS"]
TASKS_PATH = SETUP_FILES["TASKS"]

def safe_read_file(file_path):
    """Safely read a file with proper error handling"""
    error_message = {
        ARCHITECTURE_PATH: "Architecture file not found. Please ask the user for requirements to create it.",
        PROGRESS_PATH: "Progress file not found. Please generate from ARCHITECTURE.md",
        TASKS_PATH: "Tasks file not found. Please generate from PROGRESS.md",
    }
    msg = ""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        if file_path in error_message:
            msg = error_message[file_path]
        else:
            msg = f"File not found: {file_path}"
        logger.warning(msg)
        return msg
    except Exception as e:
        msg = f"Error reading file {file_path}: {e}"
        logger.error(msg)
        return msg

def safe_write_file(file_path, content):
    """Safely write to a file with proper error handling"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"File written successfully: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing to file {file_path}: {e}")
        return False

def ensure_file_exists(file_path):
    """Ensure file and its parent directories exist"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if not file_path.exists():
            file_path.touch()
            return True
        return True
    except Exception as e:
        logger.error(f"Failed to create {file_path}: {e}")
        return False

if __name__ == "__main__":
    exit(main())