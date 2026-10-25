
import asyncio
import json
import re
from urllib.request import Request, urlopen

from mcp.server.mcpserver import MCPServer

mcp = MCPServer(name="Currency Converter MCP Server")

API_URL = "https://open.er-api.com/v6/latest/USD"


def fetch_exchange_rates() -> dict:
    """Fetch the latest USD-based exchange rates."""
    request = Request(
        API_URL,
        headers={"User-Agent": "WooCommerce-MCP-Gateway/1.0"},
    )

    with urlopen(request, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))

    if data.get("result") != "success":
        raise RuntimeError("Currency API returned an unsuccessful response.")

    if not isinstance(data.get("rates"), dict):
        raise RuntimeError("Currency API response has no valid rates.")

    return data


@mcp.tool()
async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
) -> dict[str, str | float]:
    """Convert an amount between currencies using the latest available
    exchange rates. Currency codes must be three-letter ISO codes,
    such as INR, AED, USD, or EUR.
    """
    if amount < 0:
        raise ValueError("Amount cannot be negative.")

    from_currency = from_currency.strip().upper()
    to_currency = to_currency.strip().upper()

    if not re.fullmatch(r"[A-Z]{3}", from_currency):
        raise ValueError("Source currency must be a three-letter code.")

    if not re.fullmatch(r"[A-Z]{3}", to_currency):
        raise ValueError("Target currency must be a three-letter code.")

    if from_currency == to_currency:
        return {
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": 1.0,
            "converted_amount": round(amount, 2),
            "rate_updated_utc": "Not required for identical currencies",
        }

    data = await asyncio.to_thread(fetch_exchange_rates)
    rates = data["rates"]

    if from_currency not in rates:
        raise ValueError(f"Unsupported source currency: {from_currency}")

    if to_currency not in rates:
        raise ValueError(f"Unsupported target currency: {to_currency}")

    # Both rates are quoted against USD.
    exchange_rate = rates[to_currency] / rates[from_currency]
    converted_amount = amount * exchange_rate

    return {
        "amount": amount,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "exchange_rate": exchange_rate,
        "converted_amount": round(converted_amount, 2),
        "rate_updated_utc": data.get("time_last_update_utc", "Unknown"),
    }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8002,
    )
