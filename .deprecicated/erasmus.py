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

"""
Erasmus: AI Context Watcher for Development
===========================================

This module implements a context tracking and injection system designed to enhance
AI-powered development environments.

The Erasmus Context Watcher monitors project state by tracking changes to key documentation
files (.erasmus/.architecture.md, .progress.md, and .tasks.md), and dynamically updates context files
that are used by AI-powered IDEs like cursor and windsurf to improve their understanding
of the codebase and development process.

Key Components:
--------------
1. File Watchers - Monitor key project files for changes
2. Context Injection - Update IDE context files with project state
3. Task Management - Track development tasks and their status
4. Git Integration - Provide atomic commits with AI-generated messages
5. IDE Environment Detection - Automatically identify the current IDE

Usage:
------
The system can be used in the following ways:
- As a background watcher: `uv run watcher.py --watch`
- To set up a new project: `uv run watcher.py --setup`
- To manage tasks: `uv run watcher.py --task-action [add|update|list] [options]`
- To update specific files: `uv run watcher.py --update [architecture|progress|tasks] --update-value "content"`

Environment:
-----------
Requires the following configuration in .env file:
- IDE_ENV: The IDE environment (cursor or windsurf)
- OPENAI_API_KEY: OpenAI API key for AI integrations
- OPENAI_BASE_URL: URL for OpenAI API (or local model)
- OPENAI_MODEL: Model to use for AI features

architecture:
------------
The system uses a modular design with several key classes:
- TaskManager/Task: Track and manage development tasks
- GitManager: Handle git operations and commit generation
- FileSystemEventHandler implementations: Monitor file changes
- Context management functions: Handle reading/writing context files

Dependencies:
------------
- openai: For AI integration features
- rich: For enhanced console output
- watchdog: For file system monitoring
- python-dotenv: For environment configuration

Author: Bakobi (https://github.com/bakobiibizo)
License: MIT
Version: 0.0.1
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from getpass import getpass
from pathlib import Path
from threading import Thread

from dotenv import load_dotenv
from openai import OpenAI
from rich import console
from rich.logging import RichHandler
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

GIT_COMMITS = True


# === Task Tracking ===
class TaskStatus:
    """
    Task status constants.

    This class defines constants representing different states of a task
    throughout its lifecycle. Used by the Task class to track current status.
    """

    PENDING = "pending"  # Task is acknowledged but not started
    IN_progress = "in_progress"  # Task is actively being worked on
    COMPLETED = "completed"  # Task has been finished
    BLOCKED = "blocked"  # Task is blocked by another task or external factor
    NOT_STARTED = "not_started"  # Task has been created but not scheduled


class Task:
    """
    Represents a single development task with tracking information.

    This class provides methods for managing a task's state, including
    serialization/deserialization and metadata tracking. Each task has a
    unique ID, description, status, and timestamps for lifecycle events.

    Attributes:
        id (str): Unique identifier for the task
        description (str): Detailed description of the task
        status (str): Current status from TaskStatus constants
        created_at (float): Unix timestamp when task was created
        updated_at (float): Unix timestamp when task was last updated
        completion_time (Optional[float]): Unix timestamp when task was completed
        notes (List[str]): List of additional notes or comments for the task
    """

    def __init__(self, id: str, description: str):
        """
        Initialize a new Task with given ID and description.

        Args:
            id (str): Unique identifier for the task
            description (str): Detailed description of what the task involves
        """
        self.id = id
        self.description = description
        self.status = TaskStatus.NOT_STARTED
        self.created_at = time.time()
        self.updated_at = time.time()
        self.completion_time = None
        self.notes = []

    def to_dict(self) -> dict:
        """
        Convert task to dictionary representation for serialization.

        Returns:
            dict: Dictionary containing all task attributes
        """
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completion_time": self.completion_time,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """
        Create a Task instance from a dictionary representation.

        Args:
            data (dict): Dictionary containing task attributes

        Returns:
            Task: New Task instance with restored attributes
        """
        task = cls(data["id"], data["description"])
        task.status = data["status"]
        task.created_at = data["created_at"]
        task.updated_at = data["updated_at"]
        task.completion_time = data["completion_time"]
        task.notes = data["notes"]
        return task


class TaskManager:
    """
    Manages a collection of tasks and provides operations for the task lifecycle.

    This class handles creating, retrieving, updating, and listing tasks. It also
    provides serialization/deserialization to integrate with the context tracking
    system.

    Attributes:
        tasks (Dict[str, Task]): Dictionary mapping task IDs to Task objects
    """

    def __init__(self, tasks: dict | None = None):
        """
        Initialize a new TaskManager with optional initial tasks.

        Args:
            tasks (Optional[dict]): Dictionary of tasks to initialize with. Can be
                                   either Task objects or dictionaries to deserialize.
        """
        self.tasks = {}
        if tasks:
            self.tasks = {
                task_id: Task.from_dict(task_data) if isinstance(task_data, dict) else task_data
                for task_id, task_data in tasks.items()
            }

    def add_task(self, description: str) -> Task:
        """
        Add a new task with the given description.

        Creates a new Task with an automatically assigned sequential ID and
        adds it to the task collection.

        Args:
            description (str): Description of the new task

        Returns:
            Task: The newly created Task object
        """
        task_id = str(len(self.tasks) + 1)
        task = Task(task_id, description)
        self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Task | None:
        """
        Retrieve a task by its ID.

        Args:
            task_id (str): ID of the task to retrieve

        Returns:
            Optional[Task]: The Task if found, None otherwise
        """
        return self.tasks.get(task_id)

    def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """
        List all tasks, optionally filtered by status.

        Args:
            status (Optional[TaskStatus]): If provided, only tasks with this status
                                           will be returned

        Returns:
            List[Task]: List of tasks matching the filter criteria
        """
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """
        Update a task's status.

        Args:
            task_id (str): ID of the task to update
            status (TaskStatus): New status to set
        """
        if task := self.get_task(task_id):
            task.status = status
            task.updated_at = time.time()
            if status == TaskStatus.COMPLETED:
                task.completion_time = time.time()

    def add_note_to_task(self, task_id: str, note: str) -> None:
        """
        Add a note to a task.

        Args:
            task_id (str): ID of the task to add the note to
            note (str): Content of the note to add
        """
        if task := self.get_task(task_id):
            task.notes.append(note)
            task.updated_at = time.time()

    @classmethod
    def from_dict(cls, data):
        """
        Create a TaskManager from a dictionary representation.

        Args:
            data (dict): Dictionary mapping task IDs to task data dictionaries

        Returns:
            TaskManager: New TaskManager instance with restored tasks
        """
        manager = cls()
        if isinstance(data, dict):
            manager.tasks = {
                task_id: Task.from_dict(task_data) for task_id, task_data in data.items()
            }
        return manager


def is_valid_url(url: str) -> bool:
    """
    Validate a URL string to ensure it's properly formatted.

    This function performs regex-based validation for URLs used in API connections.
    It supports both standard web URLs and localhost/IP-based URLs for local development.

    Accepted URL formats:
    - Standard HTTP/HTTPS URLs: https://api.openai.com/v1
    - Localhost URLs with optional port: http://localhost:11434/v1
    - IP-based localhost URLs: http://127.0.0.1:8000/v1

    Args:
        url (str): The URL string to validate

    Returns:
        bool: True if the URL matches a valid pattern, False otherwise

    Example:
        >>> is_valid_url("https://api.openai.com/v1")
        True
        >>> is_valid_url("http://localhost:11434/v1")
        True
        >>> is_valid_url("not-a-url")
        False
    """
    if not url:
        return False

    # Log the URL being validated for debugging
    logger.debug(f"Validating URL: {url}")

    # Check for localhost or 127.0.0.1
    localhost_pattern = re.match(r"^https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(?:/.*)?$", url)
    if localhost_pattern:
        logger.debug(f"URL {url} matched localhost pattern")
        return True

    # Check for standard http/https URLs
    standard_pattern = re.match(r"^https?://[\w\.-]+(?::\d+)?(?:/.*)?$", url)
    result = bool(standard_pattern)

    if result:
        logger.debug(f"URL {url} matched standard pattern")
    else:
        logger.warning(f"URL validation failed for: {url}")

    return result


def detect_ide_environment() -> str:
    """
    Detect the current IDE environment based on environment variables or file markers.

    This function uses multiple detection strategies in order of preference:
    1. Check the IDE_ENV environment variable
    2. Check for IDE-specific file markers in the current directory and home directory
    3. Default to 'cursor' if no environment can be detected

    The detection is important for determining where to save context files and
    how to format them correctly for the specific IDE.

    Returns:
        str: The detected IDE environment ('windsurf' or 'cursor')
    """
    from erasmus.utils.paths import SetupPaths

    # Check environment variable first
    ide_env = os.getenv("IDE_ENV", "").lower()
    if ide_env:
        if ide_env.startswith("w"):
            return "windsurf"
        if ide_env.startswith("c"):
            return "cursor"

    # Try to detect based on current working directory or known IDE paths
    setup_paths = SetupPaths.with_project_root(Path.cwd())

    # windsurf-specific detection
    windsurf_markers = [
        Path.home() / ".codeium" / "windsurf",
        setup_paths.rules_file if ide_env.startswith("w") else None,
    ]

    # cursor-specific detection
    cursor_markers = [
        setup_paths.rules_file if ide_env.startswith("c") else None,
        Path.home() / ".cursor",
    ]

    # Check windsurf markers
    for marker in windsurf_markers:
        if marker and marker.exists():
            return "windsurf"

    # Check cursor markers
    for marker in cursor_markers:
        if marker and marker.exists():
            return "cursor"

    # Default to cursor
    return "cursor"


def prompt_openai_credentials(env_path=".env"):
    """Prompt user for OpenAI credentials and save to .env"""
    global GIT_COMMITS

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(
            "If you are running local inference and do not have an api key configured just use sk-1234"
        )
        api_key = getpass("Enter your OPENAI_API_KEY (input hidden): ")
        if not api_key:
            print("API Key missing. Disabling commit message generation.")
            GIT_COMMITS = False
            api_key = "sk-1234"

    base_url = os.getenv("OPENAI_BASE_URL")
    if not base_url:
        print("Enter your OpenAI base URL.")
        print(
            "If you are running local inference use your local host url(e.g. for ollama: http://localhost:11434/v1)"
        )
        base_url = input(
            "Enter your OPENAI_BASE_URL (default: https://api.openai.com/v1): "
        ).strip()
        if not is_valid_url(base_url):
            print("Invalid URL or empty. Defaulting to https://api.openai.com/v1")
            base_url = "https://api.openai.com/v1"

    model = os.getenv("OPENAI_MODEL")
    if not model:
        model = input("Enter your OPENAI_MODEL (default: gpt-4o): ").strip()
        if not model:
            model = "gpt-4o"

    # Detect IDE environment and save it to the .env file
    ide_env = detect_ide_environment()

    env_content = (
        "\n"
        f"OPENAI_API_KEY={api_key}\n"
        f"OPENAI_BASE_URL={base_url}\n"
        f"OPENAI_MODEL={model}\n"
        f"IDE_ENV={ide_env}\n"
    )
    envpath = Path(env_path)
    if not envpath.exists():
        envpath.write_text("# Environment Variables")
    existing_content = envpath.read_text()
    env_content = existing_content + env_content

    envpath.write_text(env_content)
    load_dotenv()
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
    tracebacks_show_locals=True,
)

# Set up logging configuration
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(message)s",
    datefmt="[%X]",
    handlers=[logging_handler],
)

# Create logger instance
logger = logging.getLogger("context_watcher")

# Add file handler for persistent logging
try:
    file_handler = logging.FileHandler("context_watcher.log")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
except Exception as e:
    logger.warning(f"Could not set up file logging: {e}")


def get_openai_credentials():
    """Get OpenAI credentials from environment variables"""
    global GIT_COMMITS

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        GIT_COMMITS = False
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL")
    return api_key, base_url, model


# --- OpenAI Client Initialization ---
def init_openai_client():
    """Initialize and return OpenAI client configuration"""
    try:
        api_key, base_url, model = get_openai_credentials()

        # Check if any credentials are missing
        missing_creds = []
        if not api_key:
            missing_creds.append("API key")
        if not base_url:
            missing_creds.append("base URL")
        if not model:
            missing_creds.append("model")

        if missing_creds:
            logger.warning(
                f"Missing OpenAI credentials: {', '.join(missing_creds)}. Prompting for input..."
            )
            prompt_openai_credentials()
            api_key, base_url, model = get_openai_credentials()

            # Check again after prompting
            if not api_key:
                logger.error("Failed to initialize OpenAI client: missing API key")
                return None, None
            if not model:
                logger.error("Failed to initialize OpenAI client: missing model name")
                return None, None

        # Ensure base_url has a valid format
        if not base_url:
            base_url = "https://api.openai.com/v1"
            logger.warning(f"Using default OpenAI base URL: {base_url}")
        elif not is_valid_url(base_url):
            logger.warning(f"Invalid base URL format: {base_url}. Using default.")
            base_url = "https://api.openai.com/v1"

        logger.info(f"Initializing OpenAI client with base URL: {base_url} and model: {model}")
        client = OpenAI(api_key=api_key, base_url=base_url)
        return client, model
    except Exception as e:
        logger.exception(f"Failed to initialize OpenAI client: {e}")
        return None, None


# Global variables
CLIENT, OPENAI_MODEL = init_openai_client()


PWD = Path(__file__).parent


# === Argument Parsing ===
def parse_arguments():
    parser = argparse.ArgumentParser(description="Update script for project")
    parser.add_argument("--watch", action="store_true", help="Enable file watching")
    parser.add_argument(
        "--update", choices=["architecture", "progress", "tasks", "context"], help="File to update"
    )
    parser.add_argument("--update-value", help="New value to write to the specified file")
    parser.add_argument("--setup", help="Setup project", action="store_true")
    parser.add_argument(
        "--type",
        choices=["cursor", "windsurf", "cursor", "windsurf"],
        help="Project type",
        default="cursor",
    )

    # Task management arguments
    task_group = parser.add_argument_group("Task Management")
    task_group.add_argument(
        "--task-action",
        choices=["add", "update", "note", "list", "get"],
        help="Task management action",
    )
    task_group.add_argument("--task-id", help="Task ID for update/note/get actions")
    task_group.add_argument("--task-description", help="Task description for add action")
    task_group.add_argument(
        "--task-status",
        choices=[
            TaskStatus.PENDING,
            TaskStatus.IN_progress,
            TaskStatus.COMPLETED,
            TaskStatus.BLOCKED,
        ],
        help="Task status for update action",
    )
    task_group.add_argument("--task-note", help="Note content for note action")

    # Git management arguments
    git_group = parser.add_argument_group("Git Management")
    git_group.add_argument("--git-repo", help="Path to git repository")
    git_group.add_argument(
        "--git-action",
        choices=["status", "branch", "commit", "push", "pull"],
        help="Git action to perform",
    )
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

- **.erasmus/.architecture.md**
  Primary source of truth. Contains all major components and their requirements.
  → If missing, ask the user for requirements and generate this document.

- **.progress.md**
  Tracks major components and organizes them into a development schedule.
  → If missing, generate from `.erasmus/.architecture.md`.

- **.tasks.md**
  Contains action-oriented tasks per component, small enough to develop and test independently.
  → If missing, select the next component from `.progress.md` and break it into tasks.

---

## 🔁 WORKFLOW

```mermaid
flowchart TD
    Start([Start])
    Checkarchitecture{architecture exists?}
    AskRequirements["Ask user for requirements"]
    Checkprogress{progress exists?}
    BreakDownArch["Break architecture into major components"]
    DevSchedule["Organize components into a dev schedule"]
    Checktasks{tasks exist?}
    Createtasks["Break next component into individual tasks"]
    Reviewtasks["Review tasks"]
    DevTask["Develop a task"]
    TestTask["Test the task until it passes"]
    Updatetasks["Update tasks"]
    IsprogressComplete{All progress completed?}
    LoopBack["Loop"]
    Done([✅ Success])

    Start --> Checkarchitecture
    Checkarchitecture -- Yes --> Checkprogress
    Checkarchitecture -- No --> AskRequirements --> Checkprogress
    Checkprogress -- Yes --> DevSchedule
    Checkprogress -- No --> BreakDownArch --> DevSchedule
    DevSchedule --> Checktasks
    Checktasks -- No --> Createtasks --> Reviewtasks
    Checktasks -- Yes --> Reviewtasks
    Reviewtasks --> DevTask --> TestTask --> Updatetasks --> IsprogressComplete
    IsprogressComplete -- No --> LoopBack --> Checktasks
    IsprogressComplete -- Yes --> Done
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
   - Use .erasmus/.architecture.md for project structure
   - Use .progress.md for development tracking
   - Use .tasks.md for granular task management
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
if ARGS.setup:
    IDE_ENV = detect_ide_environment()
    KEY_NAME = "windsurf" if IDE_ENV.startswith("w") else "cursor"

# === File Paths Configuration ===


def get_rules_file_path(context_type="global") -> tuple[Path, Path]:
    """
    Determine the appropriate rules file paths based on IDE environment.

    Args:
        context_type (str): Type of rules file, either 'global' or 'context'

    Returns:
        Tuple[Path, Path]: Resolved paths to the context and global rules files
    """
    from erasmus.utils.paths import SetupPaths

    # Use SetupPaths to get the correct paths
    setup_paths = SetupPaths.with_project_root(Path.cwd())
    context_path = setup_paths.rules_file
    global_path = setup_paths.global_rules_file

    # Ensure the directories exist and create files if they don't
    if context_path and not context_path.exists():
        context_path.parent.mkdir(parents=True, exist_ok=True)
        context_path.touch()  # Create the file if it doesn't exist

    if global_path and not global_path.exists():
        global_path.parent.mkdir(parents=True, exist_ok=True)
        global_path.touch()  # Create the file if it doesn't exist

    # Return the fully resolved absolute paths
    return context_path.resolve(), global_path.resolve()


def save_global_rules(rules_content):
    """
    Save global rules to the appropriate location based on IDE environment.

    Args:
        rules_content (str): Content of the global rules
    """
    _, global_rules_path = get_rules_file_path()

    # First, write the file regardless of IDE environment
    try:
        with open(global_rules_path, "w") as f:
            f.write(rules_content)
        logger.info(f"Global rules saved to {global_rules_path}")
    except Exception as e:
        logger.exception(f"Failed to save global rules: {e}")

    # If cursor, show the warning but don't return early
    if detect_ide_environment() == "cursor":
        logger.warning(
            "For cursor, please also manually copy global rules to settings. "
            "The file has been saved to global_rules.md, but you need to add this content to cursor settings.",
        )
        print(rules_content)


def save_context_rules(context_content):
    """
    Save context-specific rules to the appropriate location.

    Args:
        context_content (str): Content of the context rules
    """
    context_rules_path, _ = get_rules_file_path()

    try:
        with open(context_rules_path, "w") as f:
            f.write(context_content)
        logger.info(f"Context rules saved to {context_rules_path}")
    except Exception as e:
        logger.exception(f"Failed to save context rules: {e}")


# Update global variables to use resolved paths
CONTEXT_RULES_PATH, GLOBAL_RULES_PATH = get_rules_file_path()


# === Project Setup ===
def setup_project():
    """Setup the project with necessary files"""

    # Create all required files
    for file in [GLOBAL_RULES_PATH, CONTEXT_RULES_PATH]:
        ensure_file_exists(file)

    # Always write global rules to global_rules.md
    save_global_rules(GLOBAL_RULES)
    logger.info(f"Created global rules at {GLOBAL_RULES_PATH}")
    logger.info("Please add the contents of global_rules.md to your IDE's global rules section")

    # Initialize cursor rules file if empty
    if not safe_read_file(CONTEXT_RULES_PATH):
        # Initialize with current architecture, progress and tasks
        context = {
            "architecture": safe_read_file(architecture_PATH),
            "progress": safe_read_file(progress_PATH),
            "tasks": safe_read_file(tasks_PATH),
        }
        update_context(context)

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
    elif architecture_PATH.exists():
        content["architecture"] = safe_read_file(architecture_PATH)
    else:
        content["architecture"] = ""

    # Add progress if available
    if context.get("progress"):
        content["progress"] = context["progress"]
    elif progress_PATH.exists():
        content["progress"] = safe_read_file(progress_PATH)
    else:
        content["progress"] = ""

    # Add tasks section
    if context.get("tasks"):
        content["tasks"] = context["tasks"]
    elif tasks_PATH.exists():
        content["tasks"] = safe_read_file(tasks_PATH)
    else:
        content["tasks"] = ""

    # Write to context file
    safe_write_file(CONTEXT_RULES_PATH, json.dumps(content, indent=2))
    make_atomic_commit()

    return content


def update_specific_file(file_type, content):
    """
    Update a specific project file with new content.

    This function allows targeted updates to individual project files based on their
    logical type (e.g., architecture, progress, tasks). It handles the special case
    of CONTEXT updates and ensures that the context tracking system is updated
    and changes are committed to Git after file modifications.

    Args:
        file_type (str): The type of file to update. Must be one of the keys in
            SETUP_FILES dictionary (e.g., "architecture", "progress", "tasks")
            or "CONTEXT" for special handling of context updates.
        content (str): The new content to write to the file.

    Returns:
        bool: Implicitly returns True if successful, False otherwise
            (through the called functions).

    Side Effects:
        - Updates the specified file with new content
        - Updates the context tracking system
        - Creates a Git commit with the changes

    Note:
        The file_type parameter is case-insensitive. It will be converted to
        lowercase before processing.
    """
    file_type = file_type.lower()

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
    """
    Lightweight Git repository management for context tracking.

    This class provides a simplified interface for common Git operations
    required by the Erasmus context watcher. It handles repository initialization,
    staging changes, creating commits, and retrieving repository status.

    The GitManager is designed to work with the local repository where the
    watcher is running, allowing for automated commits when context files
    are updated.

    Attributes:
        repo_path (Path): Path to the Git repository
    """

    def __init__(self, repo_path: str | Path):
        """
        Initialize GitManager with a repository path.

        Args:
            repo_path (str | Path): Path to the repository to manage

        Note:
            If the specified path is not a Git repository, it will be
            initialized as one automatically.
        """
        self.repo_path = Path(repo_path).resolve()
        if not self._is_git_repo():
            self._init_git_repo()

    def _is_git_repo(self) -> bool:
        """
        Check if the path is a git repository.

        Returns:
            bool: True if the path is a Git repository, False otherwise

        Implementation:
            Uses 'git rev-parse --is-inside-work-tree' to determine if
            the directory is already a Git repository
        """
        try:
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def _init_git_repo(self):
        """
        Initialize a new git repository if one doesn't exist.

        This method:
        1. Initializes a new Git repository at the specified path
        2. Configures default user information for commits

        Raises:
            Logs error if repository initialization fails
        """
        try:
            subprocess.run(
                ["git", "init"],
                cwd=self.repo_path,
                check=True,
            )
            # Configure default user
            subprocess.run(
                ["git", "config", "user.name", "Context Watcher"],
                cwd=self.repo_path,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "context.watcher@local"],
                cwd=self.repo_path,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            logger.exception(f"Failed to initialize git repository: {e}")

    def _run_git_command(self, command: list[str]) -> tuple[str, str]:
        """
        Run a git command and return stdout and stderr.

        This is a utility method used by other class methods to execute
        Git commands with proper error handling.

        Args:
            command (List[str]): Git command arguments (excluding 'git')

        Returns:
            Tuple[str, str]: A tuple containing (stdout, stderr) of the command

        Raises:
            Logs error if the command fails but doesn't raise exceptions
        """
        try:
            result = subprocess.run(
                ["git", *command],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip(), result.stderr.strip()
        except subprocess.CalledProcessError as e:
            logger.exception(f"Git command failed: {e}")
            return "", e.stderr.strip()

    def stage_all_changes(self) -> bool:
        """
        Stage all changes in the repository.

        This method is equivalent to running 'git add -A' and stages
        all modifications, additions, and deletions.

        Returns:
            bool: True if changes were staged successfully, False otherwise
        """
        try:
            self._run_git_command(["add", "-A"])
            return True
        except subprocess.CalledProcessError as e:
            logger.exception(f"Failed to stage changes: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error while staging changes: {e}")
            return False

    def commit_changes(self, message: str) -> bool:
        """
        Commit staged changes with a given message.

        Args:
            message (str): Commit message to use

        Returns:
            bool: True if changes were committed successfully, False otherwise

        Note:
            This method assumes changes have already been staged.
            Use stage_all_changes() before this method if needed.
        """
        try:
            self._run_git_command(["commit", "-m", message])
            return True
        except subprocess.CalledProcessError as e:
            logger.exception(f"Failed to commit changes: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error while committing changes: {e}")
            return False

    def validate_commit_message(self, message: str) -> tuple[bool, str]:
        """
        Validate a commit message against conventions.

        This method checks if the commit message follows conventional
        commit format and other best practices.

        Args:
            message (str): Commit message to validate

        Returns:
            Tuple[bool, str]: (is_valid, validation_message) where
                is_valid - True if the message is valid, False otherwise
                validation_message - Reason for validation result

        Conventions checked:
        - Message cannot be empty
        - Maximum length of 72 characters
        - Follows conventional commit format (type: description)
        - Type must be one of the standard conventional commit types
        """
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
                return (
                    False,
                    f"Invalid commit type. Must be one of: {', '.join(conventional_types)}",
                )

        return True, "Commit message is valid"

    def get_repository_state(self) -> dict:
        """
        Get the current state of the repository.

        This method retrieves and parses information about the current
        state of the repository, including branch name and file statuses.

        Returns:
            dict: A dictionary containing:
                - branch (str): Current branch name
                - staged (List[str]): Files staged for commit
                - unstaged (List[str]): Modified files not staged
                - untracked (List[str]): Untracked files

        Note:
            Returns a dict with empty lists and "unknown" branch on error.
        """
        try:
            # Get current branch
            branch = self.get_current_branch()

            # Get status
            status_output, _ = self._run_git_command(["status", "--porcelain"])
            status_lines = status_output.split("\n") if status_output else []

            # Parse status
            staged = []
            unstaged = []
            untracked = []

            for line in status_lines:
                if not line:
                    continue
                status = line[:2]
                path = line[3:].strip()

                if status.startswith("??"):
                    untracked.append(path)
                elif status[0] != " ":
                    staged.append(path)
                elif status[1] != " ":
                    unstaged.append(path)

            return {
                "branch": branch,
                "staged": staged,
                "unstaged": unstaged,
                "untracked": untracked,
            }
        except Exception as e:
            logger.exception(f"Failed to get repository state: {e}")
            return {
                "branch": "unknown",
                "staged": [],
                "unstaged": [],
                "untracked": [],
            }

    def get_current_branch(self) -> str:
        """
        Get the name of the current branch.

        Returns:
            str: Name of the current branch, or "unknown" on error
        """
        try:
            branch_output, _ = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
            return branch_output.strip()
        except Exception as e:
            logger.exception(f"Failed to get current branch: {e}")
            return "unknown"


def determine_commit_type(diff_output: str) -> str:
    """
    Programmatically determine the most appropriate commit type based on diff content.

    This function analyzes the Git diff output to identify the most appropriate
    conventional commit type prefix based on the changes detected. It uses pattern
    matching on keywords commonly associated with different types of changes.

    Args:
        diff_output (str): The output from 'git diff --staged' command

    Returns:
        str: One of the conventional commit type prefixes:
            - feat: New feature or functionality addition
            - fix: Bug fix or error correction
            - docs: Documentation-only changes
            - style: Formatting, whitespace changes (no code change)
            - refactor: Code restructuring without changing functionality
            - test: Adding or modifying tests
            - chore: Maintenance tasks, updates to build process, etc.

    Decision Logic:
        The function applies the following priority order when analyzing the diff:
        1. 'test' - If keywords like 'test', 'pytest', or '_test.py' are found
        2. 'fix' - If keywords like 'fix', 'bug', or 'error' are found
        3. 'docs' - If keywords like 'docs', 'readme', or 'documentation' are found
        4. 'style' - If keywords like 'style', 'format', or 'lint' are found
        5. 'refactor' - If keywords like 'refactor' or 'restructure' are found
        6. 'feat' - If new code elements like 'def ', 'class ', or 'new ' are found
        7. 'chore' - Default for all other types of changes

    Note:
        This function makes a best-effort determination based on simple pattern matching.
        It may not always correctly identify the commit type for complex changes that
        span multiple categories or require more sophisticated analysis.
    """
    # Convert diff to lowercase for case-insensitive matching
    diff_lower = diff_output.lower()

    # Prioritize specific patterns
    if "test" in diff_lower or "pytest" in diff_lower or "_test.py" in diff_lower:
        return "test"

    if "fix" in diff_lower or "bug" in diff_lower or "error" in diff_lower:
        return "fix"

    if "docs" in diff_lower or "readme" in diff_lower or "documentation" in diff_lower:
        return "docs"

    if "style" in diff_lower or "format" in diff_lower or "lint" in diff_lower:
        return "style"

    if "refactor" in diff_lower or "restructure" in diff_lower:
        return "refactor"

    # Check for new feature indicators
    if "def " in diff_lower or "class " in diff_lower or "new " in diff_lower:
        return "feat"

    # Default to chore for miscellaneous changes
    return "chore"


def check_creds():
    api_key, base_url, model = get_openai_credentials()
    print(api_key, base_url, model)
    return not ("sk-1234" in api_key and "openai" in base_url)


def make_atomic_commit():
    """Makes an atomic commit with AI-generated commit message."""
    if not check_creds():
        return False
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
            encoding="utf-8",
            errors="replace",  # Replace undecodable bytes
        )

        # Truncate diff if it's too long
        max_diff_length = 4000
        if len(diff_output) > max_diff_length:
            diff_output = diff_output[:max_diff_length] + "... (diff truncated)"

        # Sanitize diff output to remove potentially problematic characters
        diff_output = "".join(char for char in diff_output if ord(char) < 128)

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
                {"role": "user", "content": prompt},
            ],
            max_tokens=100,
        )

        # Sanitize commit message
        raw_message = response.choices[0].message.content
        commit_message = "".join(char for char in raw_message if ord(char) < 128)

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
        logger.error("Commit failed")
        return False

    except Exception as e:
        logger.exception(f"Error in atomic commit: {e}")
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
    code_block_match = re.search(r"```(?:markdown|commit)?(.+?)```", response, re.DOTALL)
    if code_block_match:
        response = code_block_match.group(1).strip()

    # Extract from markdown inline code
    inline_code_match = re.search(r"`(.+?)`", response)
    if inline_code_match:
        response = inline_code_match.group(1).strip()

    # Remove any leading type if already present
    type_match = re.match(
        r"^(feat|fix|docs|style|refactor|test|chore):\s*", response, re.IGNORECASE
    )
    if type_match:
        response = response[type_match.end() :]

    # Trim to 72 characters, respecting word boundaries
    if len(response) > 72:
        response = response[:72].rsplit(" ", 1)[0] + "..."

    return response.strip()


def restart_program():
    """Restart the current program."""
    logger.info("Restarting the program...")
    python = sys.executable
    os.execv(python, [python, *sys.argv])


class BaseWatcher(FileSystemEventHandler):
    """
    Base file system event handler for monitoring file changes.

    This class extends watchdog's FileSystemEventHandler to provide a configurable
    file monitoring system. It maps specific file paths to identifiers and executes
    a callback function when any of the monitored files are modified.

    The watcher normalizes all file paths to absolute paths to ensure consistent
    path comparison across different operating systems and environments.

    Attributes:
        file_paths (Dict[str, str]): Dictionary mapping normalized absolute file paths
            to their logical identifiers/keys
        callback (Callable): Function to call when a watched file is modified.
            The callback receives the file identifier as its argument.

    Methods:
        on_modified: Overridden method from FileSystemEventHandler that processes
            file modification events

    Example:
        >>> def on_change(file_id):
        ...     print(f"File {file_id} was changed")
        >>> watcher = BaseWatcher(
        ...     {"path/to/file.txt": "config_file", "path/to/other.md": "readme"}, on_change
        ... )
        >>> observer = Observer()
        >>> observer.schedule(watcher, "path/to", recursive=False)
        >>> observer.start()
    """

    def __init__(self, file_paths: dict, callback):
        """
        Initialize a new file watcher.

        Args:
            file_paths (Dict[str, str]): Dictionary mapping file paths to their
                logical identifiers/keys. Keys in this dictionary will be used
                to identify which file triggered the callback.
            callback (Callable): Function to call when a watched file is modified.
                The callback receives the file identifier as its argument.
        """
        super().__init__()
        # Normalize and store the file paths
        self.file_paths = {str(Path(fp).resolve()): key for fp, key in file_paths.items()}
        self.callback = callback
        logger.info(f"Watching files: {list(self.file_paths.values())}")

    def on_modified(self, event):
        """
        Handle file modification events.

        This method is automatically called by the watchdog Observer when a file
        in the watched directory is modified. It checks if the modified file is
        one of the tracked files and executes the callback if it is.

        Args:
            event (FileSystemEvent): Event object containing information about
                the file system change
        """
        path = str(Path(event.src_path).resolve())
        if path in self.file_paths:
            file_key = self.file_paths[path]
            logger.info(f"Detected update in {file_key}")
            self.callback(file_key)


class MarkdownWatcher(BaseWatcher):
    """
    Specialized watcher for monitoring markdown documentation files.

    This watcher subclass is specifically designed to monitor the project's
    documentation files (.erasmus/.architecture.md, .progress.md, .tasks.md, etc.).
    When any of these files change, it automatically updates the context
    tracking system and creates a Git commit to track the changes.

    The file mapping is built automatically from the SETUP_FILES dictionary,
    which defines the standard set of project documentation files.

    Attributes:
        Inherits all attributes from BaseWatcher

    Methods:
        markdown_callback: Callback function executed when a markdown file changes

    Note:
        This watcher is a key component of the automatic context tracking system,
        ensuring that documentation changes are immediately reflected in the
        IDE context and properly versioned in Git.
    """

    def __init__(self):
        """
        Initialize a new MarkdownWatcher.

        Automatically builds the file mapping from the SETUP_FILES global dictionary
        and configures the callback to update context and create a Git commit.
        """
        # Build the file mapping from SETUP_FILES:
        # SETUP_FILES is assumed to be a dict mapping keys (e.g., "architecture") to Path objects.
        file_mapping = {str(path.resolve()): name for name, path in SETUP_FILES.items()}
        super().__init__(file_mapping, self.markdown_callback)

    def markdown_callback(self, file_key):
        """
        Process updates to markdown documentation files.

        This callback is triggered whenever a watched markdown file is modified.
        It updates the context tracking system and creates an atomic Git commit
        to track the changes.

        Args:
            file_key (str): Identifier of the file that was modified
                (e.g., "architecture", "progress", "tasks")
        """
        # Handle markdown file updates:
        logger.info(f"Processing update from {file_key}")
        update_context({})
        make_atomic_commit()


class ScriptWatcher(BaseWatcher):
    """
    Specialized watcher for monitoring the script file itself.

    This watcher is responsible for detecting changes to the watcher.py script
    itself and triggering a self-restart when changes are detected. This allows
    the script to be updated while running, ensuring that new functionality is
    immediately available without manual intervention.

    Attributes:
        Inherits all attributes from BaseWatcher

    Methods:
        script_callback: Callback function executed when the script file changes
    """

    def __init__(self, script_path):
        """
        Initialize a new ScriptWatcher.

        Args:
            script_path (str): Path to the script file to monitor (usually __file__)
        """
        # We only want to watch the script file itself.
        file_mapping = {os.path.abspath(script_path): "Script File"}
        super().__init__(file_mapping, self.script_callback)

    def script_callback(self, file_key):
        """
        Process updates to the script file.

        This callback is triggered when the script file itself is modified.
        It triggers a self-restart of the script to ensure the new version
        is running.

        Args:
            file_key (str): Identifier of the file that was modified
                (always "Script File" for this watcher)
        """
        logger.info(f"Detected change in {file_key}. Restarting the script...")
        time.sleep(1)  # Allow time for the file write to complete.
        restart_program()


def run_observer(observer: Observer):
    """
    Run a watchdog Observer in a blocking manner.

    This helper function starts an Observer and blocks until the Observer
    is stopped. It's typically used to run Observers in separate threads.

    Args:
        observer (Observer): The watchdog Observer to run

    Note:
        This function is blocking and will not return until the Observer
        is stopped. It should typically be run in a separate thread.
    """
    observer.start()
    observer.join()


def main():
    """Main function to handle arguments and execute appropriate actions"""
    try:
        detect_ide_environment()

        # Handle setup action first
        if ARGS.setup:
            logger.info("Setting up project...")
            setup_project()
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
                    logger.exception(f"Failed to initialize git manager: {e}")
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
                logger.exception(f"Git action failed: {e}")
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
            script_observer.schedule(
                script_watcher, os.path.dirname(os.path.abspath(__file__)), recursive=False
            )

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


def save_rules(context_content: str) -> None:
    """
    Save rules content to the appropriate file based on IDE environment.

    Args:
        context_content: The content to save to the rules file
    """
    try:
        # Save to context rules file
        save_context_rules(context_content)
        # Also save to global rules if needed
        save_global_rules(context_content)
        logger.info("Rules saved successfully")
    except Exception as e:
        logger.exception(f"Failed to save rules: {e}")


# Add new function to manage tasks
def manage_task(action: str, **kwargs):
    """Manage tasks based on the provided action and arguments."""
    from erasmus.utils.paths import SetupPaths

    setup_paths = SetupPaths.with_project_root(Path.cwd())
    rules_file = setup_paths.rules_file

    try:
        # Load existing tasks from context
        context = read_context_file()
        task_manager = TaskManager.from_dict(context.get("tasks", {}))

        if action == "add":
            if not kwargs.get("description"):
                return {"error": "Task description is required"}
            task = task_manager.add_task(kwargs["description"])
            context["tasks"] = task_manager.to_dict()
            write_context_file(context)
            sys.stderr.write(f"\nTask added to {rules_file}\n")
            return task

        elif action == "list":
            status = kwargs.get("status")
            if status:
                status = TaskStatus(status)
            return task_manager.list_tasks(status)

        elif action == "update":
            if not kwargs.get("task_id"):
                return {"error": "Task ID is required"}
            if not kwargs.get("status"):
                return {"error": "Task status is required"}
            task_manager.update_task_status(kwargs["task_id"], TaskStatus(kwargs["status"]))
            context["tasks"] = task_manager.to_dict()
            write_context_file(context)
            sys.stderr.write(f"\nTask status updated in {rules_file}\n")
            return task_manager.get_task(kwargs["task_id"])

        elif action == "note":
            if not kwargs.get("task_id"):
                return {"error": "Task ID is required"}
            if not kwargs.get("note"):
                return {"error": "Note content is required"}
            task_manager.add_note_to_task(kwargs["task_id"], kwargs["note"])
            context["tasks"] = task_manager.to_dict()
            write_context_file(context)
            return task_manager.get_task(kwargs["task_id"])

        else:
            return {"error": f"Unknown task action: {action}"}

    except Exception as e:
        logger.exception(f"Error managing task: {e}")
        return {"error": str(e)}


def read_context_file() -> dict:
    """Read the context file"""
    try:
        if os.path.exists(CONTEXT_RULES_PATH):
            with open(CONTEXT_RULES_PATH) as f:
                context = json.load(f)
                if "tasks" not in context:
                    context["tasks"] = {}
                return context
    except Exception as e:
        logger.exception(f"Error reading existing context: {e}")
    return {
        "tasks": {},
        "repo_path": str(Path.cwd()),
        "git_manager": None,
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
        logger.exception(f"Error writing context file: {e}")


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

    for line in content.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return ""


SETUP_FILES = {
    "architecture": Path(".erasmus/.architecture.md").resolve(),
    "progress": Path(".progress.md").resolve(),
    "tasks": Path(".tasks.md").resolve(),
}

architecture_PATH = SETUP_FILES["architecture"]
progress_PATH = SETUP_FILES["progress"]
tasks_PATH = SETUP_FILES["tasks"]


def safe_read_file(file_path):
    """Safely read a file with proper error handling"""
    error_message = {
        architecture_PATH: "architecture file not found. Please ask the user for requirements to create it.",
        progress_PATH: "progress file not found. Please generate from .erasmus/.architecture.md",
        tasks_PATH: "tasks file not found. Please generate from .progress.md",
    }
    msg = ""
    try:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        msg = error_message.get(file_path, f"File not found: {file_path}")
        logger.warning(msg)
        return msg
    except Exception as e:
        msg = f"Error reading file {file_path}: {e}"
        logger.exception(msg)
        return msg


def safe_write_file(file_path, content):
    """Safely write to a file with proper error handling"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"File written successfully: {file_path}")
        return True
    except Exception as e:
        logger.exception(f"Error writing to file {file_path}: {e}")
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
        logger.exception(f"Failed to create {file_path}: {e}")
        return False


if __name__ == "__main__":
    sys.exit(main())
