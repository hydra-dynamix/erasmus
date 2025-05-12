import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from erasmus.mcp.models import (
    McpError,
    McpServer,
    RPCRequest,
)
from erasmus.utils.rich_console import get_console_logger

logger = get_console_logger()

DEFAULT_CONFIG_PATH = Path.cwd() / ".erasmus" / "mcp" / "mcp_config.json"

class McpServers(BaseModel):
    servers: dict[str, McpServer] = Field(default_factory=dict)
    config_path: Path
    path_string_pattern: re.Pattern 
    __pydantic_fields_set__ = set()

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH):
        self.servers = {}
        self.config_path = config_path
        self.load_from_json()
        self.path_string_pattern = re.compile(r'(?:[a-zA-Z]:[\\/]|~[\\/]?|\.\.?[\\/]|[\/\\])[\w\s.+=~^-]*|(?:[\w\s.+=~^-]+[\\/])+[\w\s.+=~^-]*')


    def add_server(self, name: str, command: str, args: list[str], env: dict[str, str]):
        self.servers[name] = McpServer(name=name, command=command, args=args, env=env)

    def remove_server(self, name: str):
        if name in self.servers:
            del self.servers[name]

    def get_server(self, name: str) -> McpServer | None:
        return self.servers.get(name)

    def get_servers(self) -> dict[str, McpServer]:
        return self.servers

    def get_server_names(self) -> list[str]:
        return list(self.servers.keys())

    def get_server_paths(self) -> dict[str, Path]:
        paths = {}
        for server in self.servers.values():
            server_name = server.name
            command = server.command
            args = server.args

            if self.path_string_pattern.match(command):
                logger.info(f"Found path: {command}")
            if isinstance(args, list) and len(args) > 0:
                full_path = None
                if "--directory" in args:
                    full_path = self.parse_uv_directory_path(args)
                else:
                    try:
                        full_path = self.parse_command_path(command)
                    except Exception as error:
                        logger.warning(f"No command path found for {server_name}: {error}")
                if full_path:
                    paths[server_name] = full_path
        return paths

    def parse_command_path(self, command: str):
        return Path(command) if self.path_string_pattern.match(command) else None

    def parse_uv_directory_path(self, args: list[str]):
        directory = None
        file_path = None
        for i, arg in enumerate(args):
            if arg == "--directory":
                directory = args[i + 1]
            elif arg == "run":
                file_path = args[i + 1]
        return Path(directory) / file_path if directory and file_path else None

    def load_from_json(self):
        config_data = self.config_path.read_text()
        if "mcpServers" not in config_data:
            raise ValueError("Invalid MCP server configuration")
        for server_name, server_data in json.loads(config_data)["mcpServers"].items():
            command = server_data["command"]
            args = server_data["args"]
            raw_env = server_data.get("env", {})
            env = self.load_environment_variables(raw_env)
            self.add_server(server_name, command, args, env)

    def load_environment_variables(self, env: dict[str, str]):
        load_dotenv()
        return {key: os.getenv(key) for key in env}

    @staticmethod
    def get_server_request(
        method: str,
        request_id: int,
        params: dict[str, Any] | None=None,
    ) -> RPCRequest:
        return RPCRequest(
            jsonrpc='2.0',
            method=method,
            params=params,
            id=request_id,
        )


if __name__ == "__main__":
    mcp_servers = McpServers()
    logger.info(mcp_servers.get_servers())
    logger.info(mcp_servers.get_server_paths())
