
import asyncio
import os
import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    api_key = os.environ.get("MCP_API_KEY")
    if not api_key:
        raise RuntimeError("MCP_API_KEY is not configured.")

    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(
        headers=headers,
        timeout=30.0,
    ) as http_client:
        async with streamable_http_client(
            "http://127.0.0.1:8004/mcp",
            http_client=http_client,
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as client:
                await client.initialize()

                result = await client.list_tools()
                print("Gateway tools:")
                for tool in result.tools:
                    print("-", tool.name)

                print("\nTesting calculator.add(10, 5):")
                result = await client.call_tool(
                    "calculator.add",
                    arguments={"a": 10, "b": 5},
                )
                print("Is error:", result.is_error)
                print("Result:", result.content)

                print("\nTesting currency conversion:")
                result = await client.call_tool(
                    "currency.convert_currency",
                    arguments={
                        "amount": 100,
                        "from_currency": "USD",
                        "to_currency": "INR",
                    },
                )
                print("Is error:", result.is_error)
                print("Result:", result.content)

                print("\nTesting WooCommerce product search:")
                result = await client.call_tool(
                    "woocommerce.list_products",
                    arguments={"search": "Demo Wireless Mouse"},
                )
                print("Is error:", result.is_error)
                print("Result:", result.content)


if __name__ == "__main__":
    asyncio.run(main())
