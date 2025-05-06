"""
Utilities for managing the MCP Server Registry.

The registry stores configuration details for different MCP servers,
allowing dynamic interaction via the CLI.
"""

import json
import os
from pathlib import Path
from typing import Any, Union # Keep Any if used, or remove if not needed
import typing # Added for get_origin, get_args
from pydantic import BaseModel, ConfigDict, create_model, Field # Restored Pydantic imports
import subprocess 

from erasmus.utils.rich_console import get_console_logger
from erasmus.mcp.servers import McpServers
from erasmus.mcp.client import StdioClient
from erasmus.mcp.models import RegistryTool
from erasmus.utils.paths import get_path_manager
from erasmus.utils.type_conversions import js_type_string_to_py_type, UnionType

NoneType = type(None)


logger = get_console_logger()

path_manager = get_path_manager()

class McpRegistry(BaseModel):
    servers: McpServers
    client: StdioClient
    registry: dict[str, Any]
    registry_path: Path
    binary_path: Path
    check_binary_script: Path
    model_config = ConfigDict(arbitrary_types_allowed=True)
    __pydantic_fields_set__ = set()

    def _json_print(self, data: dict[str, Any]):
        logger.info(json.dumps(data, indent=4))

    def __init__(self, registry_path: Path | None=None):
        logger.info("Initializing MCPRegistry...")
        self.servers = McpServers()
        self.client = StdioClient()
        self.registry_path = registry_path or path_manager.erasmus_dir / "mcp" / "registry.json"
        self.binary_path = path_manager.erasmus_dir / "mcp" / "servers" / "github" / "server"
        self.check_binary_script = path_manager.erasmus_dir / "mcp" / "servers" / "github" / "check_binary.sh"
        self._setup_github_server()
        self.registry = self._load_registry(registry_path)
        self._load_mcp_servers()
        logger.info("MCPRegistry initialized.")

    def _setup_github_server(self):
        os.chmod(self.binary_path, 0o755)
        os.chmod(self.check_binary_script, 0o755)
        subprocess.run([self.check_binary_script], check=True)

    def _load_mcp_servers(self):
        if not self.servers:
            self.servers = McpServers()
        server_paths = self.servers.get_server_paths()
        servers = self.servers.servers
        self.registry = {}
        self.registry["mcp_servers"] = {}
        for server_name, server in servers.items():
            self.registry["mcp_servers"][server_name] = {}
            self.registry["mcp_servers"][server_name]["server"] = server.model_dump()
            self.registry["mcp_servers"][server_name]["path"] = str(server_paths[server_name]) # Convert Path to str
            self.registry["mcp_servers"][server_name]["tools"] = {} # Initialize tools dict for the server
            self._load_available_tools(server_name)
        self._save_registry()


    def _load_available_tools(self, server_name: str):
        stdout, stderr = self.client.communicate(
            server_name,
            "tools/list",
            {}
        )
        results = json.loads(stdout)["result"]
        for key in results["tools"]:
            dynamic_model = self._create_tool_model(key['name'], key['inputSchema'])
            # Store the serializable tool definition (key) instead of the dynamic_model type
            self.registry["mcp_servers"][server_name]["tools"][key["name"]] = key 
            # logger.info(f"Processed tool '{key['name']}'. Dynamic model created: {dynamic_model}")
            # if dynamic_model.model_fields:
                # logger.info(f"Fields for {key['name']}: {dynamic_model.model_fields}")

    def _parse_tool(self, tool: dict[str, Any]):
        tool_name = tool["name"]
        tool_description = tool["description"]
        input_schema = tool["inputSchema"]
        tool_model = self._create_tool_model(tool_name, input_schema)
        return RegistryTool(
            name=tool_name,
            description=tool_description,
            tool_model=tool_model
        )

    def _create_tool_model(self, tool_name: str, input_schema: dict[str, Any]) -> type[BaseModel]:
        model_name = f"{tool_name.capitalize().replace('_', '')}InputModel"
        fields = {}
        required_fields = set(input_schema.get("required", []))

        for prop_name, prop_info in input_schema.get("properties", {}).items():
            js_type_str = prop_info.get("type", "any")
            py_type = js_type_string_to_py_type(js_type_str)
            description = prop_info.get("description", "")
            
            if prop_name in required_fields:
                # For required fields, Ellipsis (...) indicates it's required
                fields[prop_name] = (py_type, Field(..., description=description))
            else:
                # For optional fields, provide a default (error.g., None)
                # and wrap the type with | None if not already a union with NoneType
                if not (typing.get_origin(py_type) in (typing.Union, UnionType) and \
                        NoneType in typing.get_args(py_type)):
                    py_type = py_type | None
                fields[prop_name] = (py_type, Field(default=None, description=description))
        
        # Dynamically create the Pydantic model
        # You might want to add __config__ or other BaseModel attributes if needed
        created_model = create_model(model_name, **fields) # type: ignore
        return created_model

    def _value_to_type(self, value: Any, type: type):
        try:
            return type(value)
        except Exception as error:
            logger.error(f"Failed to convert value {value} to type {type}: {error}")
            return Any(value)

    def _save_registry(self):
        logger.info(f"Saving registry to {self.registry_path}")
        try:
            self.registry_path.write_text(json.dumps(self.registry, indent=2))
        except Exception as error:
            logger.error(f"Failed to save registry to {self.registry_path}: {error}")
            return False
        logger.info("Saved registry")
        return True

    def _load_registry(self, registry_path: Path | None = None):
        self.registry_path = registry_path if registry_path else self.registry_path
        try:
            self.registry = json.loads(self.registry_path.read_text())
        except Exception as error:
            logger.error(f"Failed to load registry from {self.registry_path}: {error}")
            return False
        if not self.registry:
            self.registry = {
                "mcpServers": {}
            }
        logger.info("Loaded registry")
        return True

    def get_registry(self):
        return self.registry

    

# Example usage (for testing)
if __name__ == '__main__':
    registry = McpRegistry()