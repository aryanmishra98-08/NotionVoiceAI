from urllib.parse import urlparse, urlunparse
import httpx
from fastapi import HTTPException, Request, status
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse, Connect, Play
from twilio.rest import Client

# ---------- TwiML builders ----------
def pause_then_connect(join_url: str, pause_sec: int = 3) -> VoiceResponse:
    vr = VoiceResponse()
    vr.pause(length=pause_sec)
    c = Connect()
    c.stream(url=join_url, name="ultravox")
    vr.append(c)
    return vr

def error_play(audio_url: str) -> VoiceResponse:
    vr = VoiceResponse()
    vr.play(audio_url)
    return vr

# ---------- Request utils ----------
def _normalize_https(url: str, xfp: str | None) -> str:
    parsed = urlparse(url)
    proto = (xfp or parsed.scheme or "https").lower()
    if proto != "https":
        parsed = parsed._replace(scheme="https")
    return urlunparse(parsed)

async def parse_request_data(request: Request) -> dict:
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            return await request.json()
        form = await request.form()
        return {k: str(v) for k, v in form.items()}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request payload"
        )

async def validate_twilio_request(request: Request, validator: RequestValidator) -> None:
    try:
        # Reconstruct URL using forwarded proto if behind proxy
        full_url = str(request.url)
        parsed = urlparse(full_url)
        proto = request.headers.get("x-forwarded-proto", parsed.scheme)
        if proto.lower() != "https":
            parsed = parsed._replace(scheme="https")
        secure_url = urlunparse(parsed)

        signature = request.headers.get("X-Twilio-Signature", "")
        form = await request.form()
        params = {k: str(v) for k, v in form.items()}

        if not validator.validate(secure_url, params, signature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio signature"
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal validation error"
        )

# ---------- Voice AI service I/O ----------
async def get_jwt_token(*, voice_ai_app_url: str, username: str, password: str,
                        call_id: str, t_connect: float, t_read: float) -> str:
    try:
        auth_endpoint = f"{voice_ai_app_url}/api/auth/ccaas"
        payload = {
            "user_id": username,
            "user_password": password,
            "ccaas_call_id": call_id,
            "caller_id": "notion-voice"
        }
        timeout = httpx.Timeout(t_connect, read=t_read)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(auth_endpoint, json=payload)
            response.raise_for_status()
            data = response.json().get("data", {})
            token = data.get("jwt_token", "")
            return token
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to authenticate with voice AI service"
        )

async def initiate_call(*, voice_ai_app_url: str, username: str, token: str,
                        call_id: str, t_connect: float, t_read: float) -> str | None:
    try:
        init_endpoint = f"{voice_ai_app_url}/api/call/initiate-call"
        payload = {
            "ccaas_call_id": call_id,
            "user_id": username,
            "call_type": "journaling"
        }
        timeout = httpx.Timeout(t_connect, read=t_read)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                init_endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json().get("data", "")  # join_url
    except Exception:
        return None

async def terminate_call(*, voice_ai_app_url: str, username: str, token: str,
                         call_id: str, t_connect: float, t_read: float) -> None:
    try:
        terminate_endpoint = f"{voice_ai_app_url}/api/call/terminate-call"
        payload = {
            "ccaas_call_id": call_id,
            "user_id": username,
            "call_type": "journaling"
        }
        timeout = httpx.Timeout(t_connect, read=t_read)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                terminate_endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to terminate Ultravox call"
        )

# ---------- Outbound trigger factory ----------
def make_outbound_trigger(config: dict, twilio_client: Client):
    """
    Returns a callable that kicks off an outbound call using Twilio REST API.
    """
    app_url = config["app"]["url"]
    base_url = app_url[0] if isinstance(app_url, list) else app_url

    to_number = config["twilio"]["to_number"]
    from_number = config["twilio"]["from_number"]

    def _trigger_outbound_call():
        call = twilio_client.calls.create(
            to=to_number,
            from_=from_number,
            url=f"{base_url}/connect",
            status_callback=f"{base_url}/disconnect",
            status_callback_method="POST",
            status_callback_event=["completed", "failed", "busy", "no-answer", "canceled"],
        )
        # Use your existing logger if you want to log here; kept minimal by design.
        return call.sid

    return _trigger_outbound_call
