from typing import Any
from http import HTTPStatus
from starlette.requests import Request


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def success(data: Any = None) -> dict:
    """Success response with code 0."""
    return {"code": 0, "data": data}


def error(code: int, message: str) -> dict:
    """Error response with custom code and message."""
    return {"code": code, "message": message, "data": None}


def page_data(items: list, total: int, page: int, page_size: int) -> dict:
    """Paginated data response."""
    return success({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


def validation_error(message: str) -> dict:
    """Validation error response (400)."""
    return error(400, message)


def unauthorized_error(message: str = "Unauthorized") -> dict:
    """Unauthorized error response (401)."""
    return error(401, message)


def forbidden_error(message: str = "Forbidden") -> dict:
    """Forbidden error response (403)."""
    return error(403, message)


def not_found_error(message: str = "Not found") -> dict:
    """Not found error response (404)."""
    return error(404, message)


def conflict_error(message: str = "Conflict") -> dict:
    """Conflict error response (409)."""
    return error(409, message)


def internal_error(message: str = "Internal server error") -> dict:
    """Internal server error response (500)."""
    return error(500, message)
