from backend.app.database import (
    initialize_database,
    create_user,
    get_connection,
)

initialize_database()


def create_user_if_missing(username, password, role):
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if existing:
        print(f"{role.title()} account already exists: {username}")
        return

    create_user(username, password, role)
    print(f"{role.title()} account created: {username}")


# Demo credentials for local development only.
create_user_if_missing(
    "admin",
    "AdminDemo2026!Secure",
    "admin",
)

create_user_if_missing(
    "member",
    "MemberDemo2026!Secure",
    "member",
)
