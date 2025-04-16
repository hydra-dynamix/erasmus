"""
Erasmus inference orchestrator: integrates API client, MCP client, and tool routing.
"""
import asyncio
from typing import List, Dict, Any
from .api_client import ErasmusAPIClient
from .mcp_client import ErasmusMCPClient
from .tool_router import ToolRouter

class ErasmusInference:
    def __init__(self, api_client=None, mcp_client=None):
        self.api_client = api_client or ErasmusAPIClient()
        self.mcp_client = mcp_client or ErasmusMCPClient()
        self.tool_router = ToolRouter(self.mcp_client)

    async def chat(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs) -> Any:
        """
        Main chat/inference entry point. Handles tool calls and chaining if present in model output.
        """
        # Step 1: Get model response
        response = self.api_client.chat(messages, stream=stream, **kwargs)
        if stream:
            # Streaming mode: yield chunks, tool call detection not supported
            return response
        # Step 2: Check for tool calls
        tool_result = await self.tool_router.route(response)
        if tool_result is not None:
            return tool_result
        return response
