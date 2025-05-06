"""
GitHub MCP server CLI commands for interacting with GitHub through the MCP server.
"""

import json
import typer
from typing import List, Dict, Any
from loguru import logger
from erasmus.utils.rich_console import print_table, get_console
from erasmus.mcp.client import StdioClient, McpError

console = get_console()
mcp_client = StdioClient()

# Server name constant
GITHUB_SERVER_NAME = "github"

github_app = typer.Typer(help="Interact with GitHub through the MCP server.", no_args_is_help=True)

# Global error handler to show commands on incorrect usage
@github_app.callback()
def github_mcp_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print("[bold red]Error:[/] No command specified.")
        show_github_commands_help()
        raise typer.Exit(1)


def show_github_commands_help():
    """Display available GitHub MCP commands in a table."""
    commands = [
        ["Issues", ""],
        ["create-issue", "Create a new issue"],
        ["get-issue", "Get details of a specific issue"],
        ["list-issues", "List issues in a repository"],
        ["update-issue", "Update an existing issue"],
        ["add-issue-comment", "Add a comment to an issue"],
        ["get-issue-comments", "Get comments for an issue"],
        
        ["Pull Requests", ""],
        ["create-pr", "Create a new pull request"],
        ["get-pr", "Get details of a specific pull request"],
        ["list-prs", "List pull requests in a repository"],
        ["update-pr", "Update an existing pull request"],
        ["merge-pr", "Merge a pull request"],
        ["add-pr-comment", "Add a review comment to a pull request"],
        ["get-pr-comments", "Get review comments on a pull request"],
        ["get-pr-files", "Get files changed in a pull request"],
        ["get-pr-reviews", "Get reviews on a pull request"],
        ["create-pr-review", "Create a review on a pull request"],
        ["get-pr-status", "Get status checks for a pull request"],
        ["update-pr-branch", "Update a pull request branch"],
        
        ["Repositories", ""],
        ["create-repo", "Create a new repository"],
        # ["get-repo", "Get repository details"],
        # ["list-repos", "List repositories"],
        # ["update-repo", "Update repository settings"],
        # ["delete-repo", "Delete a repository"],
    ]
    
    print_table(["Command", "Description"], commands, title="GitHub MCP Commands")


def _send_mcp_request(method: str, params: Dict[str, Any]) -> Any:
    """Send a request to the GitHub MCP server using StdioClient.communicate.

    Args:
        method: The method name to call.
        params: The parameters to send.

    Returns:
        The 'result' field from the JSON-RPC response.

    Raises:
        typer.Exit: If the request fails due to client error, communication error,
                    JSON parsing error, or server-side JSON-RPC error.
    """
    try:
        stdout, stderr = mcp_client.communicate(
            server_name=GITHUB_SERVER_NAME, 
            method=method, 
            params=params
        )
        
        # Log stderr for debugging, even if stdout has the response
        if stderr:
            logger.debug(f"GitHub MCP server stderr: {stderr.strip()}")

        if not stdout:
            logger.error("Received empty stdout from GitHub MCP server.")
            console.print(f"[bold red]Error:[/] No response received from {GITHUB_SERVER_NAME} server.")
            if stderr:
                 console.print(f"[bold yellow]Server stderr:[/]\n{stderr.strip()}")
            raise typer.Exit(1)

        # Parse the JSON response from stdout
        try:
            response = json.loads(stdout)
        except json.JSONDecodeError as error:
            logger.error(f"Failed to decode JSON response from stdout: {error}", exc_info=True)
            logger.error(f"Raw stdout: {stdout.strip()}")
            console.print(f"[bold red]Error:[/] Invalid response format from {GITHUB_SERVER_NAME} server.")
            raise typer.Exit(1)

        # Check for JSON-RPC errors reported by the server
        if "error" in response and response["error"]:
            error_details = response['error']
            error_msg = error_details.get('message', 'Unknown server error')
            error_code = error_details.get('code', 'N/A')
            logger.error(f"GitHub MCP server returned error: Code={error_code}, Message='{error_msg}'")
            console.print(f"[bold red]Server Error ({error_code}):[/] {error_msg}")
            # Optionally show more details if available
            # if 'data' in error_details:
            #    logger.error(f"Error data: {error_details['data']}")
            raise typer.Exit(1)
        
        # Check if 'result' exists
        if "result" not in response:
             logger.error(f"JSON-RPC response missing 'result' field. Response: {response}")
             console.print(f"[bold red]Error:[/] Malformed response from {GITHUB_SERVER_NAME} server (missing 'result').")
             raise typer.Exit(1)

        return response["result"]

    except McpError as error:
        logger.error(f"MCP Client Error communicating with '{GITHUB_SERVER_NAME}': {error}", exc_info=True)
        console.print(f"\n[bold red]Error:[/] Failed to communicate with {GITHUB_SERVER_NAME} server: {error}")
        raise typer.Exit(1)
    except Exception as error:
        # Catch unexpected errors during communication or processing
        logger.error(f"Unexpected error sending MCP request to '{GITHUB_SERVER_NAME}': {error}", exc_info=True)
        console.print(f"\n[bold red]Error:[/] An unexpected error occurred: {error}")
        raise typer.Exit(1)


