"""
MCP CLI commands for managing MCP servers and clients.
"""

import typer
from pathlib import Path
from loguru import logger
from erasmus.mcp.mcp import MCPClient, MCPServer, MCPRegistry, MCPError
from erasmus.utils.rich_console import print_table
from erasmus.cli.github_mcp_commands import github_app

mcp_registry = MCPRegistry()
mcp_app = typer.Typer(help="Manage MCP servers and clients.")


def show_mcp_help_and_exit():
    """Show help menu and exit with error code."""
    command_rows = [
        ["erasmus mcp server start", "Start an MCP server"],
        ["erasmus mcp server stop", "Stop an MCP server"],
        ["erasmus mcp server register", "Register a new MCP server"],
        ["erasmus mcp server unregister", "Unregister an MCP server"],
        ["erasmus mcp server list", "List all registered servers"],
        ["erasmus mcp client connect", "Connect to an MCP server"],
        ["erasmus mcp client disconnect", "Disconnect from an MCP server"],
        ["erasmus mcp client register", "Register a new MCP client"],
        ["erasmus mcp client unregister", "Unregister an MCP client"],
        ["erasmus mcp client list", "List all registered clients"],
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
            ["erasmus mcp client", "Manage MCP clients"],
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
    host: str = typer.Option("localhost", help="Host to bind the server to"),
    port: int = typer.Option(8080, help="Port to bind the server to"),
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
        server_info = mcp_registry.get_server(name)
        if not server_info:
            # Register the server
            mcp_registry.register_server(name, host, port)
            logger.info(f"Registered server: {name}")

        # Start the server
        server = MCPServer(host, port)
        server.start()
        logger.info(f"Started server: {name} on {host}:{port}")
        show_mcp_help_and_exit()
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
        server_info = mcp_registry.get_server(name)
        if not server_info:
            raise MCPError(f"Server '{name}' not registered")

        # Stop the server
        server = MCPServer(server_info["host"], server_info["port"])
        server.stop()
        logger.info(f"Stopped server: {name}")
        show_mcp_help_and_exit()
    except MCPError as e:
        logger.error(f"Failed to stop server: {e}")
        show_mcp_help_and_exit()


@server_app.command()
def register(
    name: str = typer.Argument(None, help="Name of the server to register"),
    host: str = typer.Option("localhost", help="Host the server is running on"),
    port: int = typer.Option(8080, help="Port the server is running on"),
):
    """Register a new MCP server."""
    try:
        if not name:
            name = typer.prompt("Enter the server name")
        if not name:
            typer.echo("Error: Server name is required.")
            raise typer.Exit(1)
        mcp_registry.register_server(name, host, port)
        typer.echo(f"Registered server: {name}")
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
        mcp_registry.unregister_server(name)
        typer.echo(f"Unregistered server: {name}")
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
        servers = mcp_registry.list_servers()
        if not servers:
            typer.echo("No servers registered")
            return

        # Display servers in a table
        server_rows = []
        for server_name in servers:
            server_info = mcp_registry.get_server(server_name)
            server_rows.append([server_name, server_info["host"], server_info["port"]])
        print_table(["Server Name", "Host", "Port"], server_rows, title="Registered MCP Servers")
    except MCPError as e:
        logger.error(f"Failed to list servers: {e}")
        show_mcp_help_and_exit()


# Client commands
client_app = typer.Typer(help="Manage MCP clients.")
mcp_app.add_typer(client_app, name="client")


@client_app.command()
def connect(
    name: str = typer.Argument(None, help="Name of the client to connect"),
    server_name: str = typer.Argument(None, help="Name of the server to connect to"),
):
    """Connect to an MCP server.

    This command connects a client to an MCP server.
    If the client is not registered, it will be registered automatically.
    """
    try:
        if not name:
            name = typer.prompt("Enter the client name")
        if not name:
            typer.echo("Error: Client name is required.")
            raise typer.Exit(1)
        if not server_name:
            server_name = typer.prompt("Enter the server name to connect to")
        if not server_name:
            typer.echo("Error: Server name is required.")
            raise typer.Exit(1)
        # Check if server is registered
        server_info = mcp_registry.get_server(server_name)
        if not server_info:
            raise MCPError(f"Server '{server_name}' not registered")

        # Check if client is registered
        client_info = mcp_registry.get_client(name)
        if not client_info:
            # Register the client
            mcp_registry.register_client(name, server_name)
            logger.info(f"Registered client: {name}")

        # Connect to the server
        server_url = f"http://{server_info['host']}:{server_info['port']}"
        client = MCPClient(server_url)
        client.connect()
        logger.info(f"Connected client: {name} to server: {server_name}")
        show_mcp_help_and_exit()
    except MCPError as e:
        logger.error(f"Failed to connect client: {e}")
        show_mcp_help_and_exit()


@client_app.command()
def disconnect(
    name: str = typer.Argument(..., help="Name of the client to disconnect"),
):
    """Disconnect from an MCP server.

    This command disconnects a client from an MCP server.
    """
    try:
        # Check if client is registered
        client_info = mcp_registry.get_client(name)
        if not client_info:
            raise MCPError(f"Client '{name}' not registered")

        # Get server information
        server_name = client_info["server"]
        server_info = mcp_registry.get_server(server_name)
        if not server_info:
            raise MCPError(f"Server '{server_name}' not registered")

        # Disconnect from the server
        server_url = f"http://{server_info['host']}:{server_info['port']}"
        client = MCPClient(server_url)
        client.disconnect()
        logger.info(f"Disconnected client: {name} from server: {server_name}")
        show_mcp_help_and_exit()
    except MCPError as e:
        logger.error(f"Failed to disconnect client: {e}")
        show_mcp_help_and_exit()


@client_app.command()
def register(
    name: str = typer.Argument(None, help="Name of the client to register"),
    server_name: str = typer.Argument(None, help="Name of the server the client is connected to"),
):
    """Register a new MCP client.

    This command registers a new MCP client with the specified name and server.
    """
    try:
        if not name:
            name = typer.prompt("Enter the client name")
        if not name:
            typer.echo("Error: Client name is required.")
            raise typer.Exit(1)
        if not server_name:
            server_name = typer.prompt("Enter the server name the client is connected to")
        if not server_name:
            typer.echo("Error: Server name is required.")
            raise typer.Exit(1)
        mcp_registry.register_client(name, server_name)
        logger.info(f"Registered client: {name} to server: {server_name}")
        show_mcp_help_and_exit()
    except MCPError as e:
        logger.error(f"Failed to register client: {e}")
        show_mcp_help_and_exit()


@client_app.command()
def unregister(
    name: str = typer.Argument(None, help="Name of the client to unregister"),
):
    """Unregister an MCP client.

    This command unregisters an MCP client with the specified name.
    """
    try:
        if not name:
            name = typer.prompt("Enter the client name")
        if not name:
            typer.echo("Error: Client name is required.")
            raise typer.Exit(1)
        mcp_registry.unregister_client(name)
        logger.info(f"Unregistered client: {name}")
        show_mcp_help_and_exit()
    except MCPError as e:
        logger.error(f"Failed to unregister client: {e}")
        show_mcp_help_and_exit()


@client_app.command()
def list():
    """List all registered MCP clients.

    This command lists all registered MCP clients and their information.
    """
    try:
        clients = mcp_registry.list_clients()
        if not clients:
            typer.echo("No clients registered")
            return

        # Display clients in a table
        client_rows = []
        for client_name in clients:
            client_info = mcp_registry.get_client(client_name)
            client_rows.append([client_name, client_info["server"]])
        print_table(
            ["Client Name", "Connected Server"],
            client_rows,
            title="Registered MCP Clients",
        )
    except MCPError as e:
        logger.error(f"Failed to list clients: {e}")
        show_mcp_help_and_exit()


@mcp_app.command("select-server")
def select_server():
    """Interactively select an MCP server and display its details."""
    try:
        servers = mcp_registry.list_servers()
        if not servers:
            typer.echo("No servers found to select.")
            raise typer.Exit(1)
        # Display servers in a table
        server_rows = [[str(index + 1), server_name] for index, server_name in enumerate(servers)]
        print_table(["#", "Server Name"], server_rows, title="Registered MCP Servers")
        choice = typer.prompt("Select a server by number or name")
        selected = None
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(servers):
                selected = servers[index - 1]
        else:
            if choice in servers:
                selected = choice
        if not selected:
            typer.echo(f"Error: Invalid selection: {choice}")
            raise typer.Exit(1)
        server_info = mcp_registry.get_server(selected)
        if not server_info:
            typer.echo(f"Error: Server not found: {selected}")
            raise typer.Exit(1)
        typer.echo(f"Selected server: {selected}")
        typer.echo(f"Host: {server_info['host']}")
        typer.echo(f"Port: {server_info['port']}")
        raise typer.Exit(0)
    except MCPError as exception:
        typer.echo(f"Error: Failed to select server: {exception}")
        raise typer.Exit(1)


@mcp_app.command("select-client")
def select_client():
    """Interactively select an MCP client and display its details."""
    try:
        clients = mcp_registry.list_clients()
        if not clients:
            typer.echo("No clients found to select.")
            raise typer.Exit(1)
        # Display clients in a table
        client_rows = [[str(index + 1), client_name] for index, client_name in enumerate(clients)]
        print_table(["#", "Client Name"], client_rows, title="Registered MCP Clients")
        choice = typer.prompt("Select a client by number or name")
        selected = None
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(clients):
                selected = clients[index - 1]
        else:
            if choice in clients:
                selected = choice
        if not selected:
            typer.echo(f"Error: Invalid selection: {choice}")
            raise typer.Exit(1)
        client_info = mcp_registry.get_client(selected)
        if not client_info:
            typer.echo(f"Error: Client not found: {selected}")
            raise typer.Exit(1)
        typer.echo(f"Selected client: {selected}")
        typer.echo(f"Connected server: {client_info['server']}")
        raise typer.Exit(0)
    except MCPError as exception:
        typer.echo(f"Error: Failed to select client: {exception}")
        raise typer.Exit(1)


if __name__ == "__main__":
    try:
        mcp_app()
    except Exception as error:
        print_table(["Error"], [[str(error)]], title="CLI Error")
        raise typer.Exit(1)
