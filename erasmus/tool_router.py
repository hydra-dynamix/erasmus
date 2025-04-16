"""
Tool routing and handler for Erasmus: detects tool calls in model output and dispatches to MCP client.
Supports OpenAI-style tool/function calling and multi-step chains.
"""
import re
import asyncio
from typing import Any, Dict, List
from .mcp_client import ErasmusMCPClient

TOOL_CALL_PATTERN = re.compile(r'"tool_call":\s*\{(.*?)\}', re.DOTALL)

class ToolRouter:
    def __init__(self, mcp_client: ErasmusMCPClient):
        self.mcp_client = mcp_client

    async def route(self, model_response: str) -> Any:
        """
        Detect and dispatch tool calls from model output.
        Supports single or chained tool calls.
        """
        tool_calls = self.extract_tool_calls(model_response)
        if not tool_calls:
            return None
        if len(tool_calls) == 1:
            return await self.mcp_client.tool_call(tool_calls[0]['tool'], tool_calls[0]['input'])
        else:
            return await self.mcp_client.chain(tool_calls)

    def extract_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        # This is a placeholder: real implementation should parse model output for tool/function calls
        # For now, expects tool calls in a JSON-like format
        # TODO: Replace with robust OpenAI function call extraction
        matches = TOOL_CALL_PATTERN.findall(text)
        tool_calls = []
        for match in matches:
            # Very naive: expects a dict-like string
            try:
                tool_call = eval('{' + match + '}')
                tool_calls.append(tool_call)
            except Exception:
                continue
        return tool_calls
