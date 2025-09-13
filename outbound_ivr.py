"""
Notion Voice Control IVR Application.

This module sets up routes and middleware for handling incoming calls,
validating Twilio requests, obtaining JWT tokens from an internal Voice AI service,
and connecting calls via streaming.
"""
from setup_loader_ivr import config_data, logger
import os
import httpx
import asyncio
from zoneinfo import ZoneInfo
from urllib.parse import urlparse, urlunparse
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import Connect, Play, VoiceResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- Configuration ---
voice_ai_username = config_data['voice_ai_app']['username']
voice_ai_password = config_data['voice_ai_app']['password']
to_number = config_data['twilio']['to_number']
from_number = config_data['twilio']['from_number']
account_sid = config_data['twilio']['account_sid']
auth_token = config_data['twilio']['auth_token']
internal_error_voice_play_url = config_data['voices']['internal_error_voice_play_url']
voice_ai_timeout_connect = config_data['voice_ai_app'].get(
    'timeout_connect', 10.0)
voice_ai_timeout_read = config_data['voice_ai_app'].get('timeout_read', 30.0)

app_url = os.environ.get('CCAAS_APP_OUTBOUND_URL')
voice_ai_app_url = os.environ.get('VOICE_AI_APP_URL')

# CORS origins (default to no origins if not set)
origins = app_url if isinstance(app_url, list) else (
    [app_url] if app_url else [])

# Initialize FastAPI
app = FastAPI(
    title="Outbound-IVR",
    # docs_url=None,
    # redoc_url=None,
    # openapi_url=None,
    # redirect_slashes=False,
)

# Twilio request validator
validator = RequestValidator(auth_token)
twilio_client = Client(account_sid, auth_token)

# --- Pydantic Models ---
class ConnectPayload(BaseModel):
    CallSid: str

# --- Custom Middleware ---
class LoggingMiddleware(BaseHTTPMiddleware):
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
    # response.headers.pop("server", None)
    # response.headers.pop("Server", None)
    # response.headers.setdefault("Server", "Hidden")

    # # Security headers
    # response.headers.setdefault("X-Content-Type-Options", "nosniff")
    # response.headers.setdefault(
    #     "Content-Security-Policy",
    #     "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    #     "font-src 'self' https://fonts.gstatic.com; script-src 'self'; frame-ancestors 'self'; "
    #     "object-src 'none';",
    # )
    # response.headers.setdefault(
    #     "Strict-Transport-Security",
    #     "max-age=31536000; includeSubDomains;"
    # )
    # response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    # response.headers.setdefault(
    #     "Referrer-Policy", "no-referrer-when-downgrade")
    # response.headers.setdefault(
    #     "Permissions-Policy",
    #     "accelerometer=(), ambient-light-sensor=(), autoplay=(), battery=(), camera=(), "
    #     "display-capture=(), document-domain=(), encrypted-media=(), fullscreen=(), geolocation=(), "
    #     "gyroscope=(), magnetometer=(), microphone=*, midi=(), payment=(), picture-in-picture=(), "
    #     "publickey-credentials-get=(), screen-wake-lock=(), sync-xhr=(), usb=(), web-share=(), xr-spatial-tracking=()"
    # )
    # response.headers.setdefault("X-XSS-Protection", "1; mode=block")
    # response.headers.setdefault("Cache-Control", "must-revalidate")
    # response.headers.setdefault("Pragma", "no-cache")
    # response.headers.setdefault("Expires", "0")
    return response

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency Functions ---
async def validate_twilio_request(request: Request) -> None:
    try:
        # Reconstruct URL using forwarded proto if behind proxy
        full_url = str(request.url)
        parsed = urlparse(full_url)
        proto = request.headers.get('x-forwarded-proto', parsed.scheme)
        if proto.lower() != 'https':
            parsed = parsed._replace(scheme='https')
        secure_url = urlunparse(parsed)

        signature = request.headers.get('X-Twilio-Signature', '')
        form = await request.form()
        params = {k: str(v) for k, v in form.items()}

        logger.debug("Validating Twilio signature for URL %s", secure_url)
        if not validator.validate(secure_url, params, signature):
            logger.warning("Invalid Twilio signature: %s", signature)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio signature"
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected error in validate_twilio_request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal validation error"
        )


async def parse_request_data(request: Request) -> dict:
    try:
        content_type = request.headers.get('content-type', '')
        logger.debug("Content-Type: %s", content_type)
        if 'application/json' in content_type:
            data = await request.json()
        else:
            form = await request.form()
            data = {k: str(v) for k, v in form.items()}
        logger.debug("Parsed data: %s", data)
        return data
    except Exception as exc:
        logger.exception("Error parsing request data: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request payload"
        )


async def get_jwt_token(ccaas_call_id: str) -> str:
    try:
        auth_endpoint = f"{voice_ai_app_url}/api/auth/ccaas"
        payload = {
            "user_id": voice_ai_username,
            "user_password": voice_ai_password,
            "ccaas_call_id": ccaas_call_id,
            "caller_id": "notion-voice"
        }
        timeout = httpx.Timeout(voice_ai_timeout_connect,
                                read=voice_ai_timeout_read)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(auth_endpoint, json=payload)
            response.raise_for_status()
            data = response.json().get('data', {})
            token = data.get('jwt_token', '')
            logger.info("Received JWT token for Call ID %s", ccaas_call_id)
            return token
    except Exception as exc:
        logger.exception(
            "Error obtaining JWT token for %s: %s", ccaas_call_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to authenticate with voice AI service"
        )


