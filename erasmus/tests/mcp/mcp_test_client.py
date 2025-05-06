# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "mcp[cli]",
# ]
# ///
from mcp.client.stdio import stdio_client
from mcp.server import Server

async def test():
    # Connect to the server
    server = Server(
        name="mcp_test_server",
    )
    async with stdio_client(server) as client:
        # Call the function
        result = await client.call(
            "my_function",
            {"param1": "test", "param2": 42}
        )
        print(f"Got result: {result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test())