# Issue commands
@github_app.command()
def create_issue(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    title: str = typer.Option(..., help="Issue title"),
    body: str = typer.Option(None, help="Issue body"),
    labels: List[str] = typer.Option(None, help="Issue labels"),
    assignees: List[str] = typer.Option(None, help="Issue assignees"),
):
    """Create a new issue in a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
        "title": title,
        "body": body,
        "labels": labels,
        "assignees": assignees,
    }
    result = _send_mcp_request("create_issue", params)
    logger.info(f"Created issue #{result['number']}: {result['html_url']}")


@github_app.command()
def get_issue(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Issue number"),
):
    """Get details of a specific issue in a GitHub repository."""
    params = {"owner": owner, "repo": repo, "number": number}
    result = _send_mcp_request("get_issue", params)
    print_table(
        ["Field", "Value"],
        [
            ["Number", result["number"]],
            ["Title", result["title"]],
            ["State", result["state"]],
            ["Created", result["created_at"]],
            ["Updated", result["updated_at"]],
            ["URL", result["html_url"]],
        ],
        title=f"Issue #{number}",
    )


@github_app.command()
def list_issues(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    state: str = typer.Option("open", help="Issue state (open, closed, all)"),
    labels: List[str] = typer.Option(None, help="Filter by labels"),
    assignee: str = typer.Option(None, help="Filter by assignee"),
    creator: str = typer.Option(None, help="Filter by creator"),
    mentioned: str = typer.Option(None, help="Filter by mentioned user"),
    since: str = typer.Option(None, help="Filter by updated date (YYYY-MM-DD)"),
):
    """List issues in a GitHub repository with filtering options."""
    params = {
        "owner": owner,
        "repo": repo,
        "state": state,
        "labels": labels,
        "assignee": assignee,
        "creator": creator,
        "mentioned": mentioned,
        "since": since,
    }
    result = _send_mcp_request("list_issues", params)
    if not result:
        logger.info("No issues found")
        return
    rows = [
        [issue["number"], issue["title"], issue["state"], issue["created_at"]] for issue in result
    ]
    print_table(
        ["Number", "Title", "State", "Created"],
        rows,
        title=f"Issues in {owner}/{repo}",
    )


@github_app.command()
def update_issue(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Issue number"),
    title: str = typer.Option(None, help="New issue title"),
    body: str = typer.Option(None, help="New issue body"),
    state: str = typer.Option(None, help="New issue state (open, closed)"),
    labels: List[str] = typer.Option(None, help="New issue labels"),
    assignees: List[str] = typer.Option(None, help="New issue assignees"),
):
    """Update an existing issue in a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
        "number": number,
        "title": title,
        "body": body,
        "state": state,
        "labels": labels,
        "assignees": assignees,
    }
    result = _send_mcp_request("update_issue", params)
    logger.info(f"Updated issue #{number}: {result['html_url']}")


@github_app.command()
def add_issue_comment(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Issue number"),
    body: str = typer.Option(..., help="Comment body"),
):
    """Add a comment to an existing issue."""
    params = {
        "owner": owner,
        "repo": repo,
        "number": number,
        "body": body,
    }
    result = _send_mcp_request("add_issue_comment", params)
    logger.info(f"Added comment to issue #{number}: {result['html_url']}")


@github_app.command()
def get_issue_comments(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Issue number"),
):
    """Get comments for a GitHub issue."""
    params = {"owner": owner, "repo": repo, "number": number}
    result = _send_mcp_request("get_issue_comments", params)
    if not result:
        logger.info("No comments found")
        return
    rows = [
        [comment["user"]["login"], comment["created_at"], comment["body"][:50] + "..."]
        for comment in result
    ]
    print_table(
        ["Author", "Created", "Comment"],
        rows,
        title=f"Comments on Issue #{number}",
    )


