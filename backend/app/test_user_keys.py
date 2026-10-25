from backend.app.database import (
    get_connection,
    create_api_key,
    authenticate_api_key,
)

def get_user_id(username):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if row is None:
        raise ValueError(f"User not found: {username}")

    return row["id"]


# Generate a separate key for each account.
admin_id = get_user_id("admin")
member_id = get_user_id("member")

admin_key = create_api_key(admin_id, "admin-test-key")
member_key = create_api_key(member_id, "member-test-key")

# Verify each key belongs to the correct account.
admin_user = authenticate_api_key(admin_key)
member_user = authenticate_api_key(member_key)

assert admin_user["username"] == "admin"
assert admin_user["role"] == "admin"

assert member_user["username"] == "member"
assert member_user["role"] == "member"

print("Admin API key: SUCCESS")
print("Member API key: SUCCESS")
print("Keys belong to separate users: SUCCESS")
print("Admin role:", admin_user["role"])
print("Member role:", member_user["role"])
print("Admin API key:", admin_key)
print("Member API key:", member_key)
