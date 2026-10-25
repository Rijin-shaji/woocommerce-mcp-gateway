import base64
import hashlib
import hmac
import json
import os
import socket
import sqlite3
import time
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app.ai_service import ask_ai
from backend.app.database import (
    verify_user_password,
    get_connection,
    create_user,
    create_api_key,
    initialize_database,
)

app = FastAPI(title="MCP Dashboard API")
initialize_database()

FRONTEND_ORIGIN = os.environ.get(
    "FRONTEND_ORIGIN",
    "http://localhost:5173",
)
COOKIE_NAME = "dashboard_session"
SESSION_SECONDS = 60 * 60 * 8
SECRET_KEY = os.environ.get("DASHBOARD_SECRET_KEY", "")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12, max_length=256)
    role: str = "member"


class CreateKeyRequest(BaseModel):
    name: str = Field(default="default", max_length=100)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)


def _sign(payload: str) -> str:
    if not SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="DASHBOARD_SECRET_KEY is not configured.",
        )

    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _make_session(user: dict) -> str:
    payload = {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "exp": int(time.time()) + SESSION_SECONDS,
    }

    encoded = base64.urlsafe_b64encode(
        json.dumps(payload).encode("utf-8")
    ).decode("ascii").rstrip("=")

    return f"{encoded}.{_sign(encoded)}"


def _current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)

    if not token or "." not in token:
        raise HTTPException(status_code=401, detail="Please sign in.")

    encoded, supplied_signature = token.rsplit(".", 1)

    expected_signature = _sign(encoded)

    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid session.")

    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(
            base64.urlsafe_b64decode(padded.encode("ascii"))
        )
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Invalid session.")

    if payload.get("exp", 0) < int(time.time()):
        raise HTTPException(status_code=401, detail="Session expired.")

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, username, role
            FROM users
            WHERE id = ? AND username = ? AND is_active = 1
            """,
            (payload.get("id"), payload.get("username")),
        ).fetchone()

    if row is None or row["role"] != payload.get("role"):
        raise HTTPException(status_code=401, detail="Invalid session.")

    return dict(row)


def _require_admin(user: dict) -> None:
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access is required.",
        )


def _server_config() -> list[dict]:
    return [
        {
            "name": "Calculator",
            "port": 8001,
            "url": os.getenv(
                "CALCULATOR_MCP_URL",
                "http://calculator-mcp:8001/mcp",
            ),
        },
        {
            "name": "Currency",
            "port": 8002,
            "url": os.getenv(
                "CURRENCY_MCP_URL",
                "http://currency-mcp:8002/mcp",
            ),
        },
        {
            "name": "WooCommerce",
            "port": 8003,
            "url": os.getenv(
                "WOOCOMMERCE_MCP_URL",
                "http://woocommerce-mcp:8003/mcp",
            ),
        },
    ]


def _server_status(url: str) -> str:
    try:
        parsed = urlparse(url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        with socket.create_connection(
            (parsed.hostname, port),
            timeout=2,
        ):
            return "online"
    except (OSError, ValueError, TypeError):
        return "offline"


@app.get("/")
def home():
    return {"message": "MCP Dashboard API is running."}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/api/login")
def login(body: LoginRequest, response: Response):
    user = verify_user_password(body.username, body.password)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )

    token = _make_session(user)

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path="/",
    )

    return {"user": user}


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
    )
    return {"message": "Signed out."}


@app.get("/api/me")
def get_me(request: Request):
    return {"user": _current_user(request)}


@app.get("/api/servers")
def list_servers(request: Request):
    _current_user(request)

    servers = []

    for server in _server_config():
        servers.append({
            "name": server["name"],
            "port": server["port"],
            "status": _server_status(server["url"]),
        })

    return {"servers": servers}


@app.get("/api/users")
def list_users(request: Request):
    user = _current_user(request)
    _require_admin(user)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, username, role, is_active, created_at
            FROM users
            ORDER BY id
            """
        ).fetchall()

    return [dict(row) for row in rows]


@app.post("/api/users")
def add_user(body: CreateUserRequest, request: Request):
    user = _current_user(request)
    _require_admin(user)

    if body.role not in {"admin", "member"}:
        raise HTTPException(
            status_code=400,
            detail="Role must be admin or member.",
        )

    try:
        user_id = create_user(
            body.username,
            body.password,
            body.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="That username already exists.",
        )

    return {"id": user_id, "message": "User created."}


@app.get("/api/users/{user_id}/keys")
def list_user_keys(user_id: int, request: Request):
    user = _current_user(request)
    _require_admin(user)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, user_id, name, is_revoked, created_at, revoked_at
            FROM api_keys
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()

    return [
        {
            **dict(row),
            "revoked": bool(row["is_revoked"]),
        }
        for row in rows
    ]


@app.post("/api/users/{user_id}/keys")
def add_user_key(
    user_id: int,
    body: CreateKeyRequest,
    request: Request,
):
    user = _current_user(request)
    _require_admin(user)

    try:
        api_key = create_api_key(user_id, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # The plaintext key is returned only once.
    return {
        "api_key": api_key,
        "message": "API key created. Copy it now; it cannot be retrieved later.",
    }


@app.post("/api/keys/{key_id}/revoke")
def revoke_key(key_id: int, request: Request):
    user = _current_user(request)
    _require_admin(user)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE api_keys
            SET is_revoked = 1,
                revoked_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_revoked = 0
            """,
            (key_id,),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Active API key not found.",
            )

    return {"message": "API key revoked."}


@app.get("/api/audit-logs")
def list_audit_logs(request: Request):
    user = _current_user(request)

    with get_connection() as connection:
        if user["role"] == "admin":
            rows = connection.execute(
                """
                SELECT id, user_id, username, upstream_server, tool_name,
                       timestamp, duration_ms, outcome, details
                FROM audit_logs
                ORDER BY id DESC
                LIMIT 500
                """
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, user_id, username, upstream_server, tool_name,
                       timestamp, duration_ms, outcome, details
                FROM audit_logs
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 500
                """,
                (user["id"],),
            ).fetchall()

    return [dict(row) for row in rows]


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request):
    _current_user(request)

    try:
        answer = await ask_ai(body.message.strip())
    except Exception:
        # Avoid returning secrets or internal exception details to the browser.
        raise HTTPException(
            status_code=502,
            detail="The AI assistant could not complete the request. Check the AI and gateway service logs.",
        )

    return {
        "response": answer,
        "answer": answer,
        "message": answer,
    }