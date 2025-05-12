import asyncio
import json
import sys
import os
from typing import Dict, Any, Optional

# Basic logging to stderr to avoid interfering with stdout JSON-RPC
def log_error(message: str):
    print(f"SERVER_ERROR: {message}", file=sys.stderr, flush=True)

def log_info(message: str):
    print(f"SERVER_INFO: {message}", file=sys.stderr, flush=True)

# --- Tool Implementation ---
def my_function(param1: str, param2: int) -> str:
    """
    Function docstring - this will be used in the schema
    """
    # Basic type check (real server might have more robust validation)
    if not isinstance(param1, str) or not isinstance(param2, int):
        raise ValueError("Invalid parameter types for my_function")
    return f"Processed '{param1}' with {param2}"

# --- Available Tools Schema ---
# This should match the structure expected by the client's StdioClient
# or MCP implementation during initialization/tools/list.
AVAILABLE_TOOLS = {
    "my_function": {
        "name": "my_function",
        "description": "Function docstring - this will be used in the schema",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string"},
                "param2": {"type": "integer"}
            },
            "required": ["param1", "param2"]
        }
        # MCP spec might define a return schema too, omitted for simplicity
    }
    # Add other tools here if needed
}


# --- JSON-RPC Response Formatting ---
def create_response(request_id: Optional[str | int], result: Any) -> str:
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }
    return json.dumps(response) + '\n' # MUST end with newline

def create_error_response(request_id: Optional[str | int], code: int, message: str, data: Optional[Any] = None) -> str:
    error_obj = {"code": code, "message": message}
    if data is not None:
        error_obj["data"] = data
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": error_obj
    }
    return json.dumps(response) + '\n' # MUST end with newline


# --- Main Server Logic ---
async def handle_request(request_data: Dict[str, Any], writer: asyncio.StreamWriter, initialized: bool) -> bool:
    """Handles a single parsed JSON-RPC request."""
    request_id = request_data.get("id")
    method = request_data.get("method")
    params = request_data.get("params", {})

    log_info(f"Received request (id={request_id}): method='{method}'")

    if not isinstance(request_id, (str, int, type(None))):
        log_error("Invalid request ID type")
        # According to JSON-RPC 2.0 spec, notification errors are not sent back.
        # If it has an ID, it's not a notification.
        if request_id is not None:
             response_json = create_error_response(None, -32600, "Invalid Request", "Invalid request ID type")
             writer.write(response_json.encode('utf-8'))
             await writer.drain()
        return initialized # Still running, but handle error

    if not method:
        log_error("Missing method in request")
        response_json = create_error_response(request_id, -32600, "Invalid Request", "Method not specified")
        writer.write(response_json.encode('utf-8'))
        await writer.drain()
        return initialized

    # --- Handle MCP Handshake ---
    if method == "initialize":
        if initialized:
             log_error("Received duplicate initialize request.")
             response_json = create_error_response(request_id, -32002, "Server Error", "Already initialized")
        else:
             log_info("Handling initialize request.")
             # Respond with server capabilities (including tools)
             response_data = {
                 "capabilities": {
                     # Add other capabilities the client might need
                     "tools": list(AVAILABLE_TOOLS.values()) # Send tool schemas
                 }
             }
             response_json = create_response(request_id, response_data)
             initialized = True # Mark as initialized AFTER sending response
        writer.write(response_json.encode('utf-8'))
        await writer.drain()
        log_info(f"Initialization {'completed' if initialized else 'failed'}.")
        return initialized

    # --- Must be initialized for other methods ---
    if not initialized:
        log_error(f"Received method '{method}' before successful initialization.")
        response_json = create_error_response(request_id, -32002, "Server Error", "Server not initialized")
        writer.write(response_json.encode('utf-8'))
        await writer.drain()
        return initialized # Remain uninitialized

    # --- Handle Standard MCP Methods ---
    if method == "tools/list":
        log_info("Handling tools/list request.")
        response_json = create_response(request_id, {"tools": list(AVAILABLE_TOOLS.values())})
        writer.write(response_json.encode('utf-8'))
        await writer.drain()

    # --- Handle Custom Tool Calls ---
    elif method == "tools/call":
        tool_name = params.get("tool_name")
        tool_params = params.get("params", {})
        log_info(f"Handling tools/call request for tool: {tool_name}")

        if tool_name == "my_function":
            try:
                # Ensure params is a dict if calling by name
                if not isinstance(tool_params, dict):
                     raise TypeError("Parameters must be a dictionary for named argument calling.")
                result = my_function(param1=tool_params.get("param1"), param2=tool_params.get("param2"))
                response_json = create_response(request_id, {"result": result})
            except (TypeError, ValueError, KeyError) as error:
                log_error(f"Error calling my_function: {error}")
                response_json = create_error_response(request_id, -32602, "Invalid Params", str(e))
            except Exception as error:
                 log_error(f"Unexpected error in my_function: {error}")
                 response_json = create_error_response(request_id, -32000, "Server Error", f"Internal error: {error}")
        else:
            log_error(f"Method not found: {tool_name}")
            response_json = create_error_response(request_id, -32601, "Method not found", f"Tool '{tool_name}' not found")

        writer.write(response_json.encode('utf-8'))
        await writer.drain()

    elif method == "shutdown":
         log_info("Handling shutdown request.")
         response_json = create_response(request_id, {}) # Acknowledge shutdown
         writer.write(response_json.encode('utf-8'))
         await writer.drain()
         writer.close()
         await writer.wait_closed()
         log_info("Server shutting down.")
         # Signal the main loop to exit
         return False # No longer initialized / running

    else:
        log_error(f"Unknown method: {method}")
        response_json = create_error_response(request_id, -32601, "Method not found", f"Method '{method}' not recognized")
        writer.write(response_json.encode('utf-8'))
        await writer.drain()

    return initialized # Remain initialized unless shutdown


