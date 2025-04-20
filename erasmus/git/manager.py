"""Git operations management for Erasmus."""

import subprocess
from pathlib import Path
from loguru import logger

# Removed: from erasmus.utils.logging import LogContext, log_execution


class GitManager:
    """Manages Git operations for the project."""

    def __init__(self, repo_path: str | Path):
        """Initialize GitManager with a repository path."""
        logger.info("[init] Initializing GitManager")
        self.repo_path = Path(repo_path).resolve()
        logger.debug(f"Initializing GitManager with path: {self.repo_path}")
        if not self._is_git_repo():
            logger.info(f"No git repository found at {self.repo_path}, initializing new repo")
            self._init_git_repo()
        else:
            logger.debug(f"Found existing git repository at {self.repo_path}")

    def _is_git_repo(self) -> bool:
        """Check if the path is a git repository."""
        logger.info("[is_git_repo] Checking if path is a git repository")
        try:
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )
            logger.debug(f"Confirmed git repository at {self.repo_path}")
            return True
        except subprocess.CalledProcessError:
            logger.debug(f"No git repository found at {self.repo_path}")
            return False

    def _init_git_repo(self) -> None:
        """Initialize a new git repository."""
        logger.info("[init_git_repo] Initializing new git repository")
        try:
            logger.debug(f"Initializing new git repository at {self.repo_path}")
            subprocess.run(
                ["git", "init"],
                cwd=self.repo_path,
                check=True,
            )

            # Configure default user
            logger.debug("Configuring default git user")
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
            logger.info(f"Successfully initialized git repository at {self.repo_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to initialize git repository: {e}", exc_info=True)
            raise

    def _run_git_command(self, command: list[str]) -> tuple[str, str]:
        """Run a git command and return stdout and stderr."""
        logger.info(f"[run_git_command] Running git command: {' '.join(command)}")
        try:
            logger.debug(f"Running git command: {' '.join(command)}")
            result = subprocess.run(
                ["git", *command],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            stdout, stderr = result.stdout.strip(), result.stderr.strip()
            if stdout:
                logger.debug(f"Command output: {stdout}")
            if stderr:
                logger.warning(f"Command stderr: {stderr}")
            return stdout, stderr
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Git command failed: {' '.join(command)}",
                exc_info=True,
            )
            return "", e.stderr.strip()

    def stage_all_changes(self) -> bool:
        """Stage all changes in the repository."""
        logger.info("[stage_all_changes] Staging all changes")
        try:
            # Get status before staging
            status_before = self._run_git_command(["status", "--porcelain"])[0]
            logger.debug(f"Files to stage:\n{status_before}")

            # Stage changes
            self._run_git_command(["add", "-A"])

            # Verify staging
            status_after = self._run_git_command(["status", "--porcelain"])[0]
            staged_count = len([line for line in status_after.split("\n") if line.startswith("A ")])
            logger.info(f"Successfully staged {staged_count} changes")
            return True
        except Exception:
            logger.error("Failed to stage changes", exc_info=True)
            return False

    def commit_changes(self, message: str) -> bool:
        """Commit staged changes with a given message."""
        logger.info("[commit_changes] Attempting to commit changes")
        try:
            logger.debug(f"Attempting to commit with message: {message}")

            # First stage any changes
            if not self.stage_all_changes():
                logger.warning("No changes to commit")
                return False

            # Commit changes
            stdout, stderr = self._run_git_command(["commit", "-m", message])
            if stdout:
                logger.info(f"Successfully committed changes: {stdout}")
                return True
            logger.warning("Commit command succeeded but no output received")
            return False
        except Exception:
            logger.error("Failed to commit changes", exc_info=True)
            return False

    def get_repository_state(self) -> dict[str, list[str]]:
        """Get the current state of the repository."""
        logger.info("[get_repository_state] Getting repository state")
        try:
            # Get current branch
            branch = self.get_current_branch()
            logger.debug(f"Current branch: {branch}")

            # Get status
            status_output, _ = self._run_git_command(["status", "--porcelain"])
            status_lines = status_output.split("\n") if status_output else []
            logger.debug(f"Found {len(status_lines)} status lines")

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
                    logger.debug(f"Untracked file: {path}")
                elif status[0] != " ":
                    staged.append(path)
                    logger.debug(f"Staged file: {path}")
                elif status[1] != " ":
                    unstaged.append(path)
                    logger.debug(f"Unstaged file: {path}")

            state = {
                "branch": branch,
                "staged": staged,
                "unstaged": unstaged,
                "untracked": untracked,
            }

            logger.info(
                f"Repository state - Branch: {branch}, "
                + f"Staged: {len(staged)}, "
                + f"Unstaged: {len(unstaged)}, "
                + f"Untracked: {len(untracked)}",
            )
            return state
        except Exception:
            logger.error("Failed to get repository state", exc_info=True)
            state = {
                "branch": "unknown",
                "staged": [],
                "unstaged": [],
                "untracked": [],
            }
            logger.debug("Returning empty repository state")
            return state

    def get_current_branch(self) -> str:
        """Get the name of the current branch."""
        logger.info("[get_current_branch] Getting current branch")
        try:
            branch_output, _ = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
            branch = branch_output.strip()
            logger.debug(f"Current branch: {branch}")
            return branch
        except Exception:
            logger.error("Failed to get current branch", exc_info=True)
            return "unknown"
