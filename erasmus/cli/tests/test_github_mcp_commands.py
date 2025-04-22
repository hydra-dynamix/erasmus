"""
Tests for the GitHub MCP client commands.
"""

import json
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from erasmus.cli.github_mcp_commands import (
    github_app,
    _send_mcp_request,
    create_issue,
    add_comment,
    get_issue,
    list_issues,
    update_issue,
    search_issues,
    get_pr,
    list_prs,
    merge_pr,
    create_pr,
    update_pr,
    get_pr_files,
    get_pr_status,
    create_repo,
    fork_repo,
    get_file,
    create_or_update_file,
    push_files,
    create_branch,
    list_branches,
    list_commits,
    search_repos,
    search_code,
    get_user,
    list_user_repos,
    list_user_orgs,
    get_org,
    list_org_repos,
    list_org_members,
    list_workflows,
    get_workflow,
    list_workflow_runs,
    get_workflow_run,
    rerun_workflow,
    list_releases,
    get_release,
    create_release,
    list_labels,
    get_label,
    create_label,
    update_label,
    delete_label,
    list_milestones,
    get_milestone,
    create_milestone,
    update_milestone,
    delete_milestone,
)

# Mock response for testing
MOCK_RESPONSE = {"id": 123, "title": "Test Issue", "body": "Test Body"}


@pytest.fixture
def mock_mcp_request():
    """Fixture to mock the _send_mcp_request function."""
    with patch("erasmus.cli.github_mcp_commands._send_mcp_request") as mock:
        mock.return_value = MOCK_RESPONSE
        yield mock


@pytest.fixture
def runner():
    """Fixture to create a Typer CLI runner."""
    return CliRunner()


class TestSendMcpRequest:
    """Tests for the _send_mcp_request function."""

    def test_send_mcp_request_success(self):
        """Test successful MCP request."""
        with patch("subprocess.Popen") as mock_popen:
            # Mock the process
            mock_process = MagicMock()
            mock_process.communicate.return_value = (json.dumps({"result": MOCK_RESPONSE}), "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            # Call the function
            result = _send_mcp_request("test_method", {"param": "value"})

            # Verify the result
            assert result == MOCK_RESPONSE

            # Verify the process was called correctly
            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args
            assert args[0] == ["github-mcp-server", "stdio"]
            assert kwargs["stdin"] == subprocess.PIPE
            assert kwargs["stdout"] == subprocess.PIPE
            assert kwargs["stderr"] == subprocess.PIPE
            assert kwargs["text"] is True

            # Verify the request was sent correctly
            mock_process.communicate.assert_called_once()
            request = json.loads(mock_process.communicate.call_args[0][0])
            assert request["jsonrpc"] == "2.0"
            assert request["id"] == 1
            assert request["method"] == "test_method"
            assert request["params"] == {"param": "value"}

    def test_send_mcp_request_error(self):
        """Test MCP request with error response."""
        with patch("subprocess.Popen") as mock_popen:
            # Mock the process
            mock_process = MagicMock()
            mock_process.communicate.return_value = (
                json.dumps({"error": {"message": "Test error"}}),
                "",
            )
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            # Call the function and expect an exception
            with pytest.raises(Exception):
                _send_mcp_request("test_method", {"param": "value"})

    def test_send_mcp_request_process_error(self):
        """Test MCP request with process error."""
        with patch("subprocess.Popen") as mock_popen:
            # Mock the process
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "Process error")
            mock_process.returncode = 1
            mock_popen.return_value = mock_process

            # Call the function and expect an exception
            with pytest.raises(Exception):
                _send_mcp_request("test_method", {"param": "value"})


