import asyncio
from mcp import Client


def print_result(result):
    print("Is error:", result.is_error)
    print("Structured content:", result.structured_content)
    print("Content blocks:")

    for block in result.content:
        if hasattr(block, "text"):
            print(block.text)
        else:
            print(block)


async def main():
    async with Client("http://127.0.0.1:8003/mcp") as client:
        print("=== Search for the demo mouse ===")
        result = await client.call_tool(
            "list_products",
            {"search": "Demo Wireless Mouse"},
        )
        print_result(result)

        print("\n=== Today's orders ===")
        result = await client.call_tool(
            "list_orders",
            {"today_only": True, "per_page": 10},
        )
        print_result(result)


if __name__ == "__main__":
    asyncio.run(main())
