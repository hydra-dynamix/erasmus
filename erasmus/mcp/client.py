from erasmus.utils.rich_console import get_console_logger
from erasmus.mcp.models import McpError
from erasmus.mcp.servers import McpServers
from erasmus.mcp.models import (
    ServerTransport,
    RPCRequest,
    ListToolsRequest,
    CallToolRequest,
    InitializeRequest
)
from typing import Any, Optional
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
        self.request_json_str = ""
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
            McpError: If the server definition is not found.
        """
        server = self.mcp_servers.servers.get(server_name)
        if not server:
            raise McpError(f"Server '{server_name}' not found in configuration.")
        command = [server.command, *server.args]
        logger.debug(f"Constructed command for '{server_name}': {command}")
        return command

    def _load_env_vars(self, env: dict[str, str]):
        """Load environment variables required by the server into the current environment.

        Args:
            env: A dictionary of environment variables to set.
        """
        logger.debug(f"Loading environment variables: {env.keys()}")
        for key, value in env.items():
            try:
                if value.startswith("$"):
                    value = os.environ.get(key, "")
                if not value or value.startswith("$"):
                    self._create_dynamic_prompt_for_value(key)
                os.environ[key] = value
                if not os.environ[key]:
                    logger.debug(f"Environment variable '{key}' was empty, prompting user")
                    self._create_dynamic_prompt_for_value(key)
            except KeyError:
                logger.debug(f"Environment variable '{key}' not found, prompting user")
                self._create_dynamic_prompt_for_value(key)

    def _create_dynamic_prompt_for_value(self, key: str):
        """Prompt the user for a value for the given environment variable key.
        
        Args:
            key: The environment variable key to prompt for.
        """
        value = input(f"Enter value for {key}: ")
        os.environ[key] = value

    def _get_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        request_id: int = 1,
    ) -> RPCRequest:
        return self.mcp_servers.get_server_request(method, request_id, params)

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
            McpError: If there's an issue starting the server process or configuration is missing.
        """
        logger.info(f"Attempting to connect to MCP server '{server_name}'...")
        try:
            server = self.mcp_servers.servers.get(server_name)

            self._load_env_vars(server.env)
            command = self._get_server_command(server_name)
            self.request_json_str = self._get_request("initialize", {}, 1).model_dump_json() + "\n"
            process = subprocess.Popen(
                command,
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                env=os.environ.copy(),
                text=True,
            )
            logger.info(f"Successfully connected to MCP server '{server_name}'.")
            return process

        except FileNotFoundError:
             logger.error(f"Failed to start MCP server '{server_name}': Command not found ('{command[0]}'). Ensure it's in the system PATH.")
             return False
        except Exception as error:
            logger.error(f"Failed to start MCP server '{server_name}': {error}", exc_info=True)
            return False

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
                 except Exception as error:
                     logger.error(f"Error terminating server '{server_name}': {error}")
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
            McpError: If the server name is not found in the configuration.
            Exception: Can raise exceptions from subprocess.Popen or communicate.
        """
        if server_name not in self.mcp_servers.servers:
            raise McpError(f"Server '{server_name}' not found in configuration.")
        
        server = self.mcp_servers.servers.get(server_name)
        self._load_env_vars(server.env)
        command = self._get_server_command(server_name)

        # Prepare initialize and call requests as in testing.py
        init_request = InitializeRequest(id=1)
        call_request = CallToolRequest(method=method, params={"name": params.get("name"), "arguments": params.get("arguments", params)}, id=2)
        input_data = json.dumps(init_request.model_dump()) + "\n" + json.dumps(call_request.model_dump()) + "\n"

        try:
            process = subprocess.Popen(
                command,
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                env=os.environ.copy(),
                text=True,
            )
            logger.debug(f"Sending input to server: {input_data.strip()}")
            stdout, stderr = process.communicate(input=input_data)
            logger.debug(f"Received stdout: {stdout[:100]}")
            logger.debug(f"Received stderr: {stderr[:100]}")
            # print(f"stdout: {stdout}")
            # print(f"stderr: {stderr}")
            return stdout, stderr
        except Exception as error:
            logger.error(f"Error during communicate with server '{server_name}': {error}", exc_info=True)
            raise McpError(f"Subprocess communication failed for '{server_name}': {error}")


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
            McpError: If the server isn't connected, communication fails,
                      response is invalid, or the server returns a JSON-RPC error.
        """
        if server_name not in self.transports or self.transports[server_name].process.poll() is not None:
             logger.warning(f"Server '{server_name}' not connected or process dead. Attempting to reconnect.")
             if not self.connect(server_name):
                  raise McpError(f"Failed to connect/reconnect to MCP server '{server_name}'.")

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
                     raise McpError(f"MCP server '{server_name}' terminated unexpectedly while waiting for response. Exit code: {process.returncode}. Stderr: {stderr_output.strip()}")
                 else:
                      # This case might happen if the server just doesn't respond
                      # or if readline timed out (though it usually blocks)
                     raise McpError(f"No response received from MCP server '{server_name}'.")

            response_str = response_line.strip()
            logger.debug(f"Received from {server_name} stdout: {response_str}")

            # Parse JSON response
            try:
                response_payload = json.loads(response_str)
            except json.JSONDecodeError as error:
                raise McpError(f"Failed to decode JSON response from '{server_name}': {error}. Response: '{response_str}'")


            # Validate response ID
            if response_payload.get("id") != request_id:
                # Allow null ID for notifications, though we shouldn't expect them here
                if response_payload.get("id") is not None:
                    raise McpError(f"Received response with mismatched ID. Expected {request_id}, got {response_payload.get('id')}")

            # Check for JSON-RPC error
            if "error" in response_payload:
                error_data = response_payload["error"]
                code = error_data.get('code', 'N/A')
                message = error_data.get('message', 'No message')
                raise McpError(f"MCP server '{server_name}' returned error: Code {code}, Message: {message}")

            # Return the result
            if "result" in response_payload:
                result = response_payload["result"]
                # Ensure we're returning a valid result that can be properly processed
                # This helps prevent issues with isinstance() checks in the bundled erasmus.py
                if isinstance(result, dict) and "content" in result:
                    # Ensure content is always a list if present
                    if not isinstance(result["content"], list):
                        result["content"] = [result["content"]] if result["content"] is not None else []
                return result
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
                    raise McpError(f"Received unexpected notification instead of response from '{server_name}'.")                
                else:
                    raise McpError(f"Invalid JSON-RPC response from '{server_name}': Missing 'result' or 'error' field. Response: {response_payload}")



        except BrokenPipeError:
             stderr_output = ""
             try: stderr_output = transport.stderr.read()
             except Exception: pass
             raise McpError(f"Broken pipe while communicating with '{server_name}'. Process likely terminated. Exit code: {process.poll()}. Stderr: {stderr_output.strip()}")
        except Exception as error:
            # Catch-all for other potential IOErrors or unexpected issues
            exit_code = process.poll()
            stderr_output = ""
            if exit_code is not None: # Check if it died
                 try: stderr_output = transport.stderr.read()
                 except Exception: pass
            logger.error(f"Unhandled exception during communication with '{server_name}': {error}", exc_info=True)
            raise McpError(f"Failed communication with MCP server '{server_name}': {error}. Process exit code: {exit_code}. Stderr: {stderr_output.strip()}")


if __name__ == "__main__":
    client = StdioClient()
    server_to_test = "github" # Or another configured server
    stdout, stderr = client.communicate(server_name=server_to_test, method="tools/call", params={"name": "get_me"}) # Try standard introspection

    # print("stdout:", stdout)
    # print("stderr:", stderr)