# Pull Request commands
@github_app.command()
def create_pr(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    title: str = typer.Option(..., help="Pull request title"),
    head: str = typer.Option(..., help="The branch with changes"),
    base: str = typer.Option("main", help="The branch to merge into"),
    body: str = typer.Option(None, help="Pull request description"),
    draft: bool = typer.Option(False, help="Create as draft pull request"),
):
    """Create a new pull request in a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
        "title": title,
        "head": head,
        "base": base,
        "body": body,
        "draft": draft,
    }
    result = _send_mcp_request("create_pull_request", params)
    logger.info(f"Created pull request #{result['number']}: {result['html_url']}")


@github_app.command()
def get_pr(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Pull request number"),
):
    """Get details of a specific pull request."""
    params = {"owner": owner, "repo": repo, "number": number}
    result = _send_mcp_request("get_pull_request", params)
    print_table(
        ["Field", "Value"],
        [
            ["Number", result["number"]],
            ["Title", result["title"]],
            ["State", result["state"]],
            ["Created", result["created_at"]],
            ["Updated", result["updated_at"]],
            ["Head", result["head"]["ref"]],
            ["Base", result["base"]["ref"]],
            ["URL", result["html_url"]],
        ],
        title=f"Pull Request #{number}",
    )


@github_app.command()
def list_prs(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    state: str = typer.Option("open", help="PR state (open, closed, all)"),
    head: str = typer.Option(None, help="Filter by head branch"),
    base: str = typer.Option(None, help="Filter by base branch"),
    sort: str = typer.Option("created", help="Sort by (created, updated, popularity)"),
    direction: str = typer.Option("desc", help="Sort direction (asc, desc)"),
):
    """List and filter repository pull requests."""
    params = {
        "owner": owner,
        "repo": repo,
        "state": state,
        "head": head,
        "base": base,
        "sort": sort,
        "direction": direction,
    }
    result = _send_mcp_request("list_pull_requests", params)
    if not result:
        logger.info("No pull requests found")
        return
    rows = [[pr["number"], pr["title"], pr["state"], pr["created_at"]] for pr in result]
    print_table(
        ["Number", "Title", "State", "Created"],
        rows,
        title=f"Pull Requests in {owner}/{repo}",
    )


@github_app.command()
def update_pr(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Pull request number"),
    title: str = typer.Option(None, help="New PR title"),
    body: str = typer.Option(None, help="New PR body"),
    state: str = typer.Option(None, help="New PR state (open, closed)"),
    base: str = typer.Option(None, help="New base branch"),
):
    """Update an existing pull request in a GitHub repository."""
    params = {
        "owner": owner,
        "repo": repo,
        "number": number,
        "title": title,
        "body": body,
        "state": state,
        "base": base,
    }
    result = _send_mcp_request("update_pull_request", params)
    logger.info(f"Updated pull request #{number}: {result['html_url']}")


@github_app.command()
def merge_pr(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Pull request number"),
    merge_method: str = typer.Option("merge", help="Merge method (merge, squash, rebase)"),
    commit_title: str = typer.Option(None, help="Title for the merge commit"),
    commit_message: str = typer.Option(None, help="Message for the merge commit"),
):
    """Merge a pull request."""
    params = {
        "owner": owner,
        "repo": repo,
        "number": number,
        "merge_method": merge_method,
        "commit_title": commit_title,
        "commit_message": commit_message,
    }
    result = _send_mcp_request("merge_pull_request", params)
    logger.info(f"Merged pull request #{number}")


@github_app.command()
def add_pr_comment(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Pull request number"),
    body: str = typer.Option(..., help="Comment body"),
):
    """Add a review comment to a pull request."""
    params = {
        "owner": owner,
        "repo": repo,
        "number": number,
        "body": body,
    }
    result = _send_mcp_request("add_pull_request_comment", params)
    logger.info(f"Added comment to pull request #{number}: {result['html_url']}")


@github_app.command()
def get_pr_comments(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Pull request number"),
):
    """Get the review comments on a pull request."""
    params = {"owner": owner, "repo": repo, "number": number}
    result = _send_mcp_request("get_pull_request_comments", params)
    if not result:
        logger.info("No comments found")
        return
    rows = [
        [comment["user"]["login"], comment["created_at"], comment["body"][:50] + "..."]
        for comment in result
    ]
    print_table(
        ["Author", "Created", "Comment"],
        rows,
        title=f"Comments on Pull Request #{number}",
    )


@github_app.command()
def get_pr_files(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Pull request number"),
):
    """Get the list of files changed in a pull request."""
    params = {"owner": owner, "repo": repo, "number": number}
    result = _send_mcp_request("get_pull_request_files", params)
    if not result:
        logger.info("No files changed")
        return
    rows = [
        [file["filename"], file["status"], file["additions"], file["deletions"]] for file in result
    ]
    print_table(
        ["Filename", "Status", "Additions", "Deletions"],
        rows,
        title=f"Files Changed in Pull Request #{number}",
    )


@github_app.command()
def get_pr_reviews(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Pull request number"),
):
    """Get the reviews on a pull request."""
    params = {"owner": owner, "repo": repo, "number": number}
    result = _send_mcp_request("get_pull_request_reviews", params)
    if not result:
        logger.info("No reviews found")
        return
    rows = [[review["user"]["login"], review["state"], review["submitted_at"]] for review in result]
    print_table(
        ["Reviewer", "State", "Submitted"],
        rows,
        title=f"Reviews on Pull Request #{number}",
    )


@github_app.command()
def create_pr_review(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Pull request number"),
    event: str = typer.Option(..., help="Review event (APPROVE, REQUEST_CHANGES, COMMENT)"),
    body: str = typer.Option(None, help="Review body"),
):
    """Create a review on a pull request."""
    params = {
        "owner": owner,
        "repo": repo,
        "number": number,
        "event": event,
        "body": body,
    }
    result = _send_mcp_request("create_pull_request_review", params)
    logger.info(f"Created review on pull request #{number}: {result['html_url']}")


@github_app.command()
def get_pr_status(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Pull request number"),
):
    """Get the combined status of all status checks for a pull request."""
    params = {"owner": owner, "repo": repo, "number": number}
    result = _send_mcp_request("get_pull_request_status", params)
    print_table(
        ["Field", "Value"],
        [
            ["State", result["state"]],
            ["Total", result["total_count"]],
            ["Successful", result["statuses"].count(lambda s: s["state"] == "success")],
            ["Failed", result["statuses"].count(lambda s: s["state"] == "failure")],
            ["Pending", result["statuses"].count(lambda s: s["state"] == "pending")],
        ],
        title=f"Status Checks for Pull Request #{number}",
    )


@github_app.command()
def update_pr_branch(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Pull request number"),
):
    """Update a pull request branch with the latest changes from the base branch."""
    params = {"owner": owner, "repo": repo, "number": number}
    result = _send_mcp_request("update_pull_request_branch", params)
    logger.info(f"Updated pull request #{number} branch")


# Repository commands
@github_app.command()
def create_repo(
    name: str = typer.Argument(..., help="Repository name"),
    private: bool = typer.Option(False, help="Create a private repository"),
    description: str = typer.Option(None, help="Repository description"),
    homepage: str = typer.Option(None, help="Repository homepage URL"),
    has_issues: bool = typer.Option(True, help="Enable issues"),
    has_projects: bool = typer.Option(True, help="Enable projects"),
    has_wiki: bool = typer.Option(True, help="Enable wiki"),
    auto_init: bool = typer.Option(False, help="Initialize with README"),
    gitignore_template: str = typer.Option(None, help="Add .gitignore template"),
    license_template: str = typer.Option(None, help="Add license template"),
    org: str = typer.Option(None, help="Create in organization"),
):
    """Create a new GitHub repository."""
    params = {
        "name": name,
        "private": private,
        "description": description,
        "homepage": homepage,
        "has_issues": has_issues,
        "has_projects": has_projects,
        "has_wiki": has_wiki,
        "auto_init": auto_init,
        "gitignore_template": gitignore_template,
        "license_template": license_template,
        "org": org,
    }
    result = _send_mcp_request("create_repository", params)
    logger.info(f"Created repository: {result['html_url']}")


@github_app.command()
def get_repo(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
):
    """Get details about a GitHub repository."""
    params = {"owner": owner, "repo": repo}
    result = _send_mcp_request("get_repository", params)
    print_table(
        ["Field", "Value"],
        [
            ["Name", result["name"]],
            ["Description", result["description"]],
            ["Private", result["private"]],
            ["Fork", result["fork"]],
            ["Created", result["created_at"]],
            ["Updated", result["updated_at"]],
            ["Stars", result["stargazers_count"]],
            ["Forks", result["forks_count"]],
            ["URL", result["html_url"]],
        ],
        title=f"Repository {owner}/{repo}",
    )


@github_app.command()
def list_repos(
    owner: str = typer.Argument(..., help="User or organization name"),
    type: str = typer.Option("all", help="Type of repos (all, owner, member)"),
    sort: str = typer.Option("full_name", help="Sort by (created, updated, pushed, full_name)"),
    direction: str = typer.Option("asc", help="Sort direction (asc, desc)"),
):
    """List repositories for a user or organization."""
    params = {
        "owner": owner,
        "type": type,
        "sort": sort,
        "direction": direction,
    }
    result = _send_mcp_request("list_repositories", params)
    if not result:
        logger.info("No repositories found")
        return
    rows = [
        [repo["name"], repo["private"], repo["stargazers_count"], repo["forks_count"]]
        for repo in result
    ]
    print_table(
        ["Name", "Private", "Stars", "Forks"],
        rows,
        title=f"Repositories for {owner}",
    )


@github_app.command()
def update_repo(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    name: str = typer.Option(None, help="New repository name"),
    description: str = typer.Option(None, help="New description"),
    homepage: str = typer.Option(None, help="New homepage URL"),
    private: bool = typer.Option(None, help="Make private"),
    has_issues: bool = typer.Option(None, help="Enable issues"),
    has_projects: bool = typer.Option(None, help="Enable projects"),
    has_wiki: bool = typer.Option(None, help="Enable wiki"),
    default_branch: str = typer.Option(None, help="Set default branch"),
    allow_squash_merge: bool = typer.Option(None, help="Allow squash merging"),
    allow_merge_commit: bool = typer.Option(None, help="Allow merge commits"),
    allow_rebase_merge: bool = typer.Option(None, help="Allow rebase merging"),
):
    """Update a GitHub repository's settings."""
    params = {
        "owner": owner,
        "repo": repo,
        "name": name,
        "description": description,
        "homepage": homepage,
        "private": private,
        "has_issues": has_issues,
        "has_projects": has_projects,
        "has_wiki": has_wiki,
        "default_branch": default_branch,
        "allow_squash_merge": allow_squash_merge,
        "allow_merge_commit": allow_merge_commit,
        "allow_rebase_merge": allow_rebase_merge,
    }
    result = _send_mcp_request("update_repository", params)
    logger.info(f"Updated repository: {result['html_url']}")


