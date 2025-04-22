"""
GitHub MCP server CLI commands for interacting with GitHub through the MCP server.
"""

import json
import subprocess
import typer
from typing import Optional, List, Dict, Any
from loguru import logger
from erasmus.utils.rich_console import print_table

github_app = typer.Typer(help="Interact with GitHub through the MCP server.")


def _send_mcp_request(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Send a request to the GitHub MCP server.

    Args:
        method: The method name to call
        params: The parameters to send

    Returns:
        The response from the server

    Raises:
        typer.Exit: If the request fails
    """
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}

    try:
        # Start the MCP server process
        process = subprocess.Popen(
            ["github-mcp-server", "stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Send the request
        request_str = json.dumps(request)
        stdout, stderr = process.communicate(input=request_str)

        if process.returncode != 0:
            logger.error(f"MCP server error: {stderr}")
            raise typer.Exit(1)

        # Parse the response
        response = json.loads(
            stdout.split("\n")[1]
        )  # Skip the "GitHub MCP Server running on stdio" line

        if "error" in response:
            logger.error(f"MCP server error: {response['error']}")
            raise typer.Exit(1)

        return response["result"]

    except Exception as e:
        logger.error(f"Failed to send MCP request: {e}")
        raise typer.Exit(1)


@github_app.command()
def create_issue(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    title: str = typer.Argument(..., help="Issue title"),
    body: Optional[str] = typer.Option(None, help="Issue body content"),
    assignees: Optional[List[str]] = typer.Option(None, help="Usernames to assign to this issue"),
    labels: Optional[List[str]] = typer.Option(None, help="Labels to apply to this issue"),
):
    """Create a new issue in a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
        "title": title,
    }
    if body:
        params["body"] = body
    if assignees:
        params["assignees"] = assignees
    if labels:
        params["labels"] = labels

    result = _send_mcp_request("create_issue", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def add_comment(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    issue_number: int = typer.Argument(..., help="Issue number"),
    body: str = typer.Argument(..., help="Comment text"),
):
    """Add a comment to an existing issue."""
    params = {
        "owner": owner,
        "repo": repo,
        "issue_number": issue_number,
        "body": body,
    }

    result = _send_mcp_request("add_issue_comment", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def get_issue(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    issue_number: int = typer.Argument(..., help="Issue number"),
):
    """Get details of a specific issue in a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
        "issue_number": issue_number,
    }

    result = _send_mcp_request("get_issue", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def list_issues(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    state: Optional[str] = typer.Option("open", help="Filter by state ('open', 'closed', 'all')"),
    labels: Optional[List[str]] = typer.Option(None, help="Labels to filter by"),
    sort: Optional[str] = typer.Option(None, help="Sort by ('created', 'updated', 'comments')"),
    direction: Optional[str] = typer.Option(None, help="Sort direction ('asc', 'desc')"),
    since: Optional[str] = typer.Option(None, help="Filter by date (ISO 8601 timestamp)"),
    page: Optional[int] = typer.Option(None, help="Page number"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
):
    """List issues in a GitHub repository with filtering options."""
    params = {
        "owner": owner,
        "repo": repo,
        "state": state,
    }
    if labels:
        params["labels"] = labels
    if sort:
        params["sort"] = sort
    if direction:
        params["direction"] = direction
    if since:
        params["since"] = since
    if page:
        params["page"] = page
    if per_page:
        params["perPage"] = per_page

    result = _send_mcp_request("list_issues", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def update_issue(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    issue_number: int = typer.Argument(..., help="Issue number to update"),
    title: Optional[str] = typer.Option(None, help="New title"),
    body: Optional[str] = typer.Option(None, help="New description"),
    state: Optional[str] = typer.Option(None, help="New state ('open' or 'closed')"),
    labels: Optional[List[str]] = typer.Option(None, help="New labels"),
    assignees: Optional[List[str]] = typer.Option(None, help="New assignees"),
    milestone: Optional[int] = typer.Option(None, help="New milestone number"),
):
    """Update an existing issue in a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
        "issue_number": issue_number,
    }
    if title:
        params["title"] = title
    if body:
        params["body"] = body
    if state:
        params["state"] = state
    if labels:
        params["labels"] = labels
    if assignees:
        params["assignees"] = assignees
    if milestone:
        params["milestone"] = milestone

    result = _send_mcp_request("update_issue", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def search_issues(
    query: str = typer.Argument(..., help="Search query"),
    sort: Optional[str] = typer.Option(None, help="Sort field"),
    order: Optional[str] = typer.Option(None, help="Sort order"),
    page: Optional[int] = typer.Option(None, help="Page number"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
):
    """Search for issues and pull requests across GitHub repositories."""
    params = {
        "query": query,
    }
    if sort:
        params["sort"] = sort
    if order:
        params["order"] = order
    if page:
        params["page"] = page
    if per_page:
        params["perPage"] = per_page

    result = _send_mcp_request("search_issues", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def get_pr(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    pull_number: int = typer.Argument(..., help="Pull request number"),
):
    """Get details of a specific pull request."""
    params = {
        "owner": owner,
        "repo": repo,
        "pullNumber": pull_number,
    }

    result = _send_mcp_request("get_pull_request", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def list_prs(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    state: Optional[str] = typer.Option(None, help="PR state"),
    sort: Optional[str] = typer.Option(None, help="Sort field"),
    direction: Optional[str] = typer.Option(None, help="Sort direction"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """List and filter repository pull requests."""
    params = {
        "owner": owner,
        "repo": repo,
    }
    if state:
        params["state"] = state
    if sort:
        params["sort"] = sort
    if direction:
        params["direction"] = direction
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("list_pull_requests", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def merge_pr(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    pull_number: int = typer.Argument(..., help="Pull request number"),
    commit_title: Optional[str] = typer.Option(None, help="Title for the merge commit"),
    commit_message: Optional[str] = typer.Option(None, help="Message for the merge commit"),
    merge_method: Optional[str] = typer.Option(None, help="Merge method"),
):
    """Merge a pull request."""
    params = {
        "owner": owner,
        "repo": repo,
        "pullNumber": pull_number,
    }
    if commit_title:
        params["commit_title"] = commit_title
    if commit_message:
        params["commit_message"] = commit_message
    if merge_method:
        params["merge_method"] = merge_method

    result = _send_mcp_request("merge_pull_request", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def create_pr(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    title: str = typer.Argument(..., help="Pull request title"),
    head: str = typer.Argument(
        ..., help="The name of the branch where your changes are implemented"
    ),
    base: str = typer.Argument(
        ..., help="The name of the branch you want your changes pulled into"
    ),
    body: Optional[str] = typer.Option(None, help="Pull request description"),
    draft: Optional[bool] = typer.Option(False, help="Create pull request as draft"),
):
    """Create a new pull request in a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
        "title": title,
        "head": head,
        "base": base,
    }
    if body:
        params["body"] = body
    if draft:
        params["draft"] = draft

    result = _send_mcp_request("create_pull_request", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def update_pr(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    pull_number: int = typer.Argument(..., help="Pull request number"),
    title: Optional[str] = typer.Option(None, help="New title"),
    body: Optional[str] = typer.Option(None, help="New description"),
    state: Optional[str] = typer.Option(None, help="New state ('open' or 'closed')"),
    base: Optional[str] = typer.Option(None, help="Name of the branch to merge into"),
):
    """Update an existing pull request in a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
        "pullNumber": pull_number,
    }
    if title:
        params["title"] = title
    if body:
        params["body"] = body
    if state:
        params["state"] = state
    if base:
        params["base"] = base

    result = _send_mcp_request("update_pull_request", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def get_pr_files(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    pull_number: int = typer.Argument(..., help="Pull request number"),
):
    """Get the list of files changed in a pull request."""
    params = {
        "owner": owner,
        "repo": repo,
        "pullNumber": pull_number,
    }

    result = _send_mcp_request("get_pull_request_files", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def get_pr_status(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    pull_number: int = typer.Argument(..., help="Pull request number"),
):
    """Get the combined status of all status checks for a pull request."""
    params = {
        "owner": owner,
        "repo": repo,
        "pullNumber": pull_number,
    }

    result = _send_mcp_request("get_pull_request_status", params)
    typer.echo(json.dumps(result, indent=2))


# Repository commands
@github_app.command()
def create_repo(
    name: str = typer.Argument(..., help="Repository name"),
    description: Optional[str] = typer.Option(None, help="Repository description"),
    private: Optional[bool] = typer.Option(False, help="Create a private repository"),
    auto_init: Optional[bool] = typer.Option(False, help="Initialize with README"),
    gitignore_template: Optional[str] = typer.Option(None, help="Add .gitignore template"),
    license_template: Optional[str] = typer.Option(None, help="Add license template"),
):
    """Create a new GitHub repository in your account."""
    params = {
        "name": name,
    }
    if description:
        params["description"] = description
    if private:
        params["private"] = private
    if auto_init:
        params["auto_init"] = auto_init
    if gitignore_template:
        params["gitignore_template"] = gitignore_template
    if license_template:
        params["license_template"] = license_template

    result = _send_mcp_request("create_repository", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def fork_repo(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    organization: Optional[str] = typer.Option(None, help="Organization to fork to"),
):
    """Fork a GitHub repository to your account or specified organization."""
    params = {
        "owner": owner,
        "repo": repo,
    }
    if organization:
        params["organization"] = organization

    result = _send_mcp_request("fork_repository", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def get_file(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    path: str = typer.Argument(..., help="Path to file or directory"),
    ref: Optional[str] = typer.Option(None, help="The name of the commit/branch/tag"),
):
    """Get the contents of a file or directory from a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
        "path": path,
    }
    if ref:
        params["ref"] = ref

    result = _send_mcp_request("get_file_contents", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def create_or_update_file(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    path: str = typer.Argument(..., help="Path in the repository"),
    content: str = typer.Argument(..., help="File content"),
    message: str = typer.Argument(..., help="Commit message"),
    branch: Optional[str] = typer.Option(None, help="Branch to commit to"),
    sha: Optional[str] = typer.Option(None, help="SHA of file being updated"),
):
    """Create or update a single file in a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
        "path": path,
        "content": content,
        "message": message,
    }
    if branch:
        params["branch"] = branch
    if sha:
        params["sha"] = sha

    result = _send_mcp_request("create_or_update_file", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def push_files(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    branch: str = typer.Argument(..., help="Branch to commit to"),
    message: str = typer.Argument(..., help="Commit message"),
    files: List[str] = typer.Argument(..., help="Files to push (in path:content format)"),
):
    """Push multiple files to a GitHub repository in a single commit."""
    # Convert files list from path:content format to dictionary
    files_dict = {}
    for file_spec in files:
        path, content = file_spec.split(":", 1)
        files_dict[path] = content

    params = {
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "message": message,
        "files": files_dict,
    }

    result = _send_mcp_request("push_files", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def create_branch(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    branch: str = typer.Argument(..., help="New branch name"),
    sha: str = typer.Argument(..., help="SHA of commit to branch from"),
):
    """Create a new branch in a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "sha": sha,
    }

    result = _send_mcp_request("create_branch", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def list_branches(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    protected: Optional[bool] = typer.Option(None, help="Filter by protected status"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """List branches in a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
    }
    if protected is not None:
        params["protected"] = protected
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("list_branches", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def list_commits(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    sha: Optional[str] = typer.Option(None, help="SHA or branch to start listing commits from"),
    path: Optional[str] = typer.Option(None, help="Only commits containing this file path"),
    author: Optional[str] = typer.Option(
        None, help="GitHub username or email address to filter by"
    ),
    since: Optional[str] = typer.Option(None, help="Only commits after this timestamp"),
    until: Optional[str] = typer.Option(None, help="Only commits before this timestamp"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """Get list of commits of a branch in a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
    }
    if sha:
        params["sha"] = sha
    if path:
        params["path"] = path
    if author:
        params["author"] = author
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("list_commits", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def search_repos(
    query: str = typer.Argument(..., help="Search query"),
    sort: Optional[str] = typer.Option(None, help="Sort field"),
    order: Optional[str] = typer.Option(None, help="Sort order"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """Search for GitHub repositories."""
    params = {
        "query": query,
    }
    if sort:
        params["sort"] = sort
    if order:
        params["order"] = order
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("search_repositories", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def search_code(
    query: str = typer.Argument(..., help="Search query"),
    sort: Optional[str] = typer.Option(None, help="Sort field"),
    order: Optional[str] = typer.Option(None, help="Sort order"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """Search for code across GitHub repositories."""
    params = {
        "query": query,
    }
    if sort:
        params["sort"] = sort
    if order:
        params["order"] = order
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("search_code", params)
    typer.echo(json.dumps(result, indent=2))


# User commands
@github_app.command()
def get_user(
    username: Optional[str] = typer.Argument(None, help="GitHub username"),
):
    """Get information about a GitHub user."""
    params = {}
    if username:
        params["username"] = username

    result = _send_mcp_request("get_user", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def list_user_repos(
    username: str = typer.Argument(..., help="GitHub username"),
    type: Optional[str] = typer.Option(
        None, help="Filter by repository type (all, owner, public, private, member)"
    ),
    sort: Optional[str] = typer.Option(None, help="Sort field"),
    direction: Optional[str] = typer.Option(None, help="Sort direction"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """List repositories for a GitHub user."""
    params = {
        "username": username,
    }
    if type:
        params["type"] = type
    if sort:
        params["sort"] = sort
    if direction:
        params["direction"] = direction
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("list_user_repositories", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def list_user_orgs(
    username: str = typer.Argument(..., help="GitHub username"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """List organizations for a GitHub user."""
    params = {
        "username": username,
    }
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("list_user_organizations", params)
    typer.echo(json.dumps(result, indent=2))


# Organization commands
@github_app.command()
def get_org(
    org: str = typer.Argument(..., help="Organization name"),
):
    """Get information about a GitHub organization."""
    params = {
        "org": org,
    }

    result = _send_mcp_request("get_organization", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def list_org_repos(
    org: str = typer.Argument(..., help="Organization name"),
    type: Optional[str] = typer.Option(
        None, help="Filter by repository type (all, public, private, forks, sources, member)"
    ),
    sort: Optional[str] = typer.Option(None, help="Sort field"),
    direction: Optional[str] = typer.Option(None, help="Sort direction"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """List repositories for a GitHub organization."""
    params = {
        "org": org,
    }
    if type:
        params["type"] = type
    if sort:
        params["sort"] = sort
    if direction:
        params["direction"] = direction
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("list_organization_repositories", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def list_org_members(
    org: str = typer.Argument(..., help="Organization name"),
    role: Optional[str] = typer.Option(None, help="Filter by role (all, admin, member)"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """List members of a GitHub organization."""
    params = {
        "org": org,
    }
    if role:
        params["role"] = role
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("list_organization_members", params)
    typer.echo(json.dumps(result, indent=2))


# Workflow commands
@github_app.command()
def list_workflows(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """List GitHub Actions workflows for a repository."""
    params = {
        "owner": owner,
        "repo": repo,
    }
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("list_workflows", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def get_workflow(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    workflow_id: str = typer.Argument(..., help="Workflow ID or file name"),
):
    """Get details of a specific GitHub Actions workflow."""
    params = {
        "owner": owner,
        "repo": repo,
        "workflow_id": workflow_id,
    }

    result = _send_mcp_request("get_workflow", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def list_workflow_runs(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    workflow_id: Optional[str] = typer.Option(None, help="Workflow ID or file name"),
    status: Optional[str] = typer.Option(
        None, help="Filter by status (queued, in_progress, completed)"
    ),
    conclusion: Optional[str] = typer.Option(
        None,
        help="Filter by conclusion (success, failure, neutral, cancelled, skipped, timed_out, action_required)",
    ),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """List runs of a GitHub Actions workflow."""
    params = {
        "owner": owner,
        "repo": repo,
    }
    if workflow_id:
        params["workflow_id"] = workflow_id
    if status:
        params["status"] = status
    if conclusion:
        params["conclusion"] = conclusion
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("list_workflow_runs", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def get_workflow_run(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    run_id: int = typer.Argument(..., help="Run ID"),
):
    """Get details of a specific GitHub Actions workflow run."""
    params = {
        "owner": owner,
        "repo": repo,
        "run_id": run_id,
    }

    result = _send_mcp_request("get_workflow_run", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def rerun_workflow(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    run_id: int = typer.Argument(..., help="Run ID"),
    enable_debug_logging: Optional[bool] = typer.Option(None, help="Enable debug logging"),
):
    """Re-run a GitHub Actions workflow run."""
    params = {
        "owner": owner,
        "repo": repo,
        "run_id": run_id,
    }
    if enable_debug_logging is not None:
        params["enable_debug_logging"] = enable_debug_logging

    result = _send_mcp_request("rerun_workflow", params)
    typer.echo(json.dumps(result, indent=2))


# Release commands
@github_app.command()
def list_releases(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """List releases for a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
    }
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("list_releases", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def get_release(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    release_id: int = typer.Argument(..., help="Release ID"),
):
    """Get details of a specific GitHub release."""
    params = {
        "owner": owner,
        "repo": repo,
        "release_id": release_id,
    }

    result = _send_mcp_request("get_release", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def create_release(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    tag_name: str = typer.Argument(..., help="Tag name for the release"),
    name: Optional[str] = typer.Option(None, help="Release name"),
    body: Optional[str] = typer.Option(None, help="Release description"),
    draft: Optional[bool] = typer.Option(None, help="Create as draft"),
    prerelease: Optional[bool] = typer.Option(None, help="Create as prerelease"),
    target_commitish: Optional[str] = typer.Option(None, help="Target commitish (branch or SHA)"),
):
    """Create a new GitHub release."""
    params = {
        "owner": owner,
        "repo": repo,
        "tag_name": tag_name,
    }
    if name:
        params["name"] = name
    if body:
        params["body"] = body
    if draft is not None:
        params["draft"] = draft
    if prerelease is not None:
        params["prerelease"] = prerelease
    if target_commitish:
        params["target_commitish"] = target_commitish

    result = _send_mcp_request("create_release", params)
    typer.echo(json.dumps(result, indent=2))


# Label commands
@github_app.command()
def list_labels(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """List labels for a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
    }
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("list_labels", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def get_label(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    name: str = typer.Argument(..., help="Label name"),
):
    """Get details of a specific GitHub label."""
    params = {
        "owner": owner,
        "repo": repo,
        "name": name,
    }

    result = _send_mcp_request("get_label", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def create_label(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    name: str = typer.Argument(..., help="Label name"),
    color: str = typer.Argument(..., help="Label color (hex code without #)"),
    description: Optional[str] = typer.Option(None, help="Label description"),
):
    """Create a new GitHub label."""
    params = {
        "owner": owner,
        "repo": repo,
        "name": name,
        "color": color,
    }
    if description:
        params["description"] = description

    result = _send_mcp_request("create_label", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def update_label(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    name: str = typer.Argument(..., help="Label name"),
    new_name: Optional[str] = typer.Option(None, help="New label name"),
    color: Optional[str] = typer.Option(None, help="New label color (hex code without #)"),
    description: Optional[str] = typer.Option(None, help="New label description"),
):
    """Update an existing GitHub label."""
    params = {
        "owner": owner,
        "repo": repo,
        "name": name,
    }
    if new_name:
        params["new_name"] = new_name
    if color:
        params["color"] = color
    if description:
        params["description"] = description

    result = _send_mcp_request("update_label", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def delete_label(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    name: str = typer.Argument(..., help="Label name"),
):
    """Delete a GitHub label."""
    params = {
        "owner": owner,
        "repo": repo,
        "name": name,
    }

    result = _send_mcp_request("delete_label", params)
    typer.echo(json.dumps(result, indent=2))


# Milestone commands
@github_app.command()
def list_milestones(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    state: Optional[str] = typer.Option(None, help="Filter by state (open, closed, all)"),
    sort: Optional[str] = typer.Option(None, help="Sort field"),
    direction: Optional[str] = typer.Option(None, help="Sort direction"),
    per_page: Optional[int] = typer.Option(None, help="Results per page"),
    page: Optional[int] = typer.Option(None, help="Page number"),
):
    """List milestones for a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
    }
    if state:
        params["state"] = state
    if sort:
        params["sort"] = sort
    if direction:
        params["direction"] = direction
    if per_page:
        params["perPage"] = per_page
    if page:
        params["page"] = page

    result = _send_mcp_request("list_milestones", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def get_milestone(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    milestone_number: int = typer.Argument(..., help="Milestone number"),
):
    """Get details of a specific GitHub milestone."""
    params = {
        "owner": owner,
        "repo": repo,
        "milestone_number": milestone_number,
    }

    result = _send_mcp_request("get_milestone", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def create_milestone(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    title: str = typer.Argument(..., help="Milestone title"),
    state: Optional[str] = typer.Option(None, help="Milestone state (open, closed)"),
    description: Optional[str] = typer.Option(None, help="Milestone description"),
    due_on: Optional[str] = typer.Option(None, help="Due date (ISO 8601 format)"),
):
    """Create a new GitHub milestone."""
    params = {
        "owner": owner,
        "repo": repo,
        "title": title,
    }
    if state:
        params["state"] = state
    if description:
        params["description"] = description
    if due_on:
        params["due_on"] = due_on

    result = _send_mcp_request("create_milestone", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def update_milestone(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    milestone_number: int = typer.Argument(..., help="Milestone number"),
    title: Optional[str] = typer.Option(None, help="New milestone title"),
    state: Optional[str] = typer.Option(None, help="New milestone state (open, closed)"),
    description: Optional[str] = typer.Option(None, help="New milestone description"),
    due_on: Optional[str] = typer.Option(None, help="New due date (ISO 8601 format)"),
):
    """Update an existing GitHub milestone."""
    params = {
        "owner": owner,
        "repo": repo,
        "milestone_number": milestone_number,
    }
    if title:
        params["title"] = title
    if state:
        params["state"] = state
    if description:
        params["description"] = description
    if due_on:
        params["due_on"] = due_on

    result = _send_mcp_request("update_milestone", params)
    typer.echo(json.dumps(result, indent=2))


@github_app.command()
def delete_milestone(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    milestone_number: int = typer.Argument(..., help="Milestone number"),
):
    """Delete a GitHub milestone."""
    params = {
        "owner": owner,
        "repo": repo,
        "milestone_number": milestone_number,
    }

    result = _send_mcp_request("delete_milestone", params)
    typer.echo(json.dumps(result, indent=2))
