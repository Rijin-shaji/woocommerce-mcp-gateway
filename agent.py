
import asyncio
import json
import os
import traceback

import httpx
from dotenv import load_dotenv
from groq import AsyncGroq
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


# Load environment variables from the project root .env file
load_dotenv()

GATEWAY_URL = "http://127.0.0.1:8004/mcp"
MODEL = "openai/gpt-oss-120b"


def get_environment_variables():
    """Load and validate required environment variables."""
    groq_api_key = os.environ.get("GROQ_API_KEY")
    mcp_api_key = os.environ.get("MCP_API_KEY")

    if not groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Check your .env file."
        )

    if not mcp_api_key:
        raise RuntimeError(
            "MCP_API_KEY is missing. Check your .env file."
        )

    return groq_api_key, mcp_api_key


async def main():
    groq_api_key, api_key = get_environment_variables()

    # Initialize Groq after loading and validating environment variables
    groq_client = AsyncGroq(api_key=groq_api_key)

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    print("Connecting to Unified MCP Gateway...")

    try:
        async with httpx.AsyncClient(
            headers=headers,
            timeout=30.0,
        ) as http_client:

            async with streamable_http_client(
                GATEWAY_URL,
                http_client=http_client,
            ) as (read_stream, write_stream):

                async with ClientSession(
                    read_stream,
                    write_stream,
                ) as session:

                    # Initialize the MCP connection
                    await session.initialize()

                    # Discover available MCP tools
                    mcp_tools = (await session.list_tools()).tools

                    tool_map = {}
                    groq_tools = []

                    for tool in mcp_tools:
                        function_name = tool.name.replace(".", "__")
                        tool_map[function_name] = tool.name

                        groq_tools.append({
                            "type": "function",
                            "function": {
                                "name": function_name,
                                "description": (
                                    tool.description or tool.name
                                ),
                                "parameters": tool.input_schema,
                            },
                        })

                    print("\nConnected to Unified MCP Gateway.")
                    print(f"Discovered {len(mcp_tools)} tools.")
                    print("Type 'exit' to quit.\n")

                    messages = [
                        {
                            "role": "system",
                            "content": (
                                "You are a helpful shopping and utility "
                                "assistant. Use WooCommerce tools for product "
                                "and order questions, currency tools for "
                                "currency conversion, and calculator tools "
                                "for arithmetic. Use actual tool results; "
                                "never invent prices, stock, exchange rates, "
                                "or order details. Ask for missing information "
                                "when necessary. If a tool fails, clearly "
                                "report the failure instead of inventing "
                                "an answer. When multiple tools are needed, "
                                "call the relevant tools and combine their "
                                "results into one clear answer."
                            ),
                        }
                    ]

                    while True:
                        try:
                            question = input("You: ").strip()
                        except (EOFError, KeyboardInterrupt):
                            print("\nGoodbye!")
                            break

                        if question.lower() in {"exit", "quit"}:
                            print("Goodbye!")
                            break

                        if not question:
                            continue

                        messages.append({
                            "role": "user",
                            "content": question,
                        })

                        # Allow multiple rounds of tool calls
                        for _ in range(6):
                            try:
                                response = (
                                    await groq_client.chat.completions.create(
                                        model=MODEL,
                                        messages=messages,
                                        tools=groq_tools,
                                        tool_choice="auto",
                                        temperature=0,
                                    )
                                )
                            except Exception as exc:
                                print(
                                    "\nGroq request failed: "
                                    f"{type(exc).__name__}: {exc}\n"
                                )
                                break

                            message = response.choices[0].message

                            # No further tool calls are required
                            if not message.tool_calls:
                                answer = (
                                    message.content
                                    or "No response received."
                                )

                                print(f"\nAssistant: {answer}\n")

                                messages.append({
                                    "role": "assistant",
                                    "content": answer,
                                })
                                break

                            # Preserve the assistant's tool-call request
                            messages.append(
                                message.model_dump(exclude_none=True)
                            )

                            for call in message.tool_calls:
                                function_name = call.function.name
                                original_name = tool_map.get(function_name)

                                if not original_name:
                                    result_text = (
                                        "Unknown tool requested: "
                                        f"{function_name}"
                                    )
                                else:
                                    try:
                                        arguments = json.loads(
                                            call.function.arguments or "{}"
                                        )

                                        print(
                                            "Calling MCP tool: "
                                            f"{original_name}"
                                        )

                                        result = await session.call_tool(
                                            original_name,
                                            arguments=arguments,
                                        )

                                        result_text = json.dumps(
                                            [
                                                block.model_dump(mode="json")
                                                for block in result.content
                                            ],
                                            ensure_ascii=False,
                                        )

                                        if result.is_error:
                                            result_text = (
                                                "Tool returned an error: "
                                                + result_text
                                            )

                                            print(
                                                "MCP tool reported an error: "
                                                f"{original_name}"
                                            )

                                    except Exception as exc:
                                        print(
                                            f"\nTool call failed: "
                                            f"{type(exc).__name__}: {exc}"
                                        )

                                        result_text = (
                                            "Tool call failed: "
                                            f"{type(exc).__name__}: {exc}"
                                        )

                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": call.id,
                                    "content": result_text,
                                })

                        else:
                            print(
                                "\nAssistant: I couldn't complete that "
                                "request within the tool-call limit.\n"
                            )

    except httpx.HTTPStatusError as exc:
        print(
            f"\nGateway HTTP error: {exc.response.status_code}. "
            "Check that your MCP_API_KEY is active and has permission "
            "to access the requested tools."
        )
    except Exception as exc:
        print(
            f"\nConnection or MCP error: {type(exc).__name__}: {exc}"
        )
        print(
            "Check that the gateway is running at "
            f"{GATEWAY_URL} and that your API key is valid."
        )


if __name__ == "__main__":
    asyncio.run(main())