@github_app.command()
def delete_repo(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    confirm: bool = typer.Option(
        ...,
        prompt="Are you sure you want to delete this repository? This action cannot be undone.",
        help="Confirm deletion",
    ),
):
    """Delete a GitHub repository."""
    if not confirm:
        logger.info("Operation cancelled")
        return
    params = {"owner": owner, "repo": repo}
    _send_mcp_request("delete_repository", params)
    logger.info(f"Deleted repository {owner}/{repo}")


@github_app.command()
def list_branches(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    protected: bool = typer.Option(None, help="Filter by protection status"),
):
    """List branches in a repository."""
    params = {"owner": owner, "repo": repo, "protected": protected}
    result = _send_mcp_request("list_branches", params)
    if not result:
        logger.info("No branches found")
        return
    rows = [[branch["name"], branch["protected"], branch["commit"]["sha"][:7]] for branch in result]
    print_table(
        ["Name", "Protected", "Latest Commit"],
        rows,
        title=f"Branches in {owner}/{repo}",
    )


@github_app.command()
def get_branch(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    branch: str = typer.Argument(..., help="Branch name"),
):
    """Get details about a specific branch."""
    params = {"owner": owner, "repo": repo, "branch": branch}
    result = _send_mcp_request("get_branch", params)
    print_table(
        ["Field", "Value"],
        [
            ["Name", result["name"]],
            ["Protected", result["protected"]],
            ["Latest Commit", result["commit"]["sha"]],
            ["Latest Commit Message", result["commit"]["commit"]["message"]],
        ],
        title=f"Branch {branch} in {owner}/{repo}",
    )


