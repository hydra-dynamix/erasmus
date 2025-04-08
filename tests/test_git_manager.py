"""Tests for GitManager class functionality."""
import subprocess
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from erasmus.git.manager import GitManager

@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls."""
    with patch('erasmus.git.manager.subprocess') as mock:
        mock.CalledProcessError = subprocess.CalledProcessError
        mock.run.return_value = MagicMock(
            stdout="test output",
            stderr="",
            returncode=0
        )
        yield mock

@pytest.fixture
def git_manager(temp_dir):
    """Create a GitManager instance with a temporary directory."""
    return GitManager(temp_dir)

def test_init_new_repo(git_manager, mock_subprocess):
    """Test initializing a new git repository."""
    # Mock that it's not a git repo initially
    mock_subprocess.run.side_effect = [
        subprocess.CalledProcessError(1, "git rev-parse"),  # Not a git repo
        MagicMock(returncode=0),  # git init succeeds
        MagicMock(returncode=0),  # git config user.name succeeds
        MagicMock(returncode=0),  # git config user.email succeeds
    ]
    
    # Create new instance to trigger initialization
    GitManager(git_manager.repo_path)
    
    # Verify git init was called
    init_call = mock_subprocess.run.call_args_list[1]
    assert init_call[0][0] == ["git", "init"]

def test_init_existing_repo(git_manager, mock_subprocess):
    """Test initializing with existing git repository."""
    # Mock that it's already a git repo
    mock_subprocess.run.return_value = MagicMock(returncode=0)
    
    # Create new instance
    GitManager(git_manager.repo_path)
    
    # Verify only the check was made, no init
    assert mock_subprocess.run.call_count == 1
    check_call = mock_subprocess.run.call_args
    assert check_call[0][0] == ["git", "rev-parse", "--is-inside-work-tree"]

def test_stage_all_changes(git_manager, mock_subprocess):
    """Test staging all changes."""
    assert git_manager.stage_all_changes()
    
    # Verify git add was called
    add_call = mock_subprocess.run.call_args
    assert add_call[0][0] == ["git", "add", "-A"]

def test_stage_all_changes_failure(git_manager, mock_subprocess):
    """Test staging changes with failure."""
    mock_subprocess.run.side_effect = subprocess.CalledProcessError(1, "git add")
    assert not git_manager.stage_all_changes()

def test_commit_changes(git_manager, mock_subprocess):
    """Test committing changes."""
    message = "test commit"
    assert git_manager.commit_changes(message)
    
    # Verify git commit was called with message
    commit_call = mock_subprocess.run.call_args
    assert commit_call[0][0] == ["git", "commit", "-m", message]

def test_commit_changes_failure(git_manager, mock_subprocess):
    """Test commit with failure."""
    mock_subprocess.run.side_effect = subprocess.CalledProcessError(1, "git commit")
    assert not git_manager.commit_changes("test commit")

def test_get_repository_state(git_manager, mock_subprocess):
    """Test getting repository state."""
    mock_subprocess.run.side_effect = [
        # branch name
        MagicMock(stdout="main", stderr="", returncode=0),
        # status
        MagicMock(
            stdout=(
                "M  modified.py\n"
                " M unstaged.py\n"
                "?? untracked.py\n"
            ),
            stderr="",
            returncode=0
        )
    ]
    
    state = git_manager.get_repository_state()
    assert state["branch"] == "main"
    assert state["staged"] == ["modified.py"]
    assert state["unstaged"] == ["unstaged.py"]
    assert state["untracked"] == ["untracked.py"]

def test_get_repository_state_failure(git_manager, mock_subprocess):
    """Test repository state with failure."""
    mock_subprocess.run.side_effect = subprocess.CalledProcessError(1, "git status")
    
    state = git_manager.get_repository_state()
    assert state["branch"] == "unknown"
    assert not any([state["staged"], state["unstaged"], state["untracked"]])

def test_get_current_branch(git_manager, mock_subprocess):
    """Test getting current branch name."""
    mock_subprocess.run.return_value = MagicMock(stdout="feature-branch", stderr="")
    assert git_manager.get_current_branch() == "feature-branch"

def test_get_current_branch_failure(git_manager, mock_subprocess):
    """Test getting branch name with failure."""
    mock_subprocess.run.side_effect = subprocess.CalledProcessError(1, "git rev-parse")
    assert git_manager.get_current_branch() == "unknown"

def test_run_git_command(git_manager, mock_subprocess):
    """Test running arbitrary git command."""
    command = ["status", "--porcelain"]
    stdout, stderr = git_manager._run_git_command(command)
    
    # Verify command was called correctly
    run_call = mock_subprocess.run.call_args
    assert run_call[0][0] == ["git"] + command
    assert stdout == "test output"
    assert stderr == ""

def test_run_git_command_failure(git_manager, mock_subprocess):
    """Test git command with failure."""
    mock_subprocess.run.side_effect = subprocess.CalledProcessError(
        1, "git status", stderr="error message"
    )
    stdout, stderr = git_manager._run_git_command(["status"])
    assert stdout == ""
    assert stderr == "error message" 