import asyncio
from mcp import Client


async def main():
    async with Client("http://127.0.0.1:8001/mcp") as client:
        result = await client.list_tools()

        print("Result type:", type(result))
        print("Result:", result)
        print("Has tools attribute:", hasattr(result, "tools"))

        if hasattr(result, "tools"):
            for tool in result.tools:
                print("\nTool:", tool)
                print("Tool type:", type(tool))
                print("Tool attributes:", [
                    name for name in dir(tool)
                    if not name.startswith("_")
                ])


if __name__ == "__main__":
    asyncio.run(main())
