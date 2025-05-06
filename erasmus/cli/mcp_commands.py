"""
MCP CLI commands for managing MCP servers and clients.
"""

import typer
from pathlib import Path
from loguru import logger
from erasmus.mcp.mcp import MCPRegistry, MCPError
from erasmus.mcp.servers import McpServers
from erasmus.mcp.client import StdioClient
from erasmus.utils.rich_console import print_table
from erasmus.cli.github_mcp_commands import github_app

mcp_registry = MCPRegistry()
mcp_servers = McpServers()
mcp_client = StdioClient()
mcp_app = typer.Typer(help="Manage MCP servers and clients.")


def show_mcp_help_and_exit():
    """Show help menu and exit with error code."""
    command_rows = [
        ["erasmus mcp server start", "Start an MCP server"],
        ["                   stop", "Stop an MCP server"],
        ["                   register", "Register a new MCP server"],
        ["                   unregister", "Unregister an MCP server"],
        ["                   list", "List all registered servers"],
        ["                                                      "],
        ["erasmus mcp client connect", "Connect to an MCP server"],
        ["                   disconnect", "Disconnect from an MCP server"],
        ["                   register", "Register a new MCP client"],
        ["                   unregister", "Unregister an MCP client"],
        ["                   list", "List all registered clients"],
    ]
    print_table(["Command", "Description"], command_rows, title="Available MCP Commands")
    typer.echo("\nFor more information about a command, run:")
    typer.echo("  erasmus mcp <command> --help")
    raise typer.Exit(1)


@mcp_app.callback(invoke_without_command=True)
def mcp_callback(ctx: typer.Context):
    """
    Manage MCP servers and clients.
    """
    if ctx.invoked_subcommand is None:
        command_rows = [
            ["erasmus mcp server", "Manage MCP servers"],
            ["            client", "Manage MCP clients"],
        ]
        print_table(["Command", "Description"], command_rows, title="Available MCP Commands")
        typer.echo("\nFor more information about a command, run:")
        typer.echo("  erasmus mcp <command> --help")
        raise typer.Exit(0)


# Server commands
server_app = typer.Typer(help="Manage MCP servers.")
server_app.add_typer(github_app, name="github", help="Manage GitHub through the MCP server.")
mcp_app.add_typer(server_app, name="server")


@server_app.command()
def start(
    name: str = typer.Argument(None, help="Name of the server to start"),
    host: str | None = typer.Option(None, help="Host to bind the server to"),
    port: int | None = typer.Option(None, help="Port to bind the server to"),
):
    """Start an MCP server.

    This command starts an MCP server with the specified name, host, and port.
    If the server is not registered, it will be registered automatically.
    """
    try:
        if not name:
            name = typer.prompt("Enter the server name")
        if not name:
            typer.echo("Error: Server name is required.")
            raise typer.Exit(1)
        # Check if server is registered
        if not name in mcp_servers.get_server_names():
            raise MCPError(f"Server '{name}' not registered")
        server_info = mcp_servers.get_server(name)
        if not mcp_client.connect(name, server_info["host"], server_info["port"]):
            raise MCPError(f"Failed to connect to server '{name}'")
        typer.echo(f"Connected to server: {name}")
        raise typer.Exit(0)
    except MCPError as e:
        logger.error(f"Failed to start server: {e}")
        show_mcp_help_and_exit()


@server_app.command()
def stop(name: str = typer.Argument(None, help="Name of the server to stop")):
    """Stop an MCP server.

    This command stops an MCP server with the specified name.
    """
    try:
        if not name:
            name = typer.prompt("Enter the server name")
        if not name:
            typer.echo("Error: Server name is required.")
            raise typer.Exit(1)
        # Check if server is registered
        server_info = mcp_servers.get_server(name)
        if not server_info:
            raise MCPError(f"Server '{name}' not registered")

        # Stop the server
        mcp_client.disconnect(name)
        logger.info(f"Stopped server: {name}")
        show_mcp_help_and_exit()
    except MCPError as e:
        logger.error(f"Failed to stop server: {e}")
        show_mcp_help_and_exit()


@server_app.command()
def register(
    name: str = typer.Argument(None, help="Name of the server to register"),
    host: str | None = typer.Option(None, help="Host the server is running on"),
    port: int | None = typer.Option(None, help="Port the server is running on"),
):
    """Register a new MCP server."""
    try:
        if not name:
            name = typer.prompt("Enter the server name")
        if not name:
            typer.echo("Error: Server name is required.")
            raise typer.Exit(1)
        typer.echo("TODO: Implement Registry for MCP servers.")
        raise typer.Exit(0)
    except MCPError as e:
        typer.echo(f"Error: Failed to register server: {e}")
        raise typer.Exit(1)


@server_app.command()
def unregister(
    name: str = typer.Argument(None, help="Name of the server to unregister"),
):
    """Unregister an MCP server."""
    try:
        if not name:
            name = typer.prompt("Enter the server name")
        if not name:
            typer.echo("Error: Server name is required.")
            raise typer.Exit(1)
        typer.echo("TODO: Implement Registry for MCP servers.")
        raise typer.Exit(0)
    except MCPError as e:
        typer.echo(f"Error: Failed to unregister server: {e}")
        raise typer.Exit(1)


@server_app.command()
def list():
    """List all registered MCP servers.

    This command lists all registered MCP servers and their information.
    """
    try:
        servers = mcp_servers.get_server_names()
        if not servers:
            typer.echo("No servers registered")
            return

        # Display servers in a table
        server_rows = []
        for server_name in servers:
            server_info = mcp_servers.get_server(server_name)
            server_rows.append([server_name])
        print_table(["Server Name"], server_rows, title="Registered MCP Servers")
    except MCPError as e:
        typer.echo(f"Error: Failed to list servers: {e}")
        raise typer.Exit(1)

if __name__ == "__main__":
    try:
        mcp_app()
    except Exception as error:
        print_table(["Error"], [[str(error)]], title="CLI Error")
        raise typer.Exit(1)
