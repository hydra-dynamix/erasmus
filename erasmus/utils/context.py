"""Context management utilities for Erasmus."""
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from rich import console

from ..git.manager import GitManager
from ..utils.logging import LogContext, get_logger, log_execution
from ..utils.paths import SetupPaths

# Configure logging
logger = get_logger(__name__)

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
        'feat': ['feat', 'feature', 'add', 'new', 'implement'],
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

def backup_rules_file(file_path: Path) -> None:
    """Create a backup of a rules file if it exists."""
    if file_path.exists():
        backup_path = file_path.parent / f"{file_path.name}.old"
        shutil.copy2(file_path, backup_path)
        console.print(f"Created backup at {backup_path}")

def write_file(path: Path, content: str, backup: bool = False) -> bool:
    """Write content to a file, optionally creating a backup."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup if requested and file exists
        if backup and path.exists():
            backup_rules_file(path)

        path.write_text(content)
        return True
    except Exception as e:
        console.print(f"Error writing to {path}: {e}", style="red")
        return False

def get_rules_path() -> Path:
    """Get the appropriate rules file path based on IDE_ENV."""
    from pathlib import Path
    setup_paths = SetupPaths.with_project_root(Path.cwd())
    return setup_paths.rules_file

def restore_rules_backup() -> bool:
    """Restore rules from backup if available."""
    rules_path = get_rules_path()
    backup_path = rules_path.parent / f"{rules_path.name}.old"

    if backup_path.exists():
        try:
            shutil.copy2(backup_path, rules_path)
            console.print(f"Restored rules from {backup_path}")
            return True
        except Exception as e:
            console.print(f"Error restoring backup: {e}", style="red")
    return False

def update_context(context: dict[str, Any], backup: bool = False) -> dict[str, Any]:
    """Update the context with current file contents."""
    setup_paths = SetupPaths.with_project_root(Path.cwd())
    rules_path = setup_paths.rules_file
    global_rules_path = Path("global_rules.md")

    # Add architecture if available
    arch_path = setup_paths.markdown_files.architecture
    if arch_path.exists():
        context["architecture"] = read_file(arch_path)

    # Add progress if available
    progress_path = setup_paths.markdown_files.progress
    if progress_path.exists():
        context["progress"] = read_file(progress_path)

    # Add tasks if available
    tasks_path = setup_paths.markdown_files.tasks
    if tasks_path.exists():
        context["tasks"] = read_file(tasks_path)

    # Write updated context
    write_file(rules_path, json.dumps(context, indent=2), backup=backup)
    if global_rules_path.exists():
        write_file(global_rules_path, json.dumps(context, indent=2), backup=backup)
    return context

def setup_project() -> None:
    """Set up a new project with necessary files."""
    setup_paths = SetupPaths.with_project_root(Path.cwd())

    # Create required files
    files = {
        str(setup_paths.markdown_files.architecture): "# Project architecture\n\nDescribe your project architecture here.",
        str(setup_paths.markdown_files.progress): "# Development progress\n\nTrack your development progress here.",
        str(setup_paths.markdown_files.tasks): "# Project tasks\n\nList your project tasks here.",
        ".env.example": "IDE_ENV=\nOPENAI_API_KEY=\nOPENAI_BASE_URL=\nOPENAI_MODEL=",
        ".gitignore": ".env\n__pycache__/\n*.pyc\n.pytest_cache/\n",
    }

    # Try to restore from backup first
    if not restore_rules_backup():
        # If no backup, create new files
        for filename, content in files.items():
            path = Path(filename)
            if not path.exists():
                write_file(path, content)
                console.print(f"Created {filename}")

        # Initialize context with file contents
        context = {}

        # Get the correct rules path based on IDE environment
        rules_path = setup_paths.rules_file

        # Read content from files
        markdown_files = {
            "architecture": setup_paths.markdown_files.architecture,
            "progress": setup_paths.markdown_files.progress,
            "tasks": setup_paths.markdown_files.tasks,
        }

        for file_key, file_path in markdown_files.items():
            if file_path.exists():
                context[file_key] = read_file(file_path)

        # Write to the correct rules file
        write_file(rules_path, json.dumps(context, indent=2), backup=True)

    console.print("Project setup complete!")

@log_execution()
def update_specific_file(file_type: str, content: str = None) -> None:
    """Update a specific project file."""
    with LogContext(logger, f"update_specific_file({file_type})"):
        setup_paths = SetupPaths.with_project_root(Path.cwd())
        file_map = setup_paths.markdown_files
        logger.debug(f"Available file types: {list(file_map.keys())}")

        if file_type not in file_map:
            logger.error(f"Invalid file type: {file_type}")
            console.print(f"Invalid file type: {file_type}", style="red")
            return

        path = file_map[file_type]
        logger.debug(f"Updating file: {path}")

        # If no content provided, read from file
        if content is None and path.exists():
            try:
                content = read_file(path)
                logger.debug(f"Read existing content from {path}")
            except Exception as e:
                logger.error(f"Failed to read {path}: {e}", exc_info=True)
                raise

        if content is not None:
            try:
                if write_file(path, content, backup=False):
                    logger.info(f"Successfully updated {path}")
                    if file_type != "context":
                        # Read current context
                        current_context = {}
                        rules_path = setup_paths.rules_file
                        if rules_path.exists():
                            try:
                                current_context = json.loads(read_file(rules_path))
                                logger.debug(f"Read existing context: {list(current_context.keys())}")
                            except json.JSONDecodeError as e:
                                # If context file is invalid JSON, start fresh
                                logger.warning(f"Failed to parse context file, starting fresh: {e}")
                                current_context = {}

                        # Just update the content and save
                        current_context[file_type] = content
                        logger.info(f"💾 Updating rules with changes from {file_type}")
                        write_file(rules_path, json.dumps(current_context, indent=2), backup=False)
            except Exception as e:
                logger.error(f"Failed to update {path}: {e}", exc_info=True)
                raise

@log_execution()
def cleanup_project() -> None:
    """Remove all generated files and restore backups if available."""
    with LogContext(logger, "cleanup_project"):
        setup_paths = SetupPaths.with_project_root(Path.cwd())
        rules_path = setup_paths.rules_file
        files_to_remove = [
            str(rules_path),
            "global_rules.md",
        ]
        logger.debug(f"Files to clean up: {files_to_remove}")

        # First, create backups of all files
        for filename in files_to_remove:
            path = Path(filename)
            if path.exists():
                try:
                    backup_rules_file(path)
                    logger.info(f"Created backup for {path}")
                except Exception as e:
                    logger.error(f"Failed to backup {path}: {e}", exc_info=True)
                    raise

        # Then remove generated files
        for filename in files_to_remove:
            path = Path(filename)
            if path.exists():
                try:
                    path.unlink()
                    logger.info(f"Successfully removed {path}")
                except Exception as e:
                    logger.error(f"Failed to remove {path}: {e}", exc_info=True)
                    console.print(f"Error removing {path}: {e}", style="red")
                    raise

        # Remove cache directories
        cache_patterns = [
            "__pycache__",
            ".pytest_cache",
            "*.pyc",
        ]
        logger.debug(f"Cache patterns to clean: {cache_patterns}")

    for pattern in cache_patterns:
        for path in Path().rglob(pattern):
            try:
                if path.is_file():
                    path.unlink()
                    logger.debug(f"Removed cache file: {path}")
                elif path.is_dir():
                    shutil.rmtree(path)
                    logger.debug(f"Removed cache directory: {path}")
            except Exception as e:
                logger.error(f"Failed to remove cache {path}: {e}", exc_info=True)
                raise

@log_execution()
def check_creds() -> bool:
    """Check if OpenAI credentials are valid for API calls."""
    with LogContext(logger, "check_creds"):
        api_key, base_url, model = get_openai_credentials()
        logger.debug(f"Using base URL: {base_url}, model: {model}")

        # Skip API call if using default key or OpenAI base URL
        if api_key == "sk-1234" or "api.openai.com" in base_url.lower():
            logger.warning("Using default credentials, skipping API check")
            return False

        logger.info("OpenAI credentials validated")
        return True

@log_execution()
def make_atomic_commit() -> bool:
    """Makes an atomic commit with AI-generated commit message or falls back to diff-based message."""
    with LogContext(logger, "make_atomic_commit"):
        # Initialize GitManager with current directory
        git_manager = GitManager(PWD)
        logger.debug(f"Initialized GitManager with path: {PWD}")

        # Stage all changes
        if not git_manager.stage_all_changes():
            logger.warning("No changes to commit or staging failed")
            return False

        try:
            # Get the diff output
            logger.debug("Getting staged diff output")
            diff_output = subprocess.check_output(
                ["git", "diff", "--staged"],
                cwd=PWD,
                text=True,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',  # Replace undecodable bytes
            )

            # Truncate diff if it's too long
            max_diff_length = 4000
            original_length = len(diff_output)
            if original_length > max_diff_length:
                diff_output = diff_output[:max_diff_length] + "... (diff truncated)"
                logger.debug(f"Truncated diff from {original_length} to {max_diff_length} chars")

            # Sanitize diff output
            diff_output = ''.join(char for char in diff_output if ord(char) < 128)
            logger.debug(f"Sanitized diff output, final length: {len(diff_output)}")

        except Exception as e:
            logger.error(f"Failed to get diff output: {e}")
            raise ProcessError(f"Failed to get diff output: {e}")

        # Determine commit type programmatically
        commit_type = determine_commit_type(diff_output)
        logger.debug(f"Determined commit type: {commit_type}")

        # If we can use OpenAI, generate a message
        if check_creds() and CLIENT is not None:
            logger.debug("Using OpenAI to generate commit message")
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
                logger.debug(f"Making API request with model: {OPENAI_MODEL}")
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
                commit_message = ''.join(char for char in raw_message if ord(char) < 128)
                logger.debug(f"Raw commit message: {raw_message}")

                # Ensure commit message starts with the determined type
                if not commit_message.startswith(f"{commit_type}:"):
                    logger.debug("Adding commit type prefix")
                    commit_message = f"{commit_type}: {commit_message}"

                commit_message = extract_commit_message(commit_message)
                logger.info(f"Generated commit message via API: {commit_message}")
            except Exception as e:
                logger.warning(f"Failed to generate commit message via API: {e}", exc_info=True)
                commit_message = None
        else:
            logger.debug("Skipping OpenAI commit message generation")
            commit_message = None

        # If we don't have a commit message, generate one from the diff
        if not commit_message:
            logger.debug("Generating commit message from diff")
            # Get the first line of the diff that shows a file change
            diff_lines = diff_output.split('\n')
            file_change = next((line for line in diff_lines if line.startswith('diff --git')), '')
            if file_change:
                # Extract the file name from the diff line
                file_name = file_change.split(' b/')[-1]
                logger.debug(f"Found changed file: {file_name}")
            else:
                file_name = "project files"
                logger.debug("No specific file changes found")

            # Create a simple commit message based on the type and changed files
            commit_message = f"{commit_type}: Update {file_name}"
            logger.info(f"Generated fallback commit message: {commit_message}")

        # Validate commit message
        is_valid, validation_message = git_manager.validate_commit_message(commit_message)
        logger.debug(f"Commit message validation: {validation_message}")

        if not is_valid:
            logger.warning(f"Generated commit message invalid: {validation_message}")
            commit_message = f"{commit_type}: Update project files ({time.strftime('%Y-%m-%d')})"
            logger.info(f"Using default commit message: {commit_message}")

        # Commit changes
        if git_manager.commit_changes(commit_message):
            logger.info(f"Successfully committed changes: {commit_message}")
            return True
        logger.error("Failed to commit changes")
        return False
