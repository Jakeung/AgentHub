from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.services.auth_service import decode_token

PUBLIC_PATHS = {"/api/auth/login", "/api/auth/register", "/api/health", "/docs", "/openapi.json", "/redoc"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Public paths
        if path in PUBLIC_PATHS or not path.startswith("/api"):
            return await call_next(request)

        # Extract token from cookie
        token = request.cookies.get("auth-token")
        if not token:
            return JSONResponse(
                status_code=200,
                content={"code": -2, "message": "未登录", "data": None},
            )

        payload = decode_token(token)
        if not payload:
            return JSONResponse(
                status_code=200,
                content={"code": -2, "message": "登录已过期", "data": None},
            )

        # Inject user info into request state
        request.state.user_id = payload.get("id")
        request.state.username = payload.get("username")
        request.state.role = payload.get("role")
        request.state.permissions = payload.get("permissions", [])

        # Admin route protection
        if path.startswith("/api/admin") and request.state.role != "admin":
            return JSONResponse(
                status_code=200,
                content={"code": -3, "message": "无权限", "data": None},
            )

        return await call_next(request)
