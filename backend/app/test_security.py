from backend.app.database import (
    initialize_database,
    create_user,
    verify_user_password,
    create_api_key,
    authenticate_api_key,
    revoke_api_key,
)

initialize_database()

# Create a test member account.
username = "test_member"
password = "TestPassword123!"

try:
    user_id = create_user(username, password, role="member")
    print("1. User creation: SUCCESS")
except Exception as error:
    # Allow this test to run again if the account already exists.
    if "UNIQUE constraint failed" in str(error):
        from backend.app.database import get_connection

        with get_connection() as connection:
            row = connection.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            user_id = row["id"]
        print("1. User already exists: SUCCESS")
    else:
        raise

# Test username/password authentication.
user = verify_user_password(username, password)
assert user is not None, "Password authentication failed."
print("2. Password authentication: SUCCESS")

# Generate an API key.
api_key = create_api_key(user_id, name="test-key")
print("3. API key creation: SUCCESS")
print("   Generated key:", api_key)

# Test API key authentication.
authenticated_user = authenticate_api_key(api_key)
assert authenticated_user is not None, "API key authentication failed."
print("4. API key authentication: SUCCESS")

# Revoke the key and check that it no longer works.
revoked = revoke_api_key(api_key)
assert revoked, "API key revocation failed."
assert authenticate_api_key(api_key) is None, "Revoked key was accepted."
print("5. API key revocation: SUCCESS")
print("6. Revoked key rejection: SUCCESS")
