"""Auth utilities for non-HTTP contexts (WebSocket etc)."""
from app.services.auth_service import decode_token


def verify_token_from_cookie(token: str) -> dict | None:
    """Verify JWT token and return payload, or None if invalid."""
    return decode_token(token)
