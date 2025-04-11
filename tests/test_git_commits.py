"""Tests for git commit message generation functionality."""
import os
from unittest.mock import MagicMock, patch

import pytest

from erasmus.utils.context import (
    check_creds,
    determine_commit_type,
    extract_commit_message,
    make_atomic_commit,
)


@pytest.fixture
def mock_env_vars():
    """Fixture to set up environment variables."""
    original_env = dict(os.environ)
    yield os.environ
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def mock_git_manager():
    """Fixture to mock GitManager."""
    with patch('erasmus.utils.context.GitManager') as mock:
        instance = mock.return_value
        instance.stage_all_changes.return_value = True
        instance.commit_changes.return_value = True
        instance.validate_commit_message.return_value = (True, "Valid message")
        yield instance

@pytest.fixture
def mock_subprocess():
    """Fixture to mock subprocess calls."""
    with patch('erasmus.utils.context.subprocess') as mock:
        mock.check_output.return_value = (
            "diff --git a/src/utils/context.py b/src/utils/context.py\n"
            "index 1234567..89abcdef 100644\n"
            "--- a/src/utils/context.py\n"
            "+++ b/src/utils/context.py\n"
            "@@ -1,3 +1,4 @@\n"
            "+\"\"\"Added docstring.\"\"\"\n"
            " def test_function():\n"
            "     pass\n"
        )
        yield mock

def test_check_creds_with_default_key(mock_env_vars):
    """Test check_creds with default API key."""
    mock_env_vars["OPENAI_API_KEY"] = "sk-1234"
    mock_env_vars["OPENAI_BASE_URL"] = "http://localhost:1234"
    assert not check_creds()

def test_check_creds_with_openai_url(mock_env_vars):
    """Test check_creds with OpenAI base URL."""
    mock_env_vars["OPENAI_API_KEY"] = "sk-real-key"
    mock_env_vars["OPENAI_BASE_URL"] = "https://api.openai.com/v1"
    assert not check_creds()

def test_check_creds_with_custom_creds(mock_env_vars):
    """Test check_creds with custom credentials."""
    mock_env_vars["OPENAI_API_KEY"] = "sk-real-key"
    mock_env_vars["OPENAI_BASE_URL"] = "http://localhost:1234"
    assert check_creds()

def test_determine_commit_type_test():
    """Test determine_commit_type with test changes."""
    diff = "diff --git a/tests/test_file.py b/tests/test_file.py\nAdded new test case"
    assert determine_commit_type(diff) == "test"

def test_determine_commit_type_fix():
    """Test determine_commit_type with bug fix."""
    diff = "diff --git a/src/bug.py b/src/bug.py\nFixed critical error"
    assert determine_commit_type(diff) == "fix"

def test_determine_commit_type_docs():
    """Test determine_commit_type with documentation."""
    diff = "diff --git a/README.md b/README.md\nUpdated documentation"
    assert determine_commit_type(diff) == "docs"

def test_determine_commit_type_default():
    """Test determine_commit_type with unspecified type."""
    diff = "diff --git a/src/file.py b/src/file.py\nSome changes"
    assert determine_commit_type(diff) == "chore"

def test_extract_commit_message_simple():
    """Test extract_commit_message with simple message."""
    message = "feat: add new feature"
    assert extract_commit_message(message) == "feat: add new feature"

def test_extract_commit_message_multiline():
    """Test extract_commit_message with multiline message."""
    message = 'feat: add new feature\n\nDetailed description'
    assert extract_commit_message(message) == "feat: add new feature"

def test_extract_commit_message_long():
    """Test extract_commit_message with long message."""
    message = "feat: " + "x" * 100
    result = extract_commit_message(message)
    assert len(result) <= 72
    assert result.endswith("...")

def test_make_atomic_commit_openai_success(mock_env_vars, mock_git_manager, mock_subprocess):
    """Test successful commit with OpenAI generation."""
    mock_env_vars["OPENAI_API_KEY"] = "sk-real-key"
    mock_env_vars["OPENAI_BASE_URL"] = "http://localhost:1234"

    with patch('erasmus.utils.context.CLIENT') as mock_client:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "feat: add new feature"
        mock_client.chat.completions.create.return_value = mock_response

        assert make_atomic_commit()
        mock_git_manager.commit_changes.assert_called_once()

def test_make_atomic_commit_fallback(mock_env_vars, mock_git_manager, mock_subprocess):
    """Test commit with fallback message generation."""
    mock_env_vars["OPENAI_API_KEY"] = "sk-1234"
    mock_env_vars["OPENAI_BASE_URL"] = "https://api.openai.com/v1"

    assert make_atomic_commit()
    mock_git_manager.commit_changes.assert_called_once()
    # Verify the commit message contains the file name from the diff
    args = mock_git_manager.commit_changes.call_args[0]
    assert "context.py" in args[0]

def test_make_atomic_commit_no_changes(mock_git_manager):
    """Test commit when there are no changes to commit."""
    mock_git_manager.stage_all_changes.return_value = False
    assert not make_atomic_commit()
    mock_git_manager.commit_changes.assert_not_called()

def test_make_atomic_commit_invalid_message(mock_env_vars, mock_git_manager, mock_subprocess):
    """Test commit with invalid message validation."""
    mock_env_vars["OPENAI_API_KEY"] = "sk-real-key"
    mock_env_vars["OPENAI_BASE_URL"] = "http://localhost:1234"
    mock_git_manager.validate_commit_message.return_value = (False, "Invalid message")

    assert make_atomic_commit()
    mock_git_manager.commit_changes.assert_called_once()
    # Verify fallback to default message format
    args = mock_git_manager.commit_changes.call_args[0]
    assert "Update project files" in args[0]
