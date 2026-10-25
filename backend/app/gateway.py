
import asyncio
import inspect
import logging
import os
import re
import time
from typing import Any

from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.middleware.auth_context import get_access_token

from backend.app.database import (
    authenticate_api_key,
    initialize_database,
    log_tool_call,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-gateway")

GATEWAY_HOST = os.getenv("GATEWAY_HOST", "0.0.0.0")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8004"))
GATEWAY_RESOURCE = os.getenv(
    "GATEWAY_RESOURCE",
    "http://localhost:8004",
)
UPSTREAM_TIMEOUT_SECONDS = 20

UPSTREAM_SERVERS = {
    "calculator": os.getenv(
        "CALCULATOR_MCP_URL",
        "http://127.0.0.1:8001/mcp",
    ),
    "currency": os.getenv(
        "CURRENCY_MCP_URL",
        "http://127.0.0.1:8002/mcp",
    ),
    "woocommerce": os.getenv(
        "WOOCOMMERCE_MCP_URL",
        "http://127.0.0.1:8003/mcp",
    ),
}

MEMBER_ALLOWED_TOOLS = {
    "woocommerce.list_products",
    "woocommerce.list_orders",
    "woocommerce.get_order",
    "currency.convert_currency",
    "calculator.add",
    "calculator.subtract",
    "calculator.multiply",
    "calculator.divide",
    "calculator.calculate_percentage",
}


class APIKeyTokenVerifier:
    """Validate bearer tokens against the hashed API-key database."""

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            user = await asyncio.to_thread(
                authenticate_api_key, token
            )
        except Exception:
            logger.exception("API-key verification failed")
            return None

        if user is None:
            return None

        return AccessToken(
            token=token,
            client_id=user["username"],
            subject=str(user["id"]),
            scopes=["mcp"],
            resource=GATEWAY_RESOURCE,
            claims={
                "user_id": user["id"],
                "username": user["username"],
                "role": user["role"],
            },
        )


def schema_annotation(schema: dict[str, Any]) -> type:
    """Map JSON Schema types to Python annotations."""
    schema_type = schema.get("type")

    if isinstance(schema_type, list):
        non_null_types = [
            item for item in schema_type if item != "null"
        ]
        schema_type = non_null_types[0] if non_null_types else None

    if schema_type == "string":
        return str
    if schema_type == "integer":
        return int
    if schema_type == "number":
        return float
    if schema_type == "boolean":
        return bool
    if schema_type == "array":
        return list
    if schema_type == "object":
        return dict

    return Any


class MCPGateway:
    def __init__(self):
        self.server = MCPServer(
            name="Unified MCP Gateway",
            token_verifier=APIKeyTokenVerifier(),
            auth=AuthSettings(
                issuer_url=GATEWAY_RESOURCE,
                resource_server_url=GATEWAY_RESOURCE,
                validate_token_resource=True,
            ),
        )

        self.servers: dict[str, dict[str, Any]] = {}
        self.tool_routes: dict[str, tuple[str, str]] = {}
        self.lock = asyncio.Lock()

    def register_server(
        self,
        name: str,
        url: str,
        enabled: bool = True,
    ) -> None:
        name = name.strip().lower()

        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise ValueError(f"Invalid upstream server name: {name}")

        if not url.startswith(("http://", "https://")):
            raise ValueError("Upstream URL must use HTTP or HTTPS.")

        self.servers[name] = {
            "url": url,
            "enabled": enabled,
        }

    async def discover_tools(self) -> None:
        """Discover upstream tools and register gateway wrappers."""
        for server_name, config in self.servers.items():
            if not config["enabled"]:
                continue

            url = config["url"]
            logger.info(
                "Discovering tools from %s at %s",
                server_name,
                url,
            )

            try:
                async with Client(
                    url,
                    read_timeout_seconds=UPSTREAM_TIMEOUT_SECONDS,
                ) as client:
                    result = await client.list_tools()

                for upstream_tool in result.tools:
                    upstream_name = upstream_tool.name
                    gateway_name = (
                        f"{server_name}.{upstream_name}"
                    )

                    if gateway_name in self.tool_routes:
                        raise ValueError(
                            f"Duplicate gateway tool: {gateway_name}"
                        )

                    self._register_tool(
                        server_name=server_name,
                        upstream_name=upstream_name,
                        gateway_name=gateway_name,
                        description=upstream_tool.description or "",
                        input_schema=upstream_tool.input_schema or {},
                    )

                    logger.info(
                        "Registered tool %s",
                        gateway_name,
                    )

            except Exception:
                logger.exception(
                    "Could not discover tools from %s",
                    server_name,
                )
                raise

    def _register_tool(
        self,
        server_name: str,
        upstream_name: str,
        gateway_name: str,
        description: str,
        input_schema: dict[str, Any],
    ) -> None:
        """Create a schema-aware wrapper for an upstream tool."""
        properties = input_schema.get("properties", {})
        required = set(input_schema.get("required", []))

        parameters = []

        for param_name, param_schema in properties.items():
            if not param_name.isidentifier():
                raise ValueError(
                    f"Unsupported parameter name: {param_name}"
                )

            default = (
                inspect.Parameter.empty
                if param_name in required
                else None
            )

            parameters.append(
                inspect.Parameter(
                    param_name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=schema_annotation(param_schema),
                )
            )

        signature = inspect.Signature(parameters)

        async def forward_tool(**kwargs: Any) -> Any:
            return await self._forward_call(
                server_name,
                upstream_name,
                gateway_name,
                kwargs,
            )

        forward_tool.__name__ = gateway_name.replace(".", "_")
        forward_tool.__doc__ = description or gateway_name
        forward_tool.__signature__ = signature

        self.server.add_tool(
            forward_tool,
            name=gateway_name,
            description=description or gateway_name,
        )

        self.tool_routes[gateway_name] = (
            server_name,
            upstream_name,
        )

    async def _forward_call(
        self,
        server_name: str,
        upstream_name: str,
        gateway_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Authorize, forward and audit one tool invocation."""
        token = get_access_token()

        if token is None:
            raise PermissionError(
                "Authentication is required to call this tool."
            )

        claims = token.claims or {}
        username = claims.get("username")
        user_id = claims.get("user_id")
        role = claims.get("role")

        if role not in {"admin", "member"}:
            raise PermissionError("Invalid user role.")

        if (
            role == "member"
            and gateway_name not in MEMBER_ALLOWED_TOOLS
        ):
            await self._audit(
                user_id,
                username,
                server_name,
                gateway_name,
                0,
                "denied",
                "Role is not permitted to call this tool.",
            )
            raise PermissionError(
                f"Your role cannot call {gateway_name}."
            )

        config = self.servers.get(server_name)

        if not config or not config["enabled"]:
            raise RuntimeError(
                f"Upstream server '{server_name}' is unavailable."
            )

        started = time.perf_counter()

        try:
            async with Client(
                config["url"],
                read_timeout_seconds=UPSTREAM_TIMEOUT_SECONDS,
            ) as client:
                result = await client.call_tool(
                    upstream_name,
                    arguments=arguments,
                )

            duration_ms = (
                time.perf_counter() - started
            ) * 1000

            if result.is_error:
                message = self._result_text(result)
                await self._audit(
                    user_id,
                    username,
                    server_name,
                    gateway_name,
                    duration_ms,
                    "error",
                    message[:1000],
                )
                raise RuntimeError(
                    f"Upstream tool failed: {message}"
                )

            await self._audit(
                user_id,
                username,
                server_name,
                gateway_name,
                duration_ms,
                "success",
                None,
            )

            if result.structuredContent is not None:
                return result.structuredContent

            return {
                "content": [
                    block.model_dump(mode="json")
                    for block in result.content
                ]
            }

        except Exception as exc:
            if isinstance(exc, RuntimeError) and str(exc).startswith(
                "Upstream tool failed:"
            ):
                raise

            duration_ms = (
                time.perf_counter() - started
            ) * 1000

            await self._audit(
                user_id,
                username,
                server_name,
                gateway_name,
                duration_ms,
                "error",
                f"{type(exc).__name__}: {exc}"[:1000],
            )
            raise

    @staticmethod
    def _result_text(result: Any) -> str:
        """Extract readable text from an MCP tool result."""
        parts = []

        for block in result.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)

        return "\n".join(parts) or "No error details were returned."

    @staticmethod
    async def _audit(
        user_id: int | None,
        username: str | None,
        server_name: str,
        tool_name: str,
        duration_ms: float,
        outcome: str,
        details: str | None,
    ) -> None:
        """Write an audit record without blocking the event loop."""
        try:
            await asyncio.to_thread(
                log_tool_call,
                user_id,
                username,
                server_name,
                tool_name,
                duration_ms,
                outcome,
                details,
            )
        except Exception:
            logger.exception("Failed to write audit log")


def main() -> None:
    initialize_database()

    gateway = MCPGateway()

    for name, url in UPSTREAM_SERVERS.items():
        gateway.register_server(name, url)

    asyncio.run(gateway.discover_tools())

    logger.info(
        "Starting MCP gateway on %s:%s",
        GATEWAY_HOST,
        GATEWAY_PORT,
    )

    gateway.server.run(
        transport="streamable-http",
        host=GATEWAY_HOST,
        port=GATEWAY_PORT,
    )


if __name__ == "__main__":
    main()
