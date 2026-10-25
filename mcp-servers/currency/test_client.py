
import asyncio
from mcp import Client


async def main():
    async with Client("http://127.0.0.1:8002/mcp") as client:
        response = await client.list_tools()

        print("=== Available Currency Tools ===")
        for tool in response.tools:
            print("-", tool.name)

        print("\n=== INR to AED Conversion ===")
        result = await client.call_tool(
            "convert_currency",
            {
                "amount": 1000,
                "from_currency": "INR",
                "to_currency": "AED",
            },
        )

        if result.is_error:
            print("Conversion failed:", result.content)
            return

        print(result.structured_content)

        print("\n=== Same Currency Test ===")
        same = await client.call_tool(
            "convert_currency",
            {
                "amount": 1000,
                "from_currency": "INR",
                "to_currency": "INR",
            },
        )

        if same.is_error:
            print("Test failed:", same.content)
        else:
            data = same.structured_content
            if data["converted_amount"] == 1000:
                print("PASS: INR to INR returns the same amount.")
            else:
                print("FAIL:", data)


if __name__ == "__main__":
    asyncio.run(main())
