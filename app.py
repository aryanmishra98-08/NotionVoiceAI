"""
Notion Voice Control Main Application.

This module serves as the primary entry point for the Notion Voice Control application,
initializing the API server, setting up routes for Voice-to-Notion operations,
and managing authentication and request handling with rate limiting capabilities.
"""
from setup_loader import config_data, logger
import os
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
from modules.api_routes.APIResponse import APIResponse
from modules.api_routes import (
    AuthHandlingRoutes, CallHandlingRoutes
)
from modules.service_modules.JWTAuthentication import *


# Extract configuration values from environment variables
app_url = config_data['app']['url']

# CORS origins (default to no origins if not set)
origins = app_url if isinstance(app_url, list) else (
    [app_url] if app_url else [])

# Initialize FastAPI
app = FastAPI(
    title="NotionVoice",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    redirect_slashes=False,
)

# Setup rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- Exception Handlers ---
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded exceptions.
    Returns a standardized API response with a 429 status code.
    """
    response = APIResponse(
        output=None,
        message="Max attempts reached. Please try again after 60 seconds."
    )
    return JSONResponse(
        status_code=429,
        content=response.__dict__
    )

# --- Custom Middleware ---
class LoggingMiddleware(BaseHTTPMiddleware):  # type: ignore
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:

        body = await request.body()
        logger.info("> %s %s", request.method, request.url)
        logger.debug("Headers: %s", dict(request.headers))
        logger.debug("Body: %s", body)

        # Re-inject the body so downstream handlers can read it
        async def receive() -> dict:
            return {"type": "http.request", "body": body}
        request._receive = receive  # noqa: WPS437

        response = await call_next(request)
        logger.info("< %s %s", response.status_code, request.url)
        return response


app.add_middleware(LoggingMiddleware)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Remove any existing Server header, then set our own
    response.headers.pop("server", None)
    response.headers.pop("Server", None)
    response.headers.setdefault("Server", "Hidden")

    # Security headers
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; script-src 'self'; frame-ancestors 'self'; "
        "object-src 'none';",
    )
    response.headers.setdefault(
        "Strict-Transport-Security",
        "max-age=31536000; includeSubDomains;"
    )
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault(
        "Referrer-Policy", "no-referrer-when-downgrade")
    response.headers.setdefault(
        "Permissions-Policy",
        "accelerometer=(), ambient-light-sensor=(), autoplay=(), battery=(), camera=(), "
        "display-capture=(), document-domain=(), encrypted-media=(), fullscreen=(), geolocation=(), "
        "gyroscope=(), magnetometer=(), microphone=*, midi=(), payment=(), picture-in-picture=(), "
        "publickey-credentials-get=(), screen-wake-lock=(), sync-xhr=(), usb=(), web-share=(), xr-spatial-tracking=()"
    )
    response.headers.setdefault("X-XSS-Protection", "1; mode=block")
    response.headers.setdefault("Cache-Control", "must-revalidate")
    response.headers.setdefault("Pragma", "no-cache")
    response.headers.setdefault("Expires", "0")
    return response

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routes Registration ---
app.include_router(AuthHandlingRoutes.router, prefix="/api")
app.include_router(CallHandlingRoutes.router, prefix="/api")

# --- Entrypoint ---
if __name__ == '__main__':
    try:
        import uvicorn
        uvicorn.run(
            'app:app',
            host='0.0.0.0',
            port=8005
        )
    except Exception as exc:
        logger.exception("Error starting server: %s", exc)