@github_app.command()
def create_branch(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    branch: str = typer.Argument(..., help="New branch name"),
    source: str = typer.Option("main", help="Source branch or commit SHA"),
):
    """Create a new branch in a repository."""
    params = {"owner": owner, "repo": repo, "branch": branch, "source": source}
    result = _send_mcp_request("create_branch", params)
    logger.info(f"Created branch {branch} from {source}")


@github_app.command()
def delete_branch(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    branch: str = typer.Argument(..., help="Branch name"),
    confirm: bool = typer.Option(
        ...,
        prompt="Are you sure you want to delete this branch?",
        help="Confirm deletion",
    ),
):
    """Delete a branch from a repository."""
    if not confirm:
        logger.info("Operation cancelled")
        return
    params = {"owner": owner, "repo": repo, "branch": branch}
    _send_mcp_request("delete_branch", params)
    logger.info(f"Deleted branch {branch}")


# User commands
@github_app.command()
def get_user(
    username: str = typer.Argument(..., help="GitHub username"),
):
    """Get information about a GitHub user."""
    params = {"username": username}
    result = _send_mcp_request("get_user", params)
    print_table(
        ["Field", "Value"],
        [
            ["Login", result["login"]],
            ["Name", result["name"]],
            ["Company", result["company"]],
            ["Location", result["location"]],
            ["Email", result["email"]],
            ["Bio", result["bio"]],
            ["Public Repos", result["public_repos"]],
            ["Followers", result["followers"]],
            ["Following", result["following"]],
            ["Created", result["created_at"]],
            ["URL", result["html_url"]],
        ],
        title=f"User {username}",
    )


