import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from requests_oauthlib import OAuth1

load_dotenv()

BASE_URL = os.getenv("WOOCOMMERCE_URL", "").rstrip("/")
CONSUMER_KEY = os.getenv("WOOCOMMERCE_CONSUMER_KEY", "")
CONSUMER_SECRET = os.getenv("WOOCOMMERCE_CONSUMER_SECRET", "")

mcp = MCPServer(name="WooCommerce MCP Server")

ORDER_STATUSES = {
    "pending",
    "processing",
    "on-hold",
    "completed",
    "cancelled",
    "refunded",
    "failed",
}


def validate_configuration() -> None:
    """Ensure WooCommerce credentials are configured."""
    if not BASE_URL or not CONSUMER_KEY or not CONSUMER_SECRET:
        raise RuntimeError(
            "WooCommerce configuration is missing. "
            "Check WOOCOMMERCE_URL and API credentials in .env."
        )


def api_request(
    method: str,
    endpoint: str,
    params: dict | None = None,
    payload: dict | None = None,
) -> tuple[dict | list, dict[str, str]]:
    """Make an OAuth 1.0a authenticated request to WooCommerce."""
    validate_configuration()

    url = f"{BASE_URL}/{endpoint.lstrip('/')}"

    auth = OAuth1(
        CONSUMER_KEY,
        CONSUMER_SECRET,
        signature_method="HMAC-SHA1",
    )

    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            params=params,
            json=payload,
            auth=auth,
            headers={
                "Accept": "application/json",
                "User-Agent": "WooCommerce-MCP-Gateway/1.0",
            },
            timeout=20,
        )

        if not response.ok:
            try:
                error_data = response.json()
                message = error_data.get(
                    "message",
                    "WooCommerce API request failed.",
                )
            except ValueError:
                message = "WooCommerce API request failed."

            raise RuntimeError(
                f"WooCommerce API returned HTTP "
                f"{response.status_code}: {message}"
            )

        data = response.json() if response.content else {}

        response_headers = {
            "total": response.headers.get("X-WP-Total", ""),
            "total_pages": response.headers.get("X-WP-TotalPages", ""),
        }

        return data, response_headers

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not connect to WooCommerce at {BASE_URL}. "
            "Check that Docker and WordPress are running."
        ) from exc


def product_summary(product: dict) -> dict:
    """Return useful product fields without unnecessary API data."""
    return {
        "id": product.get("id"),
        "name": product.get("name"),
        "type": product.get("type"),
        "sku": product.get("sku"),
        "price": product.get("price"),
        "regular_price": product.get("regular_price"),
        "stock_status": product.get("stock_status"),
        "stock_quantity": product.get("stock_quantity"),
        "permalink": product.get("permalink"),
    }


def order_summary(order: dict) -> dict:
    """Return a compact summary of an order."""
    billing = order.get("billing") or {}

    return {
        "id": order.get("id"),
        "status": order.get("status"),
        "currency": order.get("currency"),
        "total": order.get("total"),
        "date_created": order.get("date_created"),
        "customer_name": (
            f"{billing.get('first_name', '')} "
            f"{billing.get('last_name', '')}"
        ).strip(),
        "line_items": [
            {
                "product_id": item.get("product_id"),
                "name": item.get("name"),
                "quantity": item.get("quantity"),
                "total": item.get("total"),
            }
            for item in order.get("line_items", [])
        ],
    }


@mcp.tool()
def list_products(
    search: str = "",
    page: int = 1,
    per_page: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    stock_status: str = "",
) -> dict:
    """List or search WooCommerce products.

    Search by product name or keyword. Optional filters include minimum
    price, maximum price and stock status (instock, outofstock,
    or onbackorder). Pagination is supported.
    """
    if page < 1:
        raise ValueError("Page must be at least 1.")

    if not 1 <= per_page <= 100:
        raise ValueError("per_page must be between 1 and 100.")

    if min_price is not None and min_price < 0:
        raise ValueError("min_price cannot be negative.")

    if max_price is not None and max_price < 0:
        raise ValueError("max_price cannot be negative.")

    if (
        min_price is not None
        and max_price is not None
        and min_price > max_price
    ):
        raise ValueError("min_price cannot exceed max_price.")

    params = {
        "page": page,
        "per_page": per_page,
    }

    if search.strip():
        params["search"] = search.strip()

    if min_price is not None:
        params["min_price"] = min_price

    if max_price is not None:
        params["max_price"] = max_price

    if stock_status:
        allowed_stock = {
            "instock",
            "outofstock",
            "onbackorder",
        }

        if stock_status not in allowed_stock:
            raise ValueError(
                f"stock_status must be one of {sorted(allowed_stock)}."
            )

        params["stock_status"] = stock_status

    data, headers = api_request(
        "GET",
        "products",
        params=params,
    )

    return {
        "products": [
            product_summary(item) for item in data
        ],
        "page": page,
        "per_page": per_page,
        "total": headers["total"],
        "total_pages": headers["total_pages"],
    }


