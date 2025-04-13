"""Context management utilities for Erasmus."""

import json
import shutil
import subprocess
import time
import asyncio
from pathlib import Path
from typing import Any, Dict

from rich import console

from erasmus.git.manager import GitManager
from erasmus.utils.logging import LogContext, get_logger, log_execution
from erasmus.utils.paths import SetupPaths
from erasmus.utils.protocols.manager import ProtocolManager
from erasmus.utils.protocols import Protocol
from erasmus.utils.protocols.context import Context

# Configure logging
logger = get_logger(__name__)

# Global variables
PWD = Path(__file__).parent
CLIENT = None
OPENAI_MODEL = None
PROJECT_MARKER = f"""
{"=" * 40}
## Current Project:
{"=" * 40}
"""


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
    first_line = message.split("\n")[0].strip()

    # Remove any quotes that might have been added
    first_line = first_line.strip("\"'")

    # Truncate if too long
    if len(first_line) > 72:
        first_line = first_line[:69] + "..."

    return first_line


def determine_commit_type(diff_output: str) -> str:
    """Determine the commit type based on the diff content."""
    diff_lower = diff_output.lower()

    # Define patterns for different commit types
    patterns = {
        "test": ["test", "spec", "_test.py", "pytest"],
        "fix": ["fix", "bug", "error", "issue", "crash", "problem"],
        "docs": ["docs", "documentation", "readme", "comment"],
        "style": ["style", "format", "lint", "pretty", "whitespace"],
        "refactor": ["refactor", "restructure", "cleanup", "clean up", "simplify"],
        "feat": ["feat", "feature", "add", "new", "implement"],
    }

    # Check each pattern
    for commit_type, keywords in patterns.items():
        if any(keyword in diff_lower for keyword in keywords):
            return commit_type

    # Default to chore
    return "chore"


console = console.Console()

# Define ASCII character limit constant
ASCII_CHAR_LIMIT = 128


def scrub_non_ascii(text: str) -> str:
    """Remove non-standard ASCII characters from text.

    Args:
        text: The text to scrub

    Returns:
        str: The text with only standard ASCII characters
    """
    return "".join(char for char in text if ord(char) < ASCII_CHAR_LIMIT)


class ProcessError(Exception):
    """Exception raised when a process fails."""


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

    # Add architecture if available
    architecture_path = setup_paths.markdown_files["architecture"]
    if architecture_path.exists():
        context["architecture"] = read_file(architecture_path)

    # Add progress if available
    progress_path = setup_paths.markdown_files["progress"]
    if progress_path.exists():
        context["progress"] = read_file(progress_path)

    # Add tasks if available
    tasks_path = setup_paths.markdown_files["tasks"]
    if tasks_path.exists():
        context["tasks"] = read_file(tasks_path)

    # Handle protocol context if a protocol is active
    if "current_protocol" in context:
        success = handle_protocol_context(setup_paths, context["current_protocol"])
        if not success:
            logger.warning(f"Failed to update protocol context for {context['current_protocol']}")

    # Scrub non-ASCII characters only when writing to rules files
    scrubbed_context = {
        key: scrub_non_ascii(value) if isinstance(value, str) else value
        for key, value in context.items()
    }

    # Get the correct rules file path based on IDE environment
    rules_context_path = setup_paths.rules_file

    # Write updated context
    if rules_context_path.exists():
        write_file(rules_context_path, json.dumps(scrubbed_context, indent=2), backup=backup)
    return context