@github_app.command()
def list_user_repos(
    username: str = typer.Argument(..., help="GitHub username"),
    type: str = typer.Option("owner", help="Type of repos (all, owner, member)"),
    sort: str = typer.Option("full_name", help="Sort by (created, updated, pushed, full_name)"),
    direction: str = typer.Option("asc", help="Sort direction (asc, desc)"),
):
    """List repositories owned by a user."""
    params = {
        "username": username,
        "type": type,
        "sort": sort,
        "direction": direction,
    }
    result = _send_mcp_request("list_user_repos", params)
    if not result:
        logger.info("No repositories found")
        return
    rows = [
        [repo["name"], repo["private"], repo["stargazers_count"], repo["forks_count"]]
        for repo in result
    ]
    print_table(
        ["Name", "Private", "Stars", "Forks"],
        rows,
        title=f"Repositories for {username}",
    )


@github_app.command()
def list_user_orgs(
    username: str = typer.Argument(..., help="GitHub username"),
):
    """List organizations a user belongs to."""
    params = {"username": username}
    result = _send_mcp_request("list_user_orgs", params)
    if not result:
        logger.info("No organizations found")
        return
    rows = [[org["login"], org["description"], org["public_repos"]] for org in result]
    print_table(
        ["Name", "Description", "Public Repos"],
        rows,
        title=f"Organizations for {username}",
    )


# Organization commands
@github_app.command()
def get_org(
    org: str = typer.Argument(..., help="Organization name"),
):
    """Get information about a GitHub organization."""
    params = {"org": org}
    result = _send_mcp_request("get_org", params)
    print_table(
        ["Field", "Value"],
        [
            ["Login", result["login"]],
            ["Name", result["name"]],
            ["Description", result["description"]],
            ["Location", result["location"]],
            ["Email", result["email"]],
            ["Public Repos", result["public_repos"]],
            ["Public Members", result["public_members"]],
            ["Created", result["created_at"]],
            ["URL", result["html_url"]],
        ],
        title=f"Organization {org}",
    )


@github_app.command()
def list_org_repos(
    org: str = typer.Argument(..., help="Organization name"),
    type: str = typer.Option(
        "all", help="Type of repos (all, public, private, forks, sources, member)"
    ),
    sort: str = typer.Option("full_name", help="Sort by (created, updated, pushed, full_name)"),
    direction: str = typer.Option("asc", help="Sort direction (asc, desc)"),
):
    """List repositories in an organization."""
    params = {
        "org": org,
        "type": type,
        "sort": sort,
        "direction": direction,
    }
    result = _send_mcp_request("list_org_repos", params)
    if not result:
        logger.info("No repositories found")
        return
    rows = [
        [repo["name"], repo["private"], repo["stargazers_count"], repo["forks_count"]]
        for repo in result
    ]
    print_table(
        ["Name", "Private", "Stars", "Forks"],
        rows,
        title=f"Repositories for {org}",
    )


@github_app.command()
def list_org_members(
    org: str = typer.Argument(..., help="Organization name"),
    role: str = typer.Option("all", help="Filter by role (all, admin, member)"),
):
    """List members of an organization."""
    params = {"org": org, "role": role}
    result = _send_mcp_request("list_org_members", params)
    if not result:
        logger.info("No members found")
        return
    rows = [[member["login"], member["type"], member["site_admin"]] for member in result]
    print_table(
        ["Login", "Type", "Site Admin"],
        rows,
        title=f"Members of {org}",
    )


# Workflow commands
@github_app.command()
def list_workflows(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
):
    """List GitHub Actions workflows in a repository."""
    params = {"owner": owner, "repo": repo}
    result = _send_mcp_request("list_workflows", params)
    if not result:
        logger.info("No workflows found")
        return
    rows = [
        [workflow["name"], workflow["state"], workflow["path"]] for workflow in result["workflows"]
    ]
    print_table(
        ["Name", "State", "Path"],
        rows,
        title=f"Workflows in {owner}/{repo}",
    )


@github_app.command()
def get_workflow(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    workflow_id: str = typer.Argument(..., help="Workflow ID or filename"),
):
    """Get a specific GitHub Actions workflow."""
    params = {"owner": owner, "repo": repo, "workflow_id": workflow_id}
    result = _send_mcp_request("get_workflow", params)
    print_table(
        ["Field", "Value"],
        [
            ["Name", result["name"]],
            ["State", result["state"]],
            ["Path", result["path"]],
            ["Created", result["created_at"]],
            ["Updated", result["updated_at"]],
        ],
        title=f"Workflow {workflow_id}",
    )