@mcp.tool()
def create_product(
    name: str,
    regular_price: float,
    description: str = "",
    stock_quantity: int | None = None,
    sku: str = "",
) -> dict:
    """Create a simple product in WooCommerce.

    Provide a name and non-negative regular price. Description, stock
    quantity and SKU are optional. This tool changes the live store.
    """
    name = name.strip()

    if not name:
        raise ValueError("Product name cannot be empty.")

    if regular_price < 0:
        raise ValueError("regular_price cannot be negative.")

    if stock_quantity is not None and stock_quantity < 0:
        raise ValueError("stock_quantity cannot be negative.")

    payload = {
        "name": name,
        "type": "simple",
        "regular_price": f"{regular_price:.2f}",
        "description": description,
    }

    if sku.strip():
        payload["sku"] = sku.strip()

    if stock_quantity is not None:
        payload["manage_stock"] = True
        payload["stock_quantity"] = stock_quantity

    data, _ = api_request(
        "POST",
        "products",
        payload=payload,
    )

    return product_summary(data)


@mcp.tool()
def list_orders(
    status: str = "",
    today_only: bool = False,
    page: int = 1,
    per_page: int = 10,
) -> dict:
    """List WooCommerce orders, optionally filtered by status or today.

    today_only uses the Asia/Kolkata calendar date. Valid status values
    include pending, processing, on-hold, completed, cancelled, refunded
    and failed. Pagination is supported.
    """
    if page < 1:
        raise ValueError("Page must be at least 1.")

    if not 1 <= per_page <= 100:
        raise ValueError("per_page must be between 1 and 100.")

    params = {
        "page": page,
        "per_page": per_page,
    }

    if status:
        if status not in ORDER_STATUSES:
            raise ValueError(
                f"Invalid status. Choose from {sorted(ORDER_STATUSES)}."
            )

        params["status"] = status

    if today_only:
        tz = ZoneInfo("Asia/Kolkata")
        now = datetime.now(tz)

        start = datetime.combine(
            now.date(),
            time.min,
            tzinfo=tz,
        )
        end = start + timedelta(days=1)

        params["after"] = start.isoformat()
        params["before"] = end.isoformat()

    data, headers = api_request(
        "GET",
        "orders",
        params=params,
    )

    return {
        "orders": [
            order_summary(order) for order in data
        ],
        "page": page,
        "per_page": per_page,
        "total": headers["total"],
        "total_pages": headers["total_pages"],
        "today_filter_timezone": (
            "Asia/Kolkata" if today_only else None
        ),
    }


@mcp.tool()
def get_order(order_id: int) -> dict:
    """Retrieve one WooCommerce order by its numeric order ID."""
    if order_id < 1:
        raise ValueError("order_id must be a positive integer.")

    data, _ = api_request(
        "GET",
        f"orders/{order_id}",
    )

    return order_summary(data)


@mcp.tool()
def update_order_status(
    order_id: int,
    status: str,
) -> dict:
    """Change an order's status in WooCommerce.

    Allowed statuses are pending, processing, on-hold, completed,
    cancelled, refunded and failed. This tool changes the live store.
    """
    if order_id < 1:
        raise ValueError("order_id must be a positive integer.")

    if status not in ORDER_STATUSES:
        raise ValueError(
            f"Invalid status. Choose from {sorted(ORDER_STATUSES)}."
        )

    data, _ = api_request(
        "PUT",
        f"orders/{order_id}",
        payload={"status": status},
    )

    return order_summary(data)


if __name__ == "__main__":
    validate_configuration()

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8003,
    )
