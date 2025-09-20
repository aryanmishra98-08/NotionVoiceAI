from urllib.parse import urlparse, urlunparse
import httpx
from fastapi import HTTPException, Request, status
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse, Connect, Play


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
        ct = request.headers.get("content-type", "")
        if "application/json" in ct:
            return await request.json()
        form = await request.form()
        return {k: str(v) for k, v in form.items()}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request payload")


async def validate_twilio_request(request: Request, validator: RequestValidator) -> None:
    try:
        secure_url = _normalize_https(
            str(request.url), request.headers.get("x-forwarded-proto"))
        signature = request.headers.get("X-Twilio-Signature", "")
        ct = request.headers.get("content-type", "")

        if "application/json" in ct:
            # If you enable JSON webhooks, also verify X-Twilio-BodySHA256 separately.
            params = {}
        else:
            form = await request.form()
            params = {k: str(v) for k, v in form.items()}

        if not validator.validate(secure_url, params, signature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal validation error")


# ---------- Voice AI service I/O ----------
async def get_jwt_token(*, voice_ai_app_url: str, username: str, password: str,
                        call_id: str, t_connect: float, t_read: float) -> str:
    payload = {
        "user_id": username,
        "user_password": password,
        "ccaas_call_id": call_id,
        "caller_id": "notion-voice",
    }
    timeout = httpx.Timeout(t_connect, read=t_read)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{voice_ai_app_url}/api/auth/ccaas", json=payload)
        r.raise_for_status()
        return (r.json().get("data") or {}).get("jwt_token", "")


async def initiate_call(*, voice_ai_app_url: str, username: str, token: str,
                        call_id: str, t_connect: float, t_read: float) -> str | None:
    payload = {
        "ccaas_call_id": call_id,
        "user_id": username,
        "call_type": "to-do-list"
    }
    timeout = httpx.Timeout(t_connect, read=t_read)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            f"{voice_ai_app_url}/api/call/initiate-call",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r.json().get("data")  # join_url


async def terminate_call(*, voice_ai_app_url: str, username: str, token: str,
                         call_id: str, t_connect: float, t_read: float) -> None:
    payload = {
        "ccaas_call_id": call_id,
        "user_id": username,
        "call_type": "to-do-list"
    }
    timeout = httpx.Timeout(t_connect, read=t_read)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            f"{voice_ai_app_url}/api/call/terminate-call",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