async def stream_to_ultravox_verb(call_sid: str, token: str):
    try:
        init_endpoint = f"{voice_ai_app_url}/api/call/initiate-call"
        payload = {
            "ccaas_call_id": call_sid,
            "user_id": voice_ai_username,
            "call_type": "journaling"
        }
        timeout = httpx.Timeout(voice_ai_timeout_connect,
                                read=voice_ai_timeout_read)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                init_endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            join_url = response.json().get('data', '')
            logger.info("Received join URL for CallSid %s: %s", call_sid, join_url)

        if join_url:
            connect = Connect()
            connect.stream(url=join_url, name="ultravox")
            return connect
        else:
            logger.error("No join URL returned for CallSid: %s", call_sid)
            return Play(internal_error_voice_play_url)
    except Exception as exc:
        logger.exception(
            "Error streaming to Ultravox for %s: %s", call_sid, exc)
        return Play(internal_error_voice_play_url)


async def terminate_ultravox_call(call_sid: str, token: str) -> None:
    try:
        terminate_endpoint = f"{voice_ai_app_url}/api/call/terminate-call"
        payload = {
            "ccaas_call_id": call_sid,
            "user_id": voice_ai_username,
            "call_type": "journaling"
        }
        timeout = httpx.Timeout(voice_ai_timeout_connect,
                                read=voice_ai_timeout_read)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                terminate_endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            logger.info(
                "Successfully terminated Ultravox call for CallSid: %s", call_sid)
    except Exception as exc:
        logger.exception(
            "Error terminating Ultravox call for %s: %s", call_sid, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to terminate Ultravox call"
        )

# --- Routes ---
@app.post(
    "/connect",
    tags=["Connect API"],
    dependencies=[Depends(validate_twilio_request)]
)
async def connect_call(request: Request) -> Response:
    try:
        data = await parse_request_data(request)
        payload = ConnectPayload(**data)
        call_sid = payload.CallSid
        logger.info("Incoming call: %s", call_sid)

        twiml = VoiceResponse()
        twiml.pause(length=3)

        token = await get_jwt_token(call_sid)
        verb = await stream_to_ultravox_verb(call_sid, token)
        twiml.append(verb)
    except Exception as exc:
        logger.exception(
            "Error handling /connect for CallSid %s: %s", locals().get('call_sid', '<unknown>'), exc)
        twiml = VoiceResponse()
        twiml.play(internal_error_voice_play_url)

    return Response(content=str(twiml), media_type="application/xml")


@app.post(
    "/disconnect",
    tags=["Disconnect API"],
    dependencies=[Depends(validate_twilio_request)]
)
async def disconnect_call(request: Request) -> Response:
    try:
        data = await parse_request_data(request)
        payload = ConnectPayload(**data)
        call_sid = payload.CallSid

        # Capture Twilio call status if present
        call_status = data.get("CallStatus", "").lower()
        logger.info("Disconnecting call: %s, status: %s", call_sid, call_status)

        # Only terminate Ultravox call if Twilio status indicates call end
        if call_status == "completed":
            token = await get_jwt_token(call_sid)
            await terminate_ultravox_call(call_sid, token)
            logger.info("Ultravox call terminated for CallSid: %s", call_sid)
            return JSONResponse(
                status_code=status.HTTP_200_OK, content={"message": f"Call disconnected with status '{call_status}'"}
            )
        else:
            logger.info("No Ultravox termination needed for CallSid: %s with status: %s", call_sid, call_status)
            return JSONResponse(
                status_code=status.HTTP_200_OK, content={"message": f"Call status '{call_status}' received, no action taken"}
            )
    except Exception as exc:
        logger.exception(
            "Error handling /disconnect for CallSid %s: %s", locals().get('call_sid', '<unknown>'), exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": "Error disconnecting call"}
        )

# Outbound trigger
def trigger_outbound_call():
    call = twilio_client.calls.create(
        to=to_number,
        from_=from_number,
        url=f"{app_url}/connect",
        status_callback=f"{app_url}/disconnect",
        status_callback_method='POST',
        status_callback_event=['completed','failed','busy','no-answer','canceled']
    )
    logger.info("Triggered outbound call SID: %s", call.sid)

scheduler = AsyncIOScheduler()

def trigger_outbound_call():
    call = twilio_client.calls.create(
        to=to_number,
        from_=from_number,
        url=f"{app_url}/connect",
        status_callback=f"{app_url}/disconnect",
        status_callback_method='POST',
        status_callback_event=['completed','failed','busy','no-answer','canceled']
    )
    logger.info("Triggered outbound call SID: %s", call.sid)

# configure jobs (ok to do this before start)
scheduler.add_job(
    trigger_outbound_call,
    trigger='cron',
    hour=17,
    minute=26,
    second=0,
    timezone=ZoneInfo('Asia/Kolkata'),  # better than a plain string
)

# REMOVE this line entirely (it does nothing useful and can confuse things):
# asyncio.Event().wait()

# Hook into FastAPI lifecycle
@app.on_event("startup")
async def _startup_scheduler():
    try:
        scheduler.start()  # loop is running now
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
if __name__ == '__main__':
    try:
        import uvicorn
        uvicorn.run(
            'outbound_ivr:app',
            host='0.0.0.0',
            port=8007
        )
    except Exception as exc:
        logger.exception("Error starting server: %s", exc)