class TestIssueCommands:
    """Tests for issue-related commands."""

    def test_create_issue(self, mock_mcp_request, runner):
        """Test create_issue command."""
        # Run the command
        result = runner.invoke(
            github_app, ["create-issue", "owner", "repo", "Test Issue", "--body", "Test Body"]
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "create_issue",
            {"owner": "owner", "repo": "repo", "title": "Test Issue", "body": "Test Body"},
        )

    def test_add_comment(self, mock_mcp_request, runner):
        """Test add_comment command."""
        # Run the command
        result = runner.invoke(github_app, ["add-comment", "owner", "repo", "123", "Test Comment"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "add_issue_comment",
            {"owner": "owner", "repo": "repo", "issue_number": 123, "body": "Test Comment"},
        )

    def test_get_issue(self, mock_mcp_request, runner):
        """Test get_issue command."""
        # Run the command
        result = runner.invoke(github_app, ["get-issue", "owner", "repo", "123"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "get_issue", {"owner": "owner", "repo": "repo", "issue_number": 123}
        )

    def test_list_issues(self, mock_mcp_request, runner):
        """Test list_issues command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "list-issues",
                "owner",
                "repo",
                "--state",
                "open",
                "--sort",
                "created",
                "--direction",
                "desc",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "list_issues",
            {
                "owner": "owner",
                "repo": "repo",
                "state": "open",
                "sort": "created",
                "direction": "desc",
            },
        )

    def test_update_issue(self, mock_mcp_request, runner):
        """Test update_issue command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "update-issue",
                "owner",
                "repo",
                "123",
                "--title",
                "Updated Title",
                "--state",
                "closed",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "update_issue",
            {
                "owner": "owner",
                "repo": "repo",
                "issue_number": 123,
                "title": "Updated Title",
                "state": "closed",
            },
        )

    def test_search_issues(self, mock_mcp_request, runner):
        """Test search_issues command."""
        # Run the command
        result = runner.invoke(
            github_app, ["search-issues", "test query", "--sort", "created", "--order", "desc"]
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "search_issues", {"query": "test query", "sort": "created", "order": "desc"}
        )


class TestPullRequestCommands:
    """Tests for pull request-related commands."""

    def test_get_pr(self, mock_mcp_request, runner):
        """Test get_pr command."""
        # Run the command
        result = runner.invoke(github_app, ["get-pr", "owner", "repo", "123"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "get_pull_request", {"owner": "owner", "repo": "repo", "pullNumber": 123}
        )

    def test_list_prs(self, mock_mcp_request, runner):
        """Test list_prs command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "list-prs",
                "owner",
                "repo",
                "--state",
                "open",
                "--sort",
                "created",
                "--direction",
                "desc",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "list_pull_requests",
            {
                "owner": "owner",
                "repo": "repo",
                "state": "open",
                "sort": "created",
                "direction": "desc",
            },
        )

    def test_merge_pr(self, mock_mcp_request, runner):
        """Test merge_pr command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "merge-pr",
                "owner",
                "repo",
                "123",
                "--commit-title",
                "Merge PR",
                "--merge-method",
                "squash",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "merge_pull_request",
            {
                "owner": "owner",
                "repo": "repo",
                "pullNumber": 123,
                "commit_title": "Merge PR",
                "merge_method": "squash",
            },
        )

    def test_create_pr(self, mock_mcp_request, runner):
        """Test create_pr command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "create-pr",
                "owner",
                "repo",
                "Test PR",
                "feature-branch",
                "main",
                "--body",
                "Test Body",
                "--draft",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "create_pull_request",
            {
                "owner": "owner",
                "repo": "repo",
                "title": "Test PR",
                "head": "feature-branch",
                "base": "main",
                "body": "Test Body",
                "draft": True,
            },
        )

    def test_update_pr(self, mock_mcp_request, runner):
        """Test update_pr command."""
        # Run the command
        result = runner.invoke(
            github_app,
            ["update-pr", "owner", "repo", "123", "--title", "Updated Title", "--state", "closed"],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "update_pull_request",
            {
                "owner": "owner",
                "repo": "repo",
                "pullNumber": 123,
                "title": "Updated Title",
                "state": "closed",
            },
        )

    def test_get_pr_files(self, mock_mcp_request, runner):
        """Test get_pr_files command."""
        # Run the command
        result = runner.invoke(github_app, ["get-pr-files", "owner", "repo", "123"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "get_pull_request_files", {"owner": "owner", "repo": "repo", "pullNumber": 123}
        )

    def test_get_pr_status(self, mock_mcp_request, runner):
        """Test get_pr_status command."""
        # Run the command
        result = runner.invoke(github_app, ["get-pr-status", "owner", "repo", "123"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "get_pull_request_status", {"owner": "owner", "repo": "repo", "pullNumber": 123}
        )


class TestRepositoryCommands:
    """Tests for repository-related commands."""

    def test_create_repo(self, mock_mcp_request, runner):
        """Test create_repo command."""
        # Run the command
        result = runner.invoke(
            github_app,
            ["create-repo", "test-repo", "--description", "Test Repo", "--private", "--auto-init"],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "create_repository",
            {"name": "test-repo", "description": "Test Repo", "private": True, "auto_init": True},
        )

    def test_fork_repo(self, mock_mcp_request, runner):
        """Test fork_repo command."""
        # Run the command
        result = runner.invoke(github_app, ["fork-repo", "owner", "repo", "--organization", "org"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "fork_repository", {"owner": "owner", "repo": "repo", "organization": "org"}
        )

    def test_get_file(self, mock_mcp_request, runner):
        """Test get_file command."""
        # Run the command
        result = runner.invoke(
            github_app, ["get-file", "owner", "repo", "path/to/file.py", "--ref", "main"]
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "get_file_contents",
            {"owner": "owner", "repo": "repo", "path": "path/to/file.py", "ref": "main"},
        )

    def test_create_or_update_file(self, mock_mcp_request, runner):
        """Test create_or_update_file command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "create-or-update-file",
                "owner",
                "repo",
                "path/to/file.py",
                "content",
                "commit message",
                "--branch",
                "feature",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "create_or_update_file",
            {
                "owner": "owner",
                "repo": "repo",
                "path": "path/to/file.py",
                "content": "content",
                "message": "commit message",
                "branch": "feature",
            },
        )

    def test_push_files(self, mock_mcp_request, runner):
        """Test push_files command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "push-files",
                "owner",
                "repo",
                "main",
                "commit message",
                "file1.py:content1",
                "file2.py:content2",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "push_files",
            {
                "owner": "owner",
                "repo": "repo",
                "branch": "main",
                "message": "commit message",
                "files": {"file1.py": "content1", "file2.py": "content2"},
            },
        )

    def test_create_branch(self, mock_mcp_request, runner):
        """Test create_branch command."""
        # Run the command
        result = runner.invoke(
            github_app, ["create-branch", "owner", "repo", "feature-branch", "abc123"]
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "create_branch",
            {"owner": "owner", "repo": "repo", "branch": "feature-branch", "sha": "abc123"},
        )

    def test_list_branches(self, mock_mcp_request, runner):
        """Test list_branches command."""
        # Run the command
        result = runner.invoke(github_app, ["list-branches", "owner", "repo", "--protected"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "list_branches", {"owner": "owner", "repo": "repo", "protected": True}
        )

    def test_list_commits(self, mock_mcp_request, runner):
        """Test list_commits command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "list-commits",
                "owner",
                "repo",
                "--sha",
                "main",
                "--author",
                "user",
                "--since",
                "2023-01-01",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "list_commits",
            {
                "owner": "owner",
                "repo": "repo",
                "sha": "main",
                "author": "user",
                "since": "2023-01-01",
            },
        )

    def test_search_repos(self, mock_mcp_request, runner):
        """Test search_repos command."""
        # Run the command
        result = runner.invoke(
            github_app, ["search-repos", "test query", "--sort", "stars", "--order", "desc"]
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "search_repositories", {"query": "test query", "sort": "stars", "order": "desc"}
        )

    def test_search_code(self, mock_mcp_request, runner):
        """Test search_code command."""
        # Run the command
        result = runner.invoke(
            github_app, ["search-code", "test query", "--sort", "indexed", "--order", "desc"]
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "search_code", {"query": "test query", "sort": "indexed", "order": "desc"}
        )


