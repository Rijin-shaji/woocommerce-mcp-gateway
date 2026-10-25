import json
import os

import httpx
from groq import AsyncGroq
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8004/mcp")
MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """
You are a helpful shopping and utility assistant.
Use WooCommerce tools for product and order questions,
currency tools for currency conversion, and calculator tools
for arithmetic.

Use actual tool results. Never invent prices, stock,
exchange rates, or order details. Ask for missing information
when necessary. If a tool fails, clearly report the failure.
"""


async def ask_ai(question: str) -> str:
    groq_api_key = os.environ.get("GROQ_API_KEY")
    mcp_api_key = os.environ.get("MCP_API_KEY")

    if not groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    if not mcp_api_key:
        raise RuntimeError("MCP_API_KEY is not configured.")

    client = AsyncGroq(api_key=groq_api_key)

    headers = {"Authorization": f"Bearer {mcp_api_key}"}

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
                    read_stream, write_stream
                ) as session:
                    await session.initialize()
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

                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": question},
                    ]

                    for _ in range(6):
                        response = await client.chat.completions.create(
                            model=MODEL,
                            messages=messages,
                            tools=groq_tools,
                            tool_choice="auto",
                            temperature=0,
                        )

                        message = response.choices[0].message

                        if not message.tool_calls:
                            return message.content or "No response received."

                        messages.append(
                            message.model_dump(exclude_none=True)
                        )

                        for call in message.tool_calls:
                            original_name = tool_map.get(
                                call.function.name
                            )

                            if not original_name:
                                result_text = "Unknown tool requested."
                            else:
                                try:
                                    arguments = json.loads(
                                        call.function.arguments or "{}"
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

                                except Exception as exc:
                                    result_text = (
                                        f"Tool call failed: "
                                        f"{type(exc).__name__}: {exc}"
                                    )

                            messages.append({
                                "role": "tool",
                                "tool_call_id": call.id,
                                "content": result_text,
                            })

                    return (
                        "I couldn't complete that request within "
                        "the tool-call limit."
                    )
    finally:
        await client.close()
