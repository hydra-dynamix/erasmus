from erasmus.utils.rich_console import get_console_logger
from erasmus.mcp.mcp import MCPError
from erasmus.mcp.servers import McpServers
from erasmus.mcp.models import RPCRequest, ServerTransport
from typing import Any
import subprocess
import os
import json
import time
import io

from subprocess import PIPE
from pydantic import ConfigDict

logger = get_console_logger()


class StdioClient:
    """Client for interacting with MCP servers over standard input/output.

    Manages subprocesses for MCP servers defined in a configuration file,
    starts them on demand, and handles JSON-RPC 2.0 communication
    over their stdin/stdout.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self):
        """Initialize the StdioClient.

        Loads server definitions and prepares to manage server processes.
        """
        self.mcp_servers = McpServers()
        self.transports: dict[str, ServerTransport] = {} # Store active transports
        self._request_id_counter = 0 # Counter for JSON-RPC request IDs
        logger.debug("StdioClient initialized.")

    def get_servers(self) -> dict[str, McpServers]:
        """Get the MCP servers defined in the configuration.

        Returns:
            A dictionary containing the server definitions.
        """
        return self.mcp_servers.servers

    def _get_server_command(self, server_name: str) -> list[str]:
        """Construct the command list to launch a specific MCP server.

        Args:
            server_name: The name of the server.

        Returns:
            A list of strings representing the command and its arguments.

        Raises:
            MCPError: If the server definition is not found.
        """
        server = self.mcp_servers.servers.get(server_name)
        if not server:
            raise MCPError(f"Server '{server_name}' not found in configuration.")
        command = [server.command] + server.args
        logger.debug(f"Constructed command for '{server_name}': {command}")
        return command

    def _load_env_vars(self, env: dict[str, str]):
        """Load environment variables required by the server into the current environment.

        Args:
            env: A dictionary of environment variables to set.
        """
        logger.debug(f"Loading environment variables: {env.keys()}")
        for key, value in env.items():
            os.environ[key] = value

    def connect(self, server_name: str) -> bool:
        """Connect to a specific MCP server by starting its process.

        If the server process is already running, this method does nothing.
        Otherwise, it attempts to launch the server subprocess using the
        configured command and environment variables.

        Args:
            server_name: The name of the server to connect to.

        Returns:
            True if the connection is established or already exists, False otherwise.

        Raises:
            MCPError: If there's an issue starting the server process or configuration is missing.
        """
        if server_name in self.transports and self.transports[server_name].process.poll() is None:
            logger.info(f"Already connected to MCP server '{server_name}'.")
            return True

        logger.info(f"Attempting to connect to MCP server '{server_name}'...")
        try:
            server = self.mcp_servers.servers.get(server_name)
            if not server:
                raise MCPError(f"Server '{server_name}' definition not found.")

            self._load_env_vars(server.env)
            command = self._get_server_command(server_name)
            try:
                process = subprocess.Popen(
                    command,
                    stdin=PIPE,
                    stdout=PIPE,
                    stderr=PIPE,
                    env=os.environ.copy(),
                    text=True, # Use text mode for automatic encoding/decoding
                    bufsize=1  # Line buffered
                )
                # Short sleep to allow process to initialize, might need adjustment
                time.sleep(0.5)

                if process.poll() is not None:
                    # Process terminated unexpectedly quickly
                    stderr_output = ""
                    try:
                        # Try reading stderr, might hang if process is weird
                         stderr_output = process.stderr.read()
                    except Exception:
                         pass # Ignore errors reading stderr from dead process
                    logger.error(f"MCP server '{server_name}' terminated immediately. Exit code: {process.returncode}. Stderr: {stderr_output.strip()}")
                    return False

                # Check if streams are valid TextIOWrapper instances
                if not isinstance(process.stdin, io.TextIOWrapper) or \
                   not isinstance(process.stdout, io.TextIOWrapper) or \
                   not isinstance(process.stderr, io.TextIOWrapper):
                    raise MCPError("Failed to get valid TextIOWrapper streams for process.")

                transport = ServerTransport(
                    name=server_name,
                    process=process,
                    connected=True,
                    stdin=process.stdin,
                    stdout=process.stdout,
                    stderr=process.stderr
                    )
                self.transports[server_name] = transport
                logger.info(f"Successfully connected to MCP server '{server_name}'.")
                return True

            except FileNotFoundError:
                 logger.error(f"Failed to start MCP server '{server_name}': Command not found ('{command[0]}'). Ensure it's in the system PATH.")
                 return False
            except Exception as e:
                logger.error(f"Failed to start MCP server '{server_name}': {e}", exc_info=True)
                return False

        except Exception as e:
            raise MCPError(f"Failed to connect to MCP server '{server_name}': {e}")

    def disconnect(self, server_name: str):
         """Disconnect from a specific MCP server by terminating its process.

         Args:
            server_name: The name of the server to disconnect from.
         """
         if server_name in self.transports:
             transport = self.transports[server_name]
             process = transport.process
             logger.info(f"Disconnecting from MCP server '{server_name}'...")
             if process.poll() is None: # Check if still running
                 try:
                     process.terminate()
                     process.wait(timeout=2) # Wait briefly
                     logger.info(f"MCP server '{server_name}' terminated.")
                 except subprocess.TimeoutExpired:
                     logger.warning(f"MCP server '{server_name}' did not terminate gracefully, killing.")
                     process.kill()
                 except Exception as e:
                     logger.error(f"Error terminating server '{server_name}': {e}")
             else:
                 logger.info(f"MCP server '{server_name}' was already stopped.")
             del self.transports[server_name]
         else:
             logger.warning(f"Not connected to MCP server '{server_name}', cannot disconnect.")

    def disconnect_all(self):
         """Disconnect from all currently connected MCP servers."""
         server_names = list(self.transports.keys())
         logger.info(f"Disconnecting from all servers: {server_names}")
         for server_name in server_names:
             self.disconnect(server_name)

    def communicate(self, server_name: str, method: str, params: dict[str, Any] | list[Any]) -> tuple[str, str]:
        """Send a single JSON-RPC request to an MCP server using subprocess.communicate.

        This method starts a new server process for the request, sends the request
        data to its stdin, and reads the entire stdout and stderr streams until
        the process terminates. It then returns the captured stdout and stderr.

        Note: This is suitable for single-shot interactions but inefficient for
        multiple requests to the same server, as it incurs process startup/shutdown
        overhead for each call. For persistent connections, use send_request (if
        the server correctly handles newline-terminated responses on stdout).

        Args:
            server_name: The name of the configured MCP server to communicate with.
            method: The JSON-RPC method name to call.
            params: The parameters for the JSON-RPC method.

        Returns:
            A tuple containing the captured stdout and stderr strings from the
            server process.

        Raises:
            MCPError: If the server name is not found in the configuration.
            Exception: Can raise exceptions from subprocess.Popen or communicate.
        """
        if server_name not in self.mcp_servers.servers:
            raise MCPError(f"Server '{server_name}' not found in configuration.")
        
        # Although connect() is called internally by _get_server_command,
        # calling it here ensures the transport exists if needed later,
        # though this method doesn't use the persistent transport.
        # We might reconsider if connect() should be called here.
        # self.connect(server_name) # Currently redundant as Popen is used directly

        server = self.mcp_servers.servers[server_name]
        command = [server.command] + server.args # Logging flags should be in config if needed
        logger.debug(f"Constructed command for communicate: {command}")

        env = self.mcp_servers.load_environment_variables(server.env)
        logger.debug(f"Loading environment variables for communicate: {list(env.keys())}")


        self._request_id_counter += 1
        request_id = self._request_id_counter
        rpc_request_obj = RPCRequest(
            jsonrpc="2.0",
            method=method,
            params=params,
            id=request_id
        )
        request_json_str = f"""{rpc_request_obj.model_dump_json()}