def setup_project() -> None:
    """Set up a new project with necessary files."""
    # Import logging here to avoid circular imports
    from erasmus.utils.logging import get_logger

    logger = get_logger(__name__)

    # Make sure .env is loaded
    from dotenv import load_dotenv

    load_dotenv()

    # Check IDE environment before creating SetupPaths
    import os

    ide_env = os.getenv("IDE_ENV", "").lower()
    logger.info(f"Setup project detected IDE environment: '{ide_env}'")

    setup_paths = SetupPaths.with_project_root(Path.cwd())

    # Create required files
    files = {
        str(
            setup_paths.markdown_files["architecture"]
        ): "# Project architecture\n\nDescribe your project architecture here.",
        str(
            setup_paths.markdown_files["progress"]
        ): "# Development progress\n\nTrack your development progress here.",
        str(
            setup_paths.markdown_files["tasks"]
        ): "# Project tasks\n\nList your project tasks here.",
        ".env.example": "IDE_ENV=\nOPENAI_API_KEY=\nOPENAI_BASE_URL=\nOPENAI_MODEL=",
        ".gitignore": ".env\n__pycache__/\n*.pyc\n.pytest_cache/\n",
    }

    # Add script files
    for script_name, script_path in setup_paths.script_files.items():
        files[str(script_path)] = f"""#!/usr/bin/env python3
# {script_name} script

def main():
    # Add your {script_name} commands here
    print(f"Running {script_name} script...")

if __name__ == "__main__":
    main()
"""

    # Try to restore from backup first
    if not restore_rules_backup():
        # If no backup, create new files
        for filename, content in files.items():
            path = Path(filename)
            if not path.exists():
                write_file(path, content)
                console.print(f"Created {filename}")

                # Make script files executable
                if filename in [str(p) for p in setup_paths.script_files.values()]:
                    path.chmod(0o755)

        # Initialize context with file contents
        context = {}

        # Get the correct rules path based on IDE environment
        rules_path = setup_paths.rules_file

        # Read content from files
        markdown_files = {
            "architecture": setup_paths.markdown_files["architecture"],
            "progress": setup_paths.markdown_files["progress"],
            "tasks": setup_paths.markdown_files["tasks"],
        }

        for file_key, file_path in markdown_files.items():
            if file_path.exists():
                context[file_key] = read_file(file_path)

        # Write to the correct rules file
        write_file(rules_path, json.dumps(context, indent=2), backup=True)

    console.print("Project setup complete!")


@log_execution()
def update_specific_file(file_type: str, content: str | None = None) -> None:
    """Update a specific project file."""
    with LogContext(logger, f"update_specific_file({file_type})"):
        setup_paths = SetupPaths.with_project_root(Path.cwd())
        file_map = setup_paths.markdown_files
        # Get available file types from the MarkdownPaths object
        available_types = ["architecture", "progress", "tasks"]
        logger.debug(f"Available file types: {available_types}")

        if file_type not in available_types:
            logger.error(f"Invalid file type: {file_type}")
            console.print(f"Invalid file type: {file_type}", style="red")
            return

        # Access the path attribute directly based on the file_type
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
                                logger.debug(
                                    f"Read existing context: {list(current_context.keys())}"
                                )
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
            rules_path,
        ]
        files_to_rm_string = [str(path) for path in files_to_remove]
        files_to_rm_string.append(".env")
        logger.debug(f"Files to clean up: {files_to_rm_string}")

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
                encoding="utf-8",
                errors="replace",  # Replace undecodable bytes
            )

            # Truncate diff if it's too long
            max_diff_length = 4000
            original_length = len(diff_output)
            if original_length > max_diff_length:
                diff_output = diff_output[:max_diff_length] + "... (diff truncated)"
                logger.debug("Truncated diff from %s to %s chars", original_length, max_diff_length)

            # Sanitize diff output
            diff_output = "".join(char for char in diff_output if ord(char) < ASCII_CHAR_LIMIT)
            logger.debug("Sanitized diff output, final length: %s", len(diff_output))

        except Exception as e:
            logger.exception("Failed to get diff output")
            raise ProcessError("Failed to get diff output") from e

        # Determine commit type programmatically
        commit_type = determine_commit_type(diff_output)
        logger.debug("Determined commit type: %s", commit_type)

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
                logger.debug("Making API request with model: %s", OPENAI_MODEL)
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
                commit_message = "".join(
                    char for char in raw_message if ord(char) < ASCII_CHAR_LIMIT
                )
                logger.debug("Raw commit message: %s", raw_message)

                # Ensure commit message starts with the determined type
                if not commit_message.startswith(f"{commit_type}:"):
                    logger.debug("Adding commit type prefix")
                    commit_message = f"{commit_type}: {commit_message}"

                commit_message = extract_commit_message(commit_message)
                logger.info("Generated commit message via API: %s", commit_message)
            except Exception as e:
                logger.warning("Failed to generate commit message via API", exc_info=True)
                commit_message = None
        else:
            logger.debug("Skipping OpenAI commit message generation")
            commit_message = None

        # If we don't have a commit message, generate one from the diff
        if not commit_message:
            logger.debug("Generating commit message from diff")
            # Get the first line of the diff that shows a file change
            diff_lines = diff_output.split("\n")
            file_change = next((line for line in diff_lines if line.startswith("diff --git")), "")
            if file_change:
                # Extract the file name from the diff line
                file_name = file_change.split(" b/")[-1]
                logger.debug("Found changed file: %s", file_name)
            else:
                file_name = "project files"
                logger.debug("No specific file changes found")

            # Create a simple commit message based on the type and changed files
            commit_message = f"{commit_type}: Update {file_name}"
            logger.info("Generated fallback commit message: %s", commit_message)

        # Validate commit message
        is_valid, validation_message = git_manager.validate_commit_message(commit_message)
        logger.debug("Commit message validation: %s", validation_message)

        if not is_valid:
            logger.warning("Generated commit message invalid: %s", validation_message)
            commit_message = f"{commit_type}: Update project files ({time.strftime('%Y-%m-%d')})"
            logger.info("Using default commit message: %s", commit_message)

        # Commit changes
        if git_manager.commit_changes(commit_message):
            logger.info("Successfully committed changes: %s", commit_message)
            return True
        logger.error("Failed to commit changes")
        return False