class TestUserCommands:
    """Tests for user-related commands."""

    def test_get_user(self, mock_mcp_request, runner):
        """Test get_user command."""
        # Run the command
        result = runner.invoke(github_app, ["get-user", "username"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with("get_user", {"username": "username"})

    def test_list_user_repos(self, mock_mcp_request, runner):
        """Test list_user_repos command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "list-user-repos",
                "username",
                "--type",
                "all",
                "--sort",
                "updated",
                "--direction",
                "desc",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "list_user_repositories",
            {"username": "username", "type": "all", "sort": "updated", "direction": "desc"},
        )

    def test_list_user_orgs(self, mock_mcp_request, runner):
        """Test list_user_orgs command."""
        # Run the command
        result = runner.invoke(github_app, ["list-user-orgs", "username"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "list_user_organizations", {"username": "username"}
        )


class TestOrganizationCommands:
    """Tests for organization-related commands."""

    def test_get_org(self, mock_mcp_request, runner):
        """Test get_org command."""
        # Run the command
        result = runner.invoke(github_app, ["get-org", "org-name"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with("get_organization", {"org": "org-name"})

    def test_list_org_repos(self, mock_mcp_request, runner):
        """Test list_org_repos command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "list-org-repos",
                "org-name",
                "--type",
                "all",
                "--sort",
                "updated",
                "--direction",
                "desc",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "list_organization_repositories",
            {"org": "org-name", "type": "all", "sort": "updated", "direction": "desc"},
        )

    def test_list_org_members(self, mock_mcp_request, runner):
        """Test list_org_members command."""
        # Run the command
        result = runner.invoke(github_app, ["list-org-members", "org-name", "--role", "admin"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "list_organization_members", {"org": "org-name", "role": "admin"}
        )


class TestWorkflowCommands:
    """Tests for workflow-related commands."""

    def test_list_workflows(self, mock_mcp_request, runner):
        """Test list_workflows command."""
        # Run the command
        result = runner.invoke(github_app, ["list-workflows", "owner", "repo"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "list_workflows", {"owner": "owner", "repo": "repo"}
        )

    def test_get_workflow(self, mock_mcp_request, runner):
        """Test get_workflow command."""
        # Run the command
        result = runner.invoke(github_app, ["get-workflow", "owner", "repo", "workflow.yml"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "get_workflow", {"owner": "owner", "repo": "repo", "workflow_id": "workflow.yml"}
        )

    def test_list_workflow_runs(self, mock_mcp_request, runner):
        """Test list_workflow_runs command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "list-workflow-runs",
                "owner",
                "repo",
                "--workflow-id",
                "workflow.yml",
                "--status",
                "completed",
                "--conclusion",
                "success",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "list_workflow_runs",
            {
                "owner": "owner",
                "repo": "repo",
                "workflow_id": "workflow.yml",
                "status": "completed",
                "conclusion": "success",
            },
        )

    def test_get_workflow_run(self, mock_mcp_request, runner):
        """Test get_workflow_run command."""
        # Run the command
        result = runner.invoke(github_app, ["get-workflow-run", "owner", "repo", "123"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "get_workflow_run", {"owner": "owner", "repo": "repo", "run_id": 123}
        )

    def test_rerun_workflow(self, mock_mcp_request, runner):
        """Test rerun_workflow command."""
        # Run the command
        result = runner.invoke(
            github_app, ["rerun-workflow", "owner", "repo", "123", "--enable-debug-logging"]
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "rerun_workflow",
            {"owner": "owner", "repo": "repo", "run_id": 123, "enable_debug_logging": True},
        )


class TestReleaseCommands:
    """Tests for release-related commands."""

    def test_list_releases(self, mock_mcp_request, runner):
        """Test list_releases command."""
        # Run the command
        result = runner.invoke(github_app, ["list-releases", "owner", "repo"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "list_releases", {"owner": "owner", "repo": "repo"}
        )

    def test_get_release(self, mock_mcp_request, runner):
        """Test get_release command."""
        # Run the command
        result = runner.invoke(github_app, ["get-release", "owner", "repo", "123"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "get_release", {"owner": "owner", "repo": "repo", "release_id": 123}
        )

    def test_create_release(self, mock_mcp_request, runner):
        """Test create_release command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "create-release",
                "owner",
                "repo",
                "v1.0.0",
                "--name",
                "Release 1.0.0",
                "--body",
                "Release notes",
                "--draft",
                "--prerelease",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "create_release",
            {
                "owner": "owner",
                "repo": "repo",
                "tag_name": "v1.0.0",
                "name": "Release 1.0.0",
                "body": "Release notes",
                "draft": True,
                "prerelease": True,
            },
        )


class TestLabelCommands:
    """Tests for label-related commands."""

    def test_list_labels(self, mock_mcp_request, runner):
        """Test list_labels command."""
        # Run the command
        result = runner.invoke(github_app, ["list-labels", "owner", "repo"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with("list_labels", {"owner": "owner", "repo": "repo"})

    def test_get_label(self, mock_mcp_request, runner):
        """Test get_label command."""
        # Run the command
        result = runner.invoke(github_app, ["get-label", "owner", "repo", "bug"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "get_label", {"owner": "owner", "repo": "repo", "name": "bug"}
        )

    def test_create_label(self, mock_mcp_request, runner):
        """Test create_label command."""
        # Run the command
        result = runner.invoke(
            github_app,
            ["create-label", "owner", "repo", "bug", "ff0000", "--description", "Bug label"],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "create_label",
            {
                "owner": "owner",
                "repo": "repo",
                "name": "bug",
                "color": "ff0000",
                "description": "Bug label",
            },
        )

    def test_update_label(self, mock_mcp_request, runner):
        """Test update_label command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "update-label",
                "owner",
                "repo",
                "bug",
                "--new-name",
                "bug-fix",
                "--color",
                "00ff00",
                "--description",
                "Updated bug label",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "update_label",
            {
                "owner": "owner",
                "repo": "repo",
                "name": "bug",
                "new_name": "bug-fix",
                "color": "00ff00",
                "description": "Updated bug label",
            },
        )

    def test_delete_label(self, mock_mcp_request, runner):
        """Test delete_label command."""
        # Run the command
        result = runner.invoke(github_app, ["delete-label", "owner", "repo", "bug"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "delete_label", {"owner": "owner", "repo": "repo", "name": "bug"}
        )


class TestMilestoneCommands:
    """Tests for milestone-related commands."""

    def test_list_milestones(self, mock_mcp_request, runner):
        """Test list_milestones command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "list-milestones",
                "owner",
                "repo",
                "--state",
                "open",
                "--sort",
                "due_on",
                "--direction",
                "asc",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "list_milestones",
            {
                "owner": "owner",
                "repo": "repo",
                "state": "open",
                "sort": "due_on",
                "direction": "asc",
            },
        )

    def test_get_milestone(self, mock_mcp_request, runner):
        """Test get_milestone command."""
        # Run the command
        result = runner.invoke(github_app, ["get-milestone", "owner", "repo", "1"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "get_milestone", {"owner": "owner", "repo": "repo", "milestone_number": 1}
        )

    def test_create_milestone(self, mock_mcp_request, runner):
        """Test create_milestone command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "create-milestone",
                "owner",
                "repo",
                "v1.0.0",
                "--state",
                "open",
                "--description",
                "First release",
                "--due-on",
                "2023-12-31",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "create_milestone",
            {
                "owner": "owner",
                "repo": "repo",
                "title": "v1.0.0",
                "state": "open",
                "description": "First release",
                "due_on": "2023-12-31",
            },
        )

    def test_update_milestone(self, mock_mcp_request, runner):
        """Test update_milestone command."""
        # Run the command
        result = runner.invoke(
            github_app,
            [
                "update-milestone",
                "owner",
                "repo",
                "1",
                "--title",
                "v1.0.1",
                "--state",
                "closed",
                "--description",
                "Updated release",
                "--due-on",
                "2023-12-31",
            ],
        )

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "update_milestone",
            {
                "owner": "owner",
                "repo": "repo",
                "milestone_number": 1,
                "title": "v1.0.1",
                "state": "closed",
                "description": "Updated release",
                "due_on": "2023-12-31",
            },
        )

    def test_delete_milestone(self, mock_mcp_request, runner):
        """Test delete_milestone command."""
        # Run the command
        result = runner.invoke(github_app, ["delete-milestone", "owner", "repo", "1"])

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Verify the MCP request was made correctly
        mock_mcp_request.assert_called_once_with(
            "delete_milestone", {"owner": "owner", "repo": "repo", "milestone_number": 1}
        )