"""
        logger.debug(f"Sending request via communicate (stdin): {request_json_str.strip()}")

        try:
            process = subprocess.Popen(
                command,
                env=env,
                text=True,
                bufsize=1, # Line buffering (might not be relevant for communicate)
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE
            )
            stdout, stderr = process.communicate(input=request_json_str)
            logger.debug(f"Received stdout via communicate: {stdout.strip()}")
            logger.debug(f"Received stderr via communicate: {stderr.strip()}")
            return stdout, stderr
        except Exception as e:
            logger.error(f"Error during communicate with server '{server_name}': {e}", exc_info=True)
            raise MCPError(f"Subprocess communication failed for '{server_name}': {e}")


    def send_request(self, server_name: str, method: str, params: dict[str, Any] | list[Any]) -> Any:
        """Send a JSON-RPC request to the specified MCP server and wait for the response.

        Ensures connection is active, sends the request, reads the response line,
        parses it, checks for errors, and returns the result.

        Args:
            server_name: Name of the target server.
            method: The RPC method name.
            params: Parameters for the RPC method (dict or list).

        Returns:
            The 'result' field from the JSON-RPC response.

        Raises:
            MCPError: If the server isn't connected, communication fails,
                      response is invalid, or the server returns a JSON-RPC error.
        """
        if server_name not in self.transports or self.transports[server_name].process.poll() is not None:
             logger.warning(f"Server '{server_name}' not connected or process dead. Attempting to reconnect.")
             if not self.connect(server_name):
                  raise MCPError(f"Failed to connect/reconnect to MCP server '{server_name}'.")

        transport = self.transports[server_name]
        process = transport.process

        # Generate request ID
        self._request_id_counter += 1
        request_id = self._request_id_counter

        # Format JSON-RPC request
        request_payload = RPCRequest(
            method=method,
            params=params,
            id=request_id
        )

        try:
            # Serialize and send request to server's stdin
            request_str = request_payload.model_dump_json() + '\\n' # Must end with newline
            logger.debug(f"Sending to {server_name} stdin: {request_str.strip()}")
            transport.stdin.write(request_str)
            transport.stdin.flush() # Ensure data is sent

            # Read response from server's stdout
            # This assumes the server sends one complete JSON response per line
            logger.debug(f"Waiting for response from {server_name} stdout...")
            response_line = transport.stdout.readline()
            if not response_line:
                 # Check if process died unexpectedly
                 if process.poll() is not None:
                     stderr_output = ""
                     try: stderr_output = transport.stderr.read() # Read remaining stderr
                     except Exception: pass
                     raise MCPError(f"MCP server '{server_name}' terminated unexpectedly while waiting for response. Exit code: {process.returncode}. Stderr: {stderr_output.strip()}")
                 else:
                      # This case might happen if the server just doesn't respond
                      # or if readline timed out (though it usually blocks)
                     raise MCPError(f"No response received from MCP server '{server_name}'.")

            response_str = response_line.strip()
            logger.debug(f"Received from {server_name} stdout: {response_str}")

            # Parse JSON response
            try:
                 response_payload = json.loads(response_str)
            except json.JSONDecodeError as e:
                 raise MCPError(f"Failed to decode JSON response from '{server_name}': {e}. Response: '{response_str}'")


            # Validate response ID
            if response_payload.get("id") != request_id:
                # Allow null ID for notifications, though we shouldn't expect them here
                if response_payload.get("id") is not None:
                    raise MCPError(f"Received response with mismatched ID. Expected {request_id}, got {response_payload.get('id')}")

            # Check for JSON-RPC error
            if "error" in response_payload:
                error_data = response_payload["error"]
                code = error_data.get('code', 'N/A')
                message = error_data.get('message', 'No message')
                raise MCPError(f"MCP server '{server_name}' returned error: Code {code}, Message: {message}")

            # Return the result
            if "result" in response_payload:
                return response_payload["result"]
            elif "error" in response_payload:
                 # Error already raised above, but covering the case where 'result' is missing in an error response
                 # This shouldn't happen with valid JSON-RPC error objects
                 pass # Error handled
            else:
                # Neither result nor error is present, or it's potentially a notification
                if response_payload.get("id") is None and "method" in response_payload:
                     logger.warning(f"Received unexpected notification from '{server_name}': {response_payload}")
                     # Decide how to handle notifications if needed, maybe return None or loop to read again?
                     # For now, treat as invalid response in a request-response flow.
                     raise MCPError(f"Received unexpected notification instead of response from '{server_name}'.")
                else:
                    raise MCPError(f"Invalid JSON-RPC response from '{server_name}': Missing 'result' or 'error' field. Response: {response_payload}")


        except BrokenPipeError:
             stderr_output = ""
             try: stderr_output = transport.stderr.read()
             except Exception: pass
             raise MCPError(f"Broken pipe while communicating with '{server_name}'. Process likely terminated. Exit code: {process.poll()}. Stderr: {stderr_output.strip()}")
        except Exception as e:
            # Catch-all for other potential IOErrors or unexpected issues
            exit_code = process.poll()
            stderr_output = ""
            if exit_code is not None: # Check if it died
                 try: stderr_output = transport.stderr.read()
                 except Exception: pass
            logger.error(f"Unhandled exception during communication with '{server_name}': {e}", exc_info=True)
            raise MCPError(f"Failed communication with MCP server '{server_name}': {e}. Process exit code: {exit_code}. Stderr: {stderr_output.strip()}")


if __name__ == "__main__":
    import io # Import io here for the isinstance checks added

    client = StdioClient()
    server_to_test = "github" # Or another configured server
    # stdout, stderr = client.communicate(server_name=server_to_test, method="tools/list", params={}) # Try standard introspection
    stdout, stderr = client.communicate(server_name=server_to_test, method="tools/call", params={"name": "get_me"}) # Try standard introspection

    print("stdout:", stdout)
    print("stderr:", stderr)

