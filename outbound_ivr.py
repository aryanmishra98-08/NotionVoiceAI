"""
Notion Voice Control IVR Application.

This application handles outbound IVR calls using Twilio and FastAPI.
"""
from setup_loader_ivr import config_data, logger
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from twilio.request_validator import RequestValidator
from twilio.rest import Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo
from modules.routes import build_router
from modules.telephony import make_outbound_trigger


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
    title="Outbound-IVR",
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

# Twilio validator + client created here and injected into routes / scheduler
validator = RequestValidator(config_data["twilio"]["auth_token"])
twilio_client = Client(config_data["twilio"]["account_sid"], config_data["twilio"]["auth_token"])

# Routes
app.include_router(build_router(config_data, validator))

# APScheduler: set up a cron job to trigger an outbound call
scheduler = AsyncIOScheduler()
trigger_outbound_call = make_outbound_trigger(config_data, twilio_client)

# Configure jobs (ok to do this before start)
scheduler.add_job(
    trigger_outbound_call,
    trigger="cron",
    hour=17,
    minute=26,
    second=0,
    timezone=ZoneInfo("Asia/Kolkata"),
)

# Hook into FastAPI lifecycle
@app.on_event("startup")
async def _startup_scheduler():
    try:
        scheduler.start()
        logger.info("APScheduler started")
    except Exception as exc:
        logger.exception("Failed to start APScheduler: %s", exc)
        raise

@app.on_event("shutdown")
async def _shutdown_scheduler():
    try:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down")
    except Exception as exc:
        logger.exception("Error shutting down APScheduler: %s", exc)

# --- Entrypoint ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("outbound_ivr:app", host="0.0.0.0", port=8007)
