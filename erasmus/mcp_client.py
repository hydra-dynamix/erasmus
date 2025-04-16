"""
MCP stdio client integration for Erasmus.
Wraps python-sdk's stdio_client for tool calls and multi-step chains.
"""
import asyncio
import os
from pathlib import Path
from typing import Any

from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import JSONRPCMessage

from erasmus.tools import TOOL_REGISTRY
from erasmus.tools.handler import handle_tool_call
from erasmus.utils.paths import SetupPaths

SETUP_PATHS = SetupPaths.with_project_root(Path.cwd())


class ErasmusMCPClient:
    def __init__(
        self,
        server_command: str | None,
        server_args: list[str] | None,
        env: dict[str, str] | None,
        cwd:str | None,
    ):
        self.server_command = server_command or os.getenv("MCP_SERVER_COMMAND", "mcp-server")
        self.server_args = server_args or []
        self.env = env or os.environ.copy()
        self.cwd = cwd or SETUP_PATHS.project_root
        self.server = StdioServerParameters(
            command=self.server_command,
            args=self.server_args,
            env=self.env,
            cwd=self.cwd,
            encoding="utf-8",
            encoding_error_handler="strict",
        )
        self.client = None

    async def ensure_client(self):
        if self.client is None:
            self.client = stdio_client(
                server=self.server,
        )
        return self.client

    async def tool_call(self, tool: str, input_data: dict[str, Any]) -> Any:
        if tool in TOOL_REGISTRY:
            # Handle locally registered tool
            return await handle_tool_call(tool, input_data)
        # Otherwise, send to MCP server
        client = await self.ensure_client()
        await client.send({"tool": tool, "input": input_data})
        return await client.receive()

    async def chain(self, tool_calls: list) -> Any:
        # If all tools are local, chain locally; else, send to MCP server
        if all(call['tool'] in TOOL_REGISTRY for call in tool_calls):
            results = []
            for call in tool_calls:
                results.append(await handle_tool_call(call['tool'], call['input']))
            return results
        client = await self.ensure_client()
        result = await client.send({"chain": tool_calls})
        await client.receive()
        return JSONRPCMessage(
            self.cwd,
            **result.model_dump(),
        )


if __name__ == "__main__":
    mcp_client = ErasmusMCPClient(
        server_command="list",
        server_args=[],
        env=os.environ.copy(),
        cwd=SETUP_PATHS.project_root,
    )
    asyncio.run(mcp_client.ensure_client())