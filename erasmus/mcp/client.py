from erasmus.utils.rich_console import get_console_logger
from erasmus.mcp.mcp import MCPError
from erasmus.mcp.servers import McpServers
from pathlib import Path
from typing import Any
import subprocess
import os
import time # Added import
from subprocess import PIPE
logger = get_console_logger()


class MCPClient:
    """Client for interacting with MCP servers."""

    def __init__(self):
        """Initialize the MCP client."""
        self.mcp_servers = McpServers()
        self.processes: dict[str, subprocess.Popen] = {} # Store active processes

    def get_servers(self) -> dict[str, McpServers]:
        """Get the MCP servers."""
        return self.mcp_servers.get_servers()

    def get_server_names(self) -> list[str]:
        """Get the names of the MCP servers."""
        return self.mcp_servers.get_server_names()

    def get_server_paths(self) -> dict[str, Path]:
        """Get the paths of the MCP servers."""
        return self.mcp_servers.get_server_paths()

    def _get_server_command(self, server_name: str) -> list[str]:
        """Get the command of the MCP server."""
        server = self.mcp_servers.get_server(server_name)
        command = []
        if server.command:
            command.append(server.command)
        if server.args:
            command.extend(server.args)
        return command

    def _load_env_vars(self, env: dict[str, str]) -> None:
        """Load the environment variables for the MCP server."""
        self.mcp_servers.load_environment_variables(env)


    def connect(self, server_name: str) -> None:
        """Connect to the MCP server.

        Raises:
            MCPError: If connection fails
        """
        if server_name not in self.get_server_names():
            logger.error(f"Server '{server_name}' not found\nAvailable servers: {self.get_server_names()}\n")
            raise MCPError(f"Server '{server_name}' not found")
        try:
            server = self.mcp_servers.get_server(server_name)
            self._load_env_vars(server.env)
            command = self._get_server_command(server_name)
            process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, env=os.environ.copy())
            time.sleep(0.5) # Give the process a moment to start or fail
            return_code = process.poll()
            if return_code is not None: # Check if it terminated
                stderr_output = process.stderr.read().decode().strip()
                if return_code != 0:
                    error_msg = f"Failed to start MCP server '{server_name}'. Exit code: {return_code}. Error: {stderr_output}"
                    logger.error(error_msg)
                    raise MCPError(error_msg)
                else:
                    # Exited cleanly but too quickly - suspicious for a server
                    warning_msg = f"MCP server '{server_name}' started but exited immediately with code 0. Stderr: {stderr_output}"
                    logger.warning(warning_msg)
                    # Don't raise error, but process handle won't be stored for this server
                    return # Exit connect method for this server
            
            logger.info(f"Successfully started MCP server process for '{server_name}'")
            self.processes[server_name] = process # Store the process handle
            self.connected = True # Assuming connection if process is running
            # TODO: Implement actual communication/health check

        except Exception as e:
            raise MCPError(f"Failed to connect to MCP server: {e}")

    def disconnect(self) -> None:
        """Disconnect from the MCP server.

        Raises:
            MCPError: If disconnection fails
        """
        try:
            # TODO: Implement actual disconnection logic
            logger.info(f"Disconnecting from MCP server at {self.server_url}")
            self.connected = False
        except Exception as e:
            raise MCPError(f"Failed to disconnect from MCP server: {e}")

    def send_request(self, request_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Send a request to the MCP server.

        Args:
            request_type: Type of request to send
            data: Request data

        Returns:
            Response from the server

        Raises:
            MCPError: If request fails
        """
        if not self.connected:
            raise MCPError("Not connected to MCP server")

        try:
            # TODO: Implement actual request logic
            logger.info(f"Sending {request_type} request to MCP server")
            return {"status": "success", "data": {}}
        except Exception as e:
            raise MCPError(f"Failed to send request to MCP server: {e}")


if __name__ == "__main__":
    client = MCPClient()
    # logger.info(client.get_server_names())
    # logger.info(client.get_server_paths())
    # logger.info(client.get_servers())
    # logger.info(client._get_server_command("github"))
    client.connect("github")
    # client.disconnect()