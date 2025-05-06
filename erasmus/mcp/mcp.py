"""
Model Context Protocol (MCP) functionality for Erasmus.
"""

import os
import json
from typing import Any
from loguru import logger




# This has been depreciated
class MCPServer:
    """Server for handling MCP requests."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        """Initialize the MCP server.

        Args:
            host: Host to bind the server to
            port: Port to bind the server to
        """
        logger.warning("MCPServer is depreciated. Use erasmus.mcp.servers.McpServers instead.")
        self.host = host
        self.port = port
        self.running = False

    def start(self) -> None:
        """Start the MCP server.

        Raises:
            McpError: If server start fails
        """
        try:
            # TODO: Implement actual server start logic
            logger.info(f"Starting MCP server on {self.host}:{self.port}")
            self.running = True
        except Exception as error:
            raise McpError(f"Failed to start MCP server: {error}")

    def stop(self) -> None:
        """Stop the MCP server.

        Raises:
            McpError: If server stop fails
        """
        try:
            # TODO: Implement actual server stop logic
            logger.info(f"Stopping MCP server on {self.host}:{self.port}")
            self.running = False
        except Exception as error:
            raise McpError(f"Failed to stop MCP server: {error}")

    def process_request(self, request_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Process a request from an MCP client.

        Args:
            request_type: Type of request to process
            data: Request data

        Returns:
            Response to send to the client

        Raises:
            McpError: If request processing fails
        """
        if not self.running:
            raise McpError("MCP server is not running")

        try:
            # TODO: Implement actual request processing logic
            logger.info(f"Processing {request_type} request")
            return {"status": "success", "data": {}}
        except Exception as error:
            raise McpError(f"Failed to process request: {error}")


# This has been depreciated. Use erasmus.mcp.registry.MCPRegistry instead.
class MCPRegistry:
    """
    Registry for MCP servers and clients.

    This class manages the registration and retrieval of MCP servers and clients.
    It provides functionality to register, unregister, and list servers and clients.
    The registry data is persisted to a JSON file.
    """

    def __init__(self, registry_file: str = None):
        logger.warning("The MCPRegistry class in erasmus.mcp.mcp is deprecated. Use erasmus.mcp.registry.MCPRegistry instead.")
        """
        Initialize the MCP registry.

        Args:
            registry_file: Path to the registry file. If None, a default path is used.
        """
        if registry_file is None:
            # Use a default path in the user's home directory
            home_dir = os.path.expanduser("~")
            self.registry_file = os.path.join(home_dir, ".erasmus", "mcp_registry.json")
        else:
            self.registry_file = registry_file

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)

        # Initialize the registry data (start fresh in-memory)
        self._load_registry()
        # Ensure clean state for servers and clients (ignore persisted file)
        self.registry = {"servers": {}, "clients": {}}

    def _load_registry(self) -> None:
        """Load the registry data from the registry file."""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r") as f:
                    self.registry = json.load(f)
            except json.JSONDecodeError:
                # If the file is corrupted, start with an empty registry
                self.registry = {"servers": {}, "clients": {}}
        else:
            # If the file doesn't exist, start with an empty registry
            self.registry = {"servers": {}, "clients": {}}

    def _save_registry(self) -> None:
        """Save the registry data to the registry file."""
        with open(self.registry_file, "w") as f:
            json.dump(self.registry, f, indent=2)

    def register_server(self, name: str, host: str, port: int) -> None:
        """
        Register a new MCP server.

        Args:
            name: The name of the server.
            host: The host address of the server.
            port: The port number of the server.

        Raises:
            McpError: If a server with the same name is already registered.
        """
        if name in self.registry["servers"]:
            raise McpError(f"Server '{name}' already registered")

        self.registry["servers"][name] = {"host": host, "port": port}
        self._save_registry()

    def unregister_server(self, name: str) -> None:
        """
        Unregister an MCP server.

        Args:
            name: The name of the server to unregister.

        Raises:
            McpError: If the server is not found.
        """
        if name not in self.registry["servers"]:
            raise McpError(f"Server '{name}' not registered")

        # Remove any clients that were connected to this server
        clients_to_remove = []
        for client_name, client_data in self.registry["clients"].items():
            if client_data["server"] == name:
                clients_to_remove.append(client_name)

        for client_name in clients_to_remove:
            del self.registry["clients"][client_name]

        # Remove the server
        del self.registry["servers"][name]
        self._save_registry()

    def get_server(self, name: str) -> dict[str, Any] | None:
        """
        Get the details of a registered MCP server.

        Args:
            name: The name of the server.

        Returns:
            A dictionary containing the server details, or None if not found.
        """
        return self.registry.get("servers", {}).get(name)

    def list_servers(self) -> list[str]:
        """
        List all registered MCP servers.

        Returns:
            A list of server names.
        """
        return list(self.registry["servers"].keys())

    def register_client(self, name: str, server: str) -> None:
        """
        Register a new MCP client.

        Args:
            name: The name of the client.
            server: The name of the server the client connects to.

        Raises:
            McpError: If a client with the same name is already registered,
                     or if the specified server is not found.
        """
        if name in self.registry["clients"]:
            raise McpError(f"Client '{name}' already registered")

        if server not in self.registry["servers"]:
            raise McpError(f"Server '{server}' not registered")

        self.registry["clients"][name] = {"server": server}
        self._save_registry()

    def unregister_client(self, name: str) -> None:
        """
        Unregister an MCP client.

        Args:
            name: The name of the client to unregister.

        Raises:
            McpError: If the client is not found.
        """
        if name not in self.registry["clients"]:
            raise McpError(f"Client '{name}' not registered")

        del self.registry["clients"][name]
        self._save_registry()

    def get_client(self, name: str) -> dict[str, any] | None:
        """
        Get the details of a registered MCP client.

        Args:
            name: The name of the client.

        Returns:
            A dictionary containing the client details, or None if not found.
        """
        return self.registry.get("clients", {}).get(name)

    def list_clients(self) -> list[str]:
        """
        List all registered MCP clients.

        Returns:
            A list of client names.
        """
        return list(self.registry["clients"].keys())

    @property
    def servers(self) -> dict[str, Any]:
        """Dictionary of registered MCP servers."""
        return self.registry.get("servers", {})

    @property
    def clients(self) -> dict[str, Any]:
        """Dictionary of registered MCP clients."""
        return self.registry.get("clients", {})
