"""Password helpers and Streamlit sessions. Account lookup belongs to database.py."""

import hashlib
import hmac
import secrets

import streamlit as st


_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000
_SESSION_KEY = "user_id"
_ROLES = ("ADMIN", "MANAGER", "AGENT")


def hash_password(password: str) -> str:
    """Store algorithm, work factor, random salt, and digest together."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be nonempty text.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    """Return False for incorrect passwords or malformed stored credentials."""
    if not isinstance(password, str) or not password or not isinstance(encoded_hash, str):
        return False
    try:
        algorithm, iterations_text, salt_hex, digest_hex = encoded_hash.split("$")
        iterations = int(iterations_text)
        if algorithm != _ALGORITHM or not 1 <= iterations <= 1_000_000:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        if len(salt) != 16 or len(expected) != 32:
            return False
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def start_session(user_id: str) -> None:
    """Call only with the ID returned by successful server-side authentication.

    Clear previous account data before switching identities. Roles are never
    stored in session state; database.py reloads them from the user record.
    """
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("A valid authenticated user ID is required.")
    logout()
    st.session_state[_SESSION_KEY] = user_id


def current_user_id() -> str | None:
    """Read identity only from this browser's server-side Streamlit session."""
    user_id = st.session_state.get(_SESSION_KEY)
    return user_id if isinstance(user_id, str) and user_id.strip() else None


def logout() -> None:
    """Clear all app state, including selected projects, drafts, and passwords."""
    st.session_state.clear()


def require_role(user: dict, allowed_roles: tuple[str, ...]) -> None:
    """Check a database-resolved user; never pass a role supplied by the browser."""
    if not isinstance(user, dict):
        raise PermissionError("You do not have permission to perform this action.")
    user_id = user.get("id")
    role = user.get("role")
    if not isinstance(user_id, str) or not user_id.strip() or role not in _ROLES or role not in allowed_roles:
        raise PermissionError("You do not have permission to perform this action.")