def store_context(setup_paths: SetupPaths) -> bool:
    """Store the current context in the context directory.

    Args:
        setup_paths: The setup paths object containing file paths

    Returns:
        bool: True if context was stored successfully, False otherwise
    """
    import shutil

    try:
        context_dir = setup_paths.stored_context
        if not context_dir.exists():
            context_dir.mkdir(parents=True, exist_ok=True)

        # Get the markdown files from the root directory
        progress_file = setup_paths.markdown_files["progress"]
        tasks_file = setup_paths.markdown_files["tasks"]
        architecture_file = setup_paths.markdown_files["architecture"]

        # Ensure architecture file exists and has content
        if not architecture_file.exists() or not architecture_file.read_text().strip():
            logger.error("Architecture file is empty or does not exist")
            return False

        architecture_content = architecture_file.read_text().splitlines()
        # Get the first line and sanitize it for use as a directory name
        raw_title = architecture_content[0].strip("#").strip()

        # Replace illegal characters for file paths
        # Windows disallows: < > : " / \ | ? *
        # Unix systems disallow: /
        # Also replace spaces with underscores for better readability
        illegal_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*", " "]
        architecture_title = raw_title
        for char in illegal_chars:
            architecture_title = architecture_title.replace(char, "_")

        # Remove any leading/trailing underscores or dots
        architecture_title = architecture_title.strip("_.")

        if not architecture_title:
            architecture_title = "unnamed_project"

        architecture_context_dir = context_dir / architecture_title
        if not architecture_context_dir.exists():
            architecture_context_dir.mkdir(parents=True, exist_ok=True)

        # Copy files to context directory preserving original content
        write_file(architecture_context_dir / "architecture.md", architecture_file.read_text())
        write_file(architecture_context_dir / "progress.md", progress_file.read_text())
        write_file(architecture_context_dir / "tasks.md", tasks_file.read_text())

        # Clear original files if needed
        architecture_file.write_text("")
        progress_file.write_text("")
        tasks_file.write_text("")

        logger.info("Context stored successfully in %s", architecture_context_dir)
        return True
    except Exception:
        logger.exception("Failed to store context")
        return False


def handle_agent_context(setup_paths: SetupPaths, context: str) -> bool:
    """Handles agent context"""
    if not context.lower().strip("# ").startswith("agent"):
        return context
    current_architecture = setup_paths.markdown_files["architecture"].read_text()
    if current_architecture.strip("# ").startswith("project"):
        context += PROJECT_MARKER
        context += current_architecture

    return context


def restore_context(setup_paths: SetupPaths, architecture_context_dir: Path) -> bool:
    """Restore the context from the context directory.

    Args:
        setup_paths: The setup paths object containing file paths
        architecture_context_dir: The context directory to restore from

    Returns:
        bool: True if context was restored successfully, False otherwise
    """
    import shutil

    try:
        if not architecture_context_dir.exists():
            logger.error("Context directory does not exist: %s", architecture_context_dir)
            return False

        architecture_file = architecture_context_dir / "architecture.md"
        progress_file = architecture_context_dir / "progress.md"
        tasks_file = architecture_context_dir / "tasks.md"

        # Check if all required files exist
        missing_files = []
        if not architecture_file.exists():
            missing_files.append("architecture.md")
        if not progress_file.exists():
            missing_files.append("progress.md")
        if not tasks_file.exists():
            missing_files.append("tasks.md")

        if missing_files:
            logger.error("Missing files in context directory: %s", ", ".join(missing_files))
            return False

        # Copy files to project directory
        shutil.copy2(architecture_file, setup_paths.markdown_files["architecture"])
        shutil.copy2(progress_file, setup_paths.markdown_files["progress"])
        shutil.copy2(tasks_file, setup_paths.markdown_files["tasks"])

        # Update the rules file with the new content
        context = {
            "architecture": read_file(setup_paths.markdown_files["architecture"]),
            "progress": read_file(setup_paths.markdown_files["progress"]),
            "tasks": read_file(setup_paths.markdown_files["tasks"]),
        }

        # Scrub non-ASCII characters only when writing to rules files
        scrubbed_context = {
            key: scrub_non_ascii(value) if isinstance(value, str) else value
            for key, value in context.items()
        }

        # Write updated context to rules file
        write_file(setup_paths.rules_file, json.dumps(scrubbed_context, indent=2))

        logger.info("Context restored successfully from %s", architecture_context_dir)
        return True
    except Exception:
        logger.exception("Failed to restore context")
        return False