@github_app.command()
def list_workflow_runs(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    workflow_id: str = typer.Argument(..., help="Workflow ID or filename"),
    branch: str = typer.Option(None, help="Filter by branch"),
    event: str = typer.Option(None, help="Filter by event type"),
    status: str = typer.Option(None, help="Filter by status"),
):
    """List runs for a specific workflow."""
    params = {
        "owner": owner,
        "repo": repo,
        "workflow_id": workflow_id,
        "branch": branch,
        "event": event,
        "status": status,
    }
    result = _send_mcp_request("list_workflow_runs", params)
    if not result:
        logger.info("No workflow runs found")
        return
    rows = [
        [run["id"], run["head_branch"], run["event"], run["status"], run["conclusion"]]
        for run in result["workflow_runs"]
    ]
    print_table(
        ["ID", "Branch", "Event", "Status", "Conclusion"],
        rows,
        title=f"Runs for workflow {workflow_id}",
    )


@github_app.command()
def get_workflow_run(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    run_id: int = typer.Argument(..., help="Run ID"),
):
    """Get a specific workflow run."""
    params = {"owner": owner, "repo": repo, "run_id": run_id}
    result = _send_mcp_request("get_workflow_run", params)
    print_table(
        ["Field", "Value"],
        [
            ["ID", result["id"]],
            ["Name", result["name"]],
            ["Branch", result["head_branch"]],
            ["Event", result["event"]],
            ["Status", result["status"]],
            ["Conclusion", result["conclusion"]],
            ["Created", result["created_at"]],
            ["Updated", result["updated_at"]],
            ["URL", result["html_url"]],
        ],
        title=f"Workflow Run {run_id}",
    )


@github_app.command()
def rerun_workflow(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    run_id: int = typer.Argument(..., help="Run ID"),
):
    """Rerun a workflow run."""
    params = {"owner": owner, "repo": repo, "run_id": run_id}
    _send_mcp_request("rerun_workflow", params)
    logger.info(f"Triggered rerun of workflow run {run_id}")


# Release commands
@github_app.command()
def list_releases(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
):
    """List releases in a repository."""
    params = {"owner": owner, "repo": repo}
    result = _send_mcp_request("list_releases", params)
    if not result:
        logger.info("No releases found")
        return
    rows = [
        [release["tag_name"], release["name"], release["created_at"], release["draft"]]
        for release in result
    ]
    print_table(
        ["Tag", "Name", "Created", "Draft"],
        rows,
        title=f"Releases in {owner}/{repo}",
    )


@github_app.command()
def get_release(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    release_id: str = typer.Argument(..., help="Release ID or tag name"),
):
    """Get a specific release."""
    params = {"owner": owner, "repo": repo, "release_id": release_id}
    result = _send_mcp_request("get_release", params)
    print_table(
        ["Field", "Value"],
        [
            ["Tag", result["tag_name"]],
            ["Name", result["name"]],
            ["Draft", result["draft"]],
            ["Prerelease", result["prerelease"]],
            ["Created", result["created_at"]],
            ["Published", result["published_at"]],
            ["URL", result["html_url"]],
        ],
        title=f"Release {release_id}",
    )


@github_app.command()
def create_release(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    tag: str = typer.Argument(..., help="Tag name"),
    name: str = typer.Option(None, help="Release name"),
    body: str = typer.Option(None, help="Release description"),
    draft: bool = typer.Option(False, help="Create as draft"),
    prerelease: bool = typer.Option(False, help="Mark as prerelease"),
    target: str = typer.Option(None, help="Target branch or commit SHA"),
):
    """Create a new release."""
    params = {
        "owner": owner,
        "repo": repo,
        "tag": tag,
        "name": name,
        "body": body,
        "draft": draft,
        "prerelease": prerelease,
        "target": target,
    }
    result = _send_mcp_request("create_release", params)
    logger.info(f"Created release {tag}: {result['html_url']}")


# Label commands
@github_app.command()
def list_labels(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
):
    """List labels in a repository."""
    params = {"owner": owner, "repo": repo}
    result = _send_mcp_request("list_labels", params)
    if not result:
        logger.info("No labels found")
        return
    rows = [[label["name"], label["description"], f"#{label['color']}"] for label in result]
    print_table(
        ["Name", "Description", "Color"],
        rows,
        title=f"Labels in {owner}/{repo}",
    )


@github_app.command()
def get_label(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    name: str = typer.Argument(..., help="Label name"),
):
    """Get a specific label."""
    params = {"owner": owner, "repo": repo, "name": name}
    result = _send_mcp_request("get_label", params)
    print_table(
        ["Field", "Value"],
        [
            ["Name", result["name"]],
            ["Description", result["description"]],
            ["Color", f"#{result['color']}"],
        ],
        title=f"Label {name}",
    )


