"""
Erasmus tool handler: dispatches tool calls to registered tool implementations.
"""
import asyncio
from typing import Any
from . import TOOL_REGISTRY

async def handle_tool_call(tool: str, input_data: dict[str, Any]) -> Any:
    handler = TOOL_REGISTRY.get(tool)
    if not handler:
        return {"error": f"Tool '{tool}' not found."}
    return await handler(input_data)

if __name__ == "__main__":
    asyncio.run(handle_tool_call("", {}))