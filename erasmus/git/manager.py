"""Git operations management for Erasmus."""
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class GitManager:
    """Manages Git operations for the project."""
    
    def __init__(self, repo_path: str | Path):
        """Initialize GitManager with a repository path."""
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
    
    def _init_git_repo(self) -> None:
        """Initialize a new git repository."""
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
        except Exception as e:
            logger.error(f"Failed to stage changes: {e}")
            return False
    
    def commit_changes(self, message: str) -> bool:
        """Commit staged changes with a given message."""
        try:
            if self.stage_all_changes():
                self._run_git_command(["commit", "-m", message])
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to commit changes: {e}")
            return False
    
    def get_repository_state(self) -> Dict[str, List[str]]:
        """Get the current state of the repository."""
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
                "untracked": untracked
            }
        except Exception as e:
            logger.error(f"Failed to get repository state: {e}")
            return {
                "branch": "unknown",
                "staged": [],
                "unstaged": [],
                "untracked": []
            }
    
    def get_current_branch(self) -> str:
        """Get the name of the current branch."""
        try:
            branch_output, _ = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
            return branch_output.strip()
        except Exception as e:
            logger.error(f"Failed to get current branch: {e}")
            return "unknown"