def list_context_dirs(setup_paths: SetupPaths) -> list[str]:
    """List all context directories.

    Args:
        setup_paths: The setup paths object containing file paths

    Returns:
        list[str]: List of context directory paths as strings
    """
    try:
        context_dir = setup_paths.stored_context
        if not context_dir.exists():
            logger.debug("Context directory does not exist: %s", context_dir)
            return []

        # Get all directories that contain the required context files
        valid_dirs = []
        for d in context_dir.iterdir():
            files_to_check = ["architecture.md", "progress.md", "tasks.md"]
            if d.is_dir() and all((d / f).exists() for f in files_to_check):
                valid_dirs.append(str(d))

        if not valid_dirs:
            logger.debug("No valid context directories found in %s", context_dir)
            return valid_dirs

        logger.debug("Found %d valid context directories", len(valid_dirs))
        return valid_dirs
    except Exception:
        logger.exception("Error listing context directories")
        return []


def print_context_dirs(setup_paths: SetupPaths) -> None:
    """Print all context directories.

    Args:
        setup_paths: The setup paths object containing file paths
    """
    context_dirs = list_context_dirs(setup_paths)
    if not context_dirs:
        console.print("No context directories found")
        return

    console.print("Available context directories:")
    for i, context_dir in enumerate(context_dirs, 1):
        # Try to extract a more readable name from the path
        dir_name = Path(context_dir).name
        # Get the first line of architecture.md as title if possible
        architecture_file = Path(context_dir) / "architecture.md"
        if architecture_file.exists():
            try:
                with architecture_file.open() as f:
                    first_line = f.readline().strip("#").strip()
                    if first_line:
                        dir_name = f"{dir_name} - {first_line}"
            except Exception:
                pass  # Just use the directory name if we can't read the file

        console.print(f"{i}. {dir_name}")


def select_context_dir(setup_paths: SetupPaths) -> Path | None:
    """Select a context directory.

    Args:
        setup_paths: The setup paths object containing file paths

    Returns:
        Path | None: The selected context directory path, or None if no selection was made
    """
    context_dirs = list_context_dirs(setup_paths)
    if not context_dirs:
        console.print("No context directories found")
        return None

    print_context_dirs(setup_paths)

    while True:
        try:
            prompt = "Enter the number of the context directory to restore (or 'q' to quit): "
            selection_input = console.input(prompt)

            if selection_input.lower() in ("q", "quit", "exit"):
                return None

            try:
                selection = int(selection_input)
                if 1 <= selection <= len(context_dirs):
                    return Path(context_dirs[selection - 1])

                msg = f"Invalid selection. Enter a number between 1 and {len(context_dirs)}."
                console.print(msg)
            except ValueError:
                console.print("Invalid input, please enter a number or 'q' to quit.")
        except KeyboardInterrupt:
            console.print("\nSelection cancelled")
            return None


