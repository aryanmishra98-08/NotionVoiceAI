"""
Notion Voice Control IVR Application.

This application handles inbound IVR calls using Twilio and FastAPI.
"""
from setup_loader_ivr import config_data, logger
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from twilio.request_validator import RequestValidator
from modules.routes import build_router


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        body = await request.body()
        logger.info("> %s %s", request.method, request.url)
        logger.debug("Headers: %s", dict(request.headers))
        logger.debug("Body: %s", body)

        async def receive():
            return {"type": "http.request", "body": body}
        request._receive = receive  # noqa

        resp: Response = await call_next(request)
        logger.info("< %s %s", resp.status_code, request.url)
        return resp


async def security_headers(request: Request, call_next):
    resp: Response = await call_next(request)
    resp.headers.pop("server", None)
    resp.headers.pop("Server", None)
    resp.headers.setdefault("Server", "Hidden")
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; script-src 'self'; frame-ancestors 'self'; object-src 'none';"
    )
    resp.headers.setdefault("Strict-Transport-Security",
                            "max-age=31536000; includeSubDomains;")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "no-referrer-when-downgrade")
    resp.headers.setdefault(
        "Permissions-Policy",
        "accelerometer=(), ambient-light-sensor=(), autoplay=(), battery=(), camera=*, "
        "display-capture=(), document-domain=(), encrypted-media=(), fullscreen=(), geolocation=(), "
        "gyroscope=(), magnetometer=(), microphone=*, midi=(), payment=(), picture-in-picture=(), "
        "publickey-credentials-get=(), screen-wake-lock=(), sync-xhr=(), usb=(), web-share=(), xr-spatial-tracking=()"
    )
    resp.headers.setdefault("X-XSS-Protection", "1; mode=block")
    resp.headers.setdefault("Cache-Control", "no-store")
    return resp

# --- App wiring ---
app = FastAPI(
    title="Inbound-IVR",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    redirect_slashes=False,
)
app.add_middleware(LoggingMiddleware)
app.middleware("http")(security_headers)

origins = config_data["app"]["url"] if isinstance(config_data["app"]["url"], list) else (
    [config_data["app"]["url"]] if config_data["app"]["url"] else []
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Twilio validator created here and injected into routes
validator = RequestValidator(config_data["twilio"]["auth_token"])
app.include_router(build_router(config_data, validator))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("inbound_ivr:app", host="0.0.0.0", port=8006)
