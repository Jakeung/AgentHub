import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from starlette.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.exceptions import BusinessError
from app.middleware.auth import AuthMiddleware
from app.api import auth
from app.api import instances
from app.api import admin_instances
from app.api import admin_users
from app.api import admin_audit
from app.api import chat
from app.api import secrets
from app.api import admin_settings
from app.api import channels

settings = get_settings()

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB + seed
    from app.seed import seed
    await seed()

    # Start background health check task
    from app.core.background_tasks import health_check_loop
    health_check_task = asyncio.create_task(health_check_loop())

    yield

    # Shutdown: cancel background tasks
    health_check_task.cancel()
    try:
        await health_check_task
    except asyncio.CancelledError:
        logger.info("Health check task cancelled")


app = FastAPI(title="AgentHub", version="1.0.0", lifespan=lifespan)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration with strict validation
cors_origins = [
    origin.strip() for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
] if settings.CORS_ORIGINS else []

# Validate no wildcard in production
if "*" in cors_origins and settings.CORS_ORIGINS:
    logger.warning("Wildcard CORS detected - this should not be used in production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["http://localhost"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type"],
    max_age=600,
)

# Auth middleware
app.add_middleware(AuthMiddleware)


# Global exception handlers
@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    return JSONResponse(
        status_code=200,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": -99, "message": "系统内部错误", "data": None},
    )


# Routers
app.include_router(auth.router)
app.include_router(instances.router)
app.include_router(admin_instances.router)
app.include_router(admin_users.router)
app.include_router(admin_audit.router)
app.include_router(chat.router)
app.include_router(secrets.router)
app.include_router(admin_settings.router)
app.include_router(admin_settings.user_router)
app.include_router(channels.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1024)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if not os.path.isdir(STATIC_DIR):
        return JSONResponse(status_code=404, content={"detail": "Frontend not built"})
    file_path = os.path.join(STATIC_DIR, full_path)
    if full_path and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