def handle_protocol_context(setup_paths: SetupPaths, protocol_name: str) -> bool:
    """Handle protocol context updates automatically.

    This function acts as an event handler for protocol state changes,
    automatically updating the context when protocols change state.

    Args:
        setup_paths: The setup paths object containing file paths
        protocol_name: Name of the protocol being activated

    Returns:
        bool: True if context was updated successfully
    """
    try:
        # Get the rules file path
        rules_path = setup_paths.rules_file
        if not rules_path.exists():
            logger.warning("Rules file does not exist, creating new context")
            rules_context = {}
        else:
            with open(rules_path) as f:
                rules_context = json.loads(f.read())

        # Update protocol state in context
        rules_context["current_protocol"] = protocol_name

        # Let the ProtocolManager handle the protocol state
        async def update_protocol_state():
            manager = await ProtocolManager.create()
            protocol = manager.get_protocol(protocol_name)

            if protocol:
                # Update protocol metadata
                rules_context.update(
                    {
                        "protocol_role": protocol.role,
                        "protocol_triggers": protocol.triggers,
                        "protocol_produces": protocol.produces,
                        "protocol_consumes": protocol.consumes,
                    }
                )

                # Load protocol markdown
                protocol_md_path = setup_paths.protocols_dir / "stored" / protocol.file_path.name
                if protocol_md_path.exists():
                    rules_context["protocol_markdown"] = read_file(protocol_md_path)

                # Update available protocols
                rules_context["protocols"] = manager.list_protocols()

                return True
            return False

        success = asyncio.run(update_protocol_state())
        if not success:
            logger.error(f"Failed to update protocol state for {protocol_name}")
            return False

        # Write updated context
        write_file(rules_path, json.dumps(rules_context, indent=2))
        logger.info(f"Successfully updated context for protocol: {protocol_name}")
        return True

    except Exception as e:
        logger.error(f"Error handling protocol context: {e}")
        return False


class ContextManager:
    """Manages the global context for the application."""

    def __init__(self):
        """Initialize the context manager."""
        self.context = Context()
        self.protocol_manager = None
        self._setup_protocol_handlers()

    def _setup_protocol_handlers(self) -> None:
        """Set up handlers for protocol events."""
        if self.protocol_manager:
            self.protocol_manager.register_event_handler(
                "protocol_activated", self._handle_protocol_activated
            )
            self.protocol_manager.register_event_handler(
                "protocol_completed", self._handle_protocol_completed
            )
            self.protocol_manager.register_event_handler(
                "transition_triggered", self._handle_transition
            )
            self.protocol_manager.register_event_handler("artifact_produced", self._handle_artifact)

    async def initialize(self) -> None:
        """Initialize the context manager."""
        self.protocol_manager = await ProtocolManager.create()
        self._setup_protocol_handlers()

    def _handle_protocol_activated(self, protocol: Protocol) -> None:
        """Handle protocol activation event."""
        self.context.active_protocol = protocol.name
        self.context.protocol_state = protocol.initial_state
        logger.info(f"Activated protocol: {protocol.name}")

    def _handle_protocol_completed(self, protocol: Protocol, artifacts: Dict[str, Any]) -> None:
        """Handle protocol completion event."""
        self.context.protocol_artifacts.update(artifacts)
        logger.info(f"Completed protocol: {protocol.name}")

    def _handle_transition(
        self, from_protocol: Protocol, to_protocol: Protocol, trigger: str, artifact: str
    ) -> None:
        """Handle protocol transition event."""
        logger.info(f"Transitioning from {from_protocol.name} to {to_protocol.name}")
        logger.info(f"Trigger: {trigger}, Artifact: {artifact}")

        # Update context for new protocol
        self.context.active_protocol = to_protocol.name
        self.context.protocol_state = to_protocol.initial_state

    def _handle_artifact(self, protocol: Protocol, artifact_name: str, artifact_value: Any) -> None:
        """Handle artifact production event."""
        self.context.protocol_artifacts[artifact_name] = artifact_value
        logger.info(f"Produced artifact {artifact_name} in protocol {protocol.name}")

    async def update_context(self, updates: Dict[str, Any]) -> None:
        """Update the context with new values.

        Args:
            updates: Dictionary of context updates
        """
        # Update context values
        for key, value in updates.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
            else:
                logger.warning(f"Unknown context key: {key}")

        # If we have an active protocol, check for completion
        if self.context.active_protocol and self.protocol_manager:
            protocol = self.protocol_manager.get_protocol(self.context.active_protocol)
            if protocol and protocol.is_complete(self.context.protocol_state):
                await self.protocol_manager.complete_protocol(
                    protocol.name, self.context.protocol_artifacts
                )

    def get_context(self) -> Context:
        """Get the current context."""
        return self.context

    async def select_protocol(self, protocol_name: str) -> bool:
        """Select and activate a protocol.

        Args:
            protocol_name: Name of the protocol to activate

        Returns:
            bool: True if protocol was activated successfully
        """
        if not self.protocol_manager:
            logger.error("Protocol manager not initialized")
            return False

        return await self.protocol_manager.activate_protocol(protocol_name)