@github_app.command()
def create_label(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    name: str = typer.Argument(..., help="Label name"),
    color: str = typer.Option(..., help="Color (hex without #)"),
    description: str = typer.Option(None, help="Label description"),
):
    """Create a new label."""
    params = {
        "owner": owner,
        "repo": repo,
        "name": name,
        "color": color,
        "description": description,
    }
    result = _send_mcp_request("create_label", params)
    logger.info(f"Created label {name}")


@github_app.command()
def update_label(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    name: str = typer.Argument(..., help="Current label name"),
    new_name: str = typer.Option(None, help="New label name"),
    color: str = typer.Option(None, help="New color (hex without #)"),
    description: str = typer.Option(None, help="New description"),
):
    """Update a label."""
    params = {
        "owner": owner,
        "repo": repo,
        "name": name,
        "new_name": new_name,
        "color": color,
        "description": description,
    }
    result = _send_mcp_request("update_label", params)
    logger.info(f"Updated label {name}")


@github_app.command()
def delete_label(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    name: str = typer.Argument(..., help="Label name"),
    confirm: bool = typer.Option(
        ...,
        prompt="Are you sure you want to delete this label?",
        help="Confirm deletion",
    ),
):
    """Delete a label."""
    if not confirm:
        logger.info("Operation cancelled")
        return
    params = {"owner": owner, "repo": repo, "name": name}
    _send_mcp_request("delete_label", params)
    logger.info(f"Deleted label {name}")


# Milestone commands
@github_app.command()
def list_milestones(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    state: str = typer.Option("open", help="State (open, closed, all)"),
    sort: str = typer.Option("due_on", help="Sort by (due_on, completeness)"),
    direction: str = typer.Option("asc", help="Sort direction (asc, desc)"),
):
    """List milestones in a repository."""
    params = {
        "owner": owner,
        "repo": repo,
        "state": state,
        "sort": sort,
        "direction": direction,
    }
    result = _send_mcp_request("list_milestones", params)
    if not result:
        logger.info("No milestones found")
        return
    rows = [
        [
            milestone["number"],
            milestone["title"],
            milestone["state"],
            milestone["due_on"],
            f"{milestone['closed_issues']}/{milestone['open_issues'] + milestone['closed_issues']}",
        ]
        for milestone in result
    ]
    print_table(
        ["Number", "Title", "State", "Due Date", "Progress"],
        rows,
        title=f"Milestones in {owner}/{repo}",
    )


@github_app.command()
def get_milestone(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Milestone number"),
):
    """Get a specific milestone."""
    params = {"owner": owner, "repo": repo, "number": number}
    result = _send_mcp_request("get_milestone", params)
    print_table(
        ["Field", "Value"],
        [
            ["Number", result["number"]],
            ["Title", result["title"]],
            ["Description", result["description"]],
            ["State", result["state"]],
            ["Due Date", result["due_on"]],
            ["Created", result["created_at"]],
            ["Updated", result["updated_at"]],
            ["Open Issues", result["open_issues"]],
            ["Closed Issues", result["closed_issues"]],
        ],
        title=f"Milestone {number}",
    )


@github_app.command()
def create_milestone(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    title: str = typer.Argument(..., help="Milestone title"),
    description: str = typer.Option(None, help="Milestone description"),
    due_on: str = typer.Option(None, help="Due date (YYYY-MM-DD)"),
):
    """Create a new milestone."""
    params = {
        "owner": owner,
        "repo": repo,
        "title": title,
        "description": description,
        "due_on": due_on,
    }
    result = _send_mcp_request("create_milestone", params)
    logger.info(f"Created milestone {title} (#{result['number']})")


@github_app.command()
def update_milestone(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Milestone number"),
    title: str = typer.Option(None, help="New title"),
    description: str = typer.Option(None, help="New description"),
    due_on: str = typer.Option(None, help="New due date (YYYY-MM-DD)"),
    state: str = typer.Option(None, help="New state (open, closed)"),
):
    """Update a milestone."""
    params = {
        "owner": owner,
        "repo": repo,
        "number": number,
        "title": title,
        "description": description,
        "due_on": due_on,
        "state": state,
    }
    result = _send_mcp_request("update_milestone", params)
    logger.info(f"Updated milestone #{number}")


@github_app.command()
def delete_milestone(
    owner: str = typer.Argument(..., help="Repository owner"),
    repo: str = typer.Argument(..., help="Repository name"),
    number: int = typer.Argument(..., help="Milestone number"),
    confirm: bool = typer.Option(
        ...,
        prompt="Are you sure you want to delete this milestone?",
        help="Confirm deletion",
    ),
):
    """Delete a milestone."""
    if not confirm:
        logger.info("Operation cancelled")
        return
    params = {"owner": owner, "repo": repo, "number": number}
    _send_mcp_request("delete_milestone", params)
    logger.info(f"Deleted milestone #{number}")
