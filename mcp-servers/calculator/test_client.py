import asyncio
from mcp import Client


async def main():
    async with Client("http://127.0.0.1:8001/mcp") as client:
        response = await client.list_tools()

        print("=== Available MCP Tools ===")
        for tool in response.tools:
            print(f"- {tool.name}")

        tests = [
            ("add", {"a": 10, "b": 5}, 15),
            ("subtract", {"a": 10, "b": 5}, 5),
            ("multiply", {"a": 10, "b": 5}, 50),
            ("divide", {"a": 10, "b": 5}, 2),
            (
                "calculate_percentage",
                {"value": 200, "percentage": 10},
                20,
            ),
        ]

        print("\n=== Calculation Tests ===")
        for name, arguments, expected in tests:
            result = await client.call_tool(name, arguments)

            if result.is_error:
                print(f"FAIL: {name} returned an error: {result.content}")
                continue

            actual = result.structured_content["result"]
            status = "PASS" if actual == expected else "FAIL"
            print(f"{status}: {name} = {actual} (expected {expected})")

        print("\n=== Division by Zero Test ===")
        result = await client.call_tool("divide", {"a": 10, "b": 0})

        if result.is_error:
            print("PASS: Division by zero was rejected.")
        else:
            print("FAIL: Division by zero was not rejected.")
            print("Response:", result)


if __name__ == "__main__":
    asyncio.run(main())
