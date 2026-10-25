import hashlib
import secrets
import sqlite3
from pathlib import Path
from typing import Optional
import os

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

# Store the database in the project root.
# Allow SQLite to use a persistent Kubernetes-mounted directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = Path(
    os.environ.get("DATABASE_PATH", str(PROJECT_ROOT / "security.db"))
)

password_hasher = PasswordHasher()


def get_connection() -> sqlite3.Connection:
    """Create a database connection with dictionary-like rows."""
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    """Create security tables if they do not already exist."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
                    CHECK (role IN ('admin', 'member')),
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key_hash TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                is_revoked INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                revoked_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                upstream_server TEXT,
                tool_name TEXT,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                duration_ms REAL,
                outcome TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_api_keys_user_id
                ON api_keys(user_id);

            CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp
                ON audit_logs(timestamp);

            CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id
                ON audit_logs(user_id);
            """
        )


def hash_api_key(api_key: str) -> str:
    """Return a SHA-256 hash of an API key."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def create_user(
    username: str,
    password: str,
    role: str = "member",
) -> int:
    """Create a user and return its database ID."""
    username = username.strip()

    if not username:
        raise ValueError("Username cannot be empty.")

    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")

    if role not in {"admin", "member"}:
        raise ValueError("Role must be 'admin' or 'member'.")

    password_hash = password_hasher.hash(password)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
            """,
            (username, password_hash, role),
        )
        return cursor.lastrowid


def verify_user_password(username: str, password: str) -> Optional[dict]:
    """Verify a password and return safe user information."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, username, password_hash, role, is_active
            FROM users
            WHERE username = ?
            """,
            (username.strip(),),
        ).fetchone()

    if row is None or not row["is_active"]:
        return None

    try:
        password_hasher.verify(row["password_hash"], password)
    except (VerifyMismatchError, VerificationError):
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
    }


def create_api_key(user_id: int, name: str = "default") -> str:
    """Create a key. Return the secret once; store only its hash."""
    api_key = "mcp_" + secrets.token_urlsafe(32)
    key_hash = hash_api_key(api_key)

    with get_connection() as connection:
        user = connection.execute(
            "SELECT id, is_active FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if user is None or not user["is_active"]:
            raise ValueError("User does not exist or is inactive.")

        connection.execute(
            """
            INSERT INTO api_keys (user_id, key_hash, name)
            VALUES (?, ?, ?)
            """,
            (user_id, key_hash, name.strip() or "default"),
        )

    # This is the only time the plaintext key is returned.
    return api_key


def authenticate_api_key(api_key: str) -> Optional[dict]:
    """Validate an API key and return its active user's information."""
    if not api_key:
        return None

    key_hash = hash_api_key(api_key)

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT u.id, u.username, u.role
            FROM api_keys AS k
            JOIN users AS u ON u.id = k.user_id
            WHERE k.key_hash = ?
              AND k.is_revoked = 0
              AND u.is_active = 1
            """,
            (key_hash,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
    }


def revoke_api_key(api_key: str) -> bool:
    """Revoke a key so subsequent authentication attempts fail."""
    key_hash = hash_api_key(api_key)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE api_keys
            SET is_revoked = 1,
                revoked_at = CURRENT_TIMESTAMP
            WHERE key_hash = ? AND is_revoked = 0
            """,
            (key_hash,),
        )
        return cursor.rowcount > 0


def log_tool_call(
    user_id: Optional[int],
    username: Optional[str],
    upstream_server: str,
    tool_name: str,
    duration_ms: float,
    outcome: str,
    details: Optional[str] = None,
) -> None:
    """Write an audit record for an attempted tool call."""
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO audit_logs (
                user_id, username, upstream_server, tool_name,
                duration_ms, outcome, details
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                upstream_server,
                tool_name,
                duration_ms,
                outcome,
                details,
            ),
        )


if __name__ == "__main__":
    initialize_database()
    print(f"Security database initialized at: {DATABASE_PATH}")