async def main():
    log_info("MCP Test Server starting...")
    # Use asyncio's streams for non-blocking stdio
    reader = await asyncio.StreamReader.from_stdin()
    writer = await asyncio.StreamWriter.from_stdout()

    initialized = False
    is_running = True

    while is_running:
        log_info("Waiting for request...")
        try:
            # Read one line (a full JSON object)
            line = await reader.readline()
            if not line:
                log_info("EOF received, exiting.")
                break # End of input

            line_str = line.decode('utf-8').strip()
            log_info(f"Raw input line: {line_str}")
            if not line_str:
                continue # Ignore empty lines

            # Parse JSON
            try:
                request_data = json.loads(line_str)
                if not isinstance(request_data, dict):
                     raise json.JSONDecodeError("Input is not a JSON object", line_str, 0)
            except json.JSONDecodeError as error:
                log_error(f"Invalid JSON received: {error}")
                response_json = create_error_response(None, -32700, "Parse error", str(e))
                writer.write(response_json.encode('utf-8'))
                await writer.drain()
                continue # Try reading next line

            # Handle the request
            initialized = await handle_request(request_data, writer, initialized)
            if not initialized and method == "shutdown": # Check if shutdown was requested
                 is_running = False


        except asyncio.CancelledError:
             log_info("Server task cancelled.")
             is_running = False
        except ConnectionResetError:
             log_info("Client closed connection.")
             is_running = False
        except Exception as error:
            log_error(f"Unexpected error in main loop: {error}")
            # Attempt to send a generic error if possible, but might fail if connection is broken
            try:
                response_json = create_error_response(None, -32000, "Internal Server Error", str(e))
                writer.write(response_json.encode('utf-8'))
                await writer.drain()
            except Exception as write_e:
                 log_error(f"Failed to send error response: {write_e}")
            is_running = False # Stop on unhandled errors

    log_info("Server main loop finished.")
    if not writer.is_closing():
        writer.close()
        await writer.wait_closed()
    log_info("Server shutdown complete.")


if __name__ == "__main__":
    # Make stdin/stdout binary for asyncio streams
    # Note: This might cause issues if something else expects text mode,
    # but it's often necessary for reliable stream handling.
    # sys.stdin = sys.stdin.detach() # Detach might not be needed if using from_stdin/from_stdout
    # sys.stdout = sys.stdout.detach()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_info("Server interrupted by user (Ctrl+C).")
