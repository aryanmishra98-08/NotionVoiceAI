from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from twilio.request_validator import RequestValidator
from modules.telephony import (
    validate_twilio_request, parse_request_data,
    get_jwt_token, initiate_call, terminate_call,
    pause_then_connect, error_play,
)


# ---------- Schemas (merged here) ----------
class ConnectPayload(BaseModel):
    CallSid: str


class DisconnectPayload(ConnectPayload):
    CallStatus: str | None = None


# ---------- Router factory ----------
def _twilio_dep(validator: RequestValidator):
    async def _inner(request: Request):
        await validate_twilio_request(request, validator)
    return _inner


def build_router(config: dict, validator: RequestValidator) -> APIRouter:
    router = APIRouter()

    # -------- /connect --------
    @router.post("/connect", tags=["Connect API"], dependencies=[Depends(_twilio_dep(validator))])
    async def connect_call(request: Request) -> Response:
        data = await parse_request_data(request)
        call_sid = ConnectPayload(**data).CallSid

        try:
            token = await get_jwt_token(
                voice_ai_app_url=config["voice_ai_app"]["voice_ai_app_url"],
                username=config["voice_ai_app"]["username"],
                password=config["voice_ai_app"]["password"],
                call_id=call_sid,
                t_connect=config["voice_ai_app"]["timeout_connect"],
                t_read=config["voice_ai_app"]["timeout_read"],
            )
            join_url = await initiate_call(
                voice_ai_app_url=config["voice_ai_app"]["voice_ai_app_url"],
                username=config["voice_ai_app"]["username"],
                token=token,
                call_id=call_sid,
                t_connect=config["voice_ai_app"]["timeout_connect"],
                t_read=config["voice_ai_app"]["timeout_read"],
            )
            vr = pause_then_connect(join_url) if join_url else error_play(
                config["voices"]["internal_error_voice_play_url"])
        except Exception:
            vr = error_play(config["voices"]["internal_error_voice_play_url"])

        return Response(content=str(vr), media_type="application/xml")

    # -------- /disconnect --------
    @router.post("/disconnect", tags=["Disconnect API"], dependencies=[Depends(_twilio_dep(validator))])
    async def disconnect_call(request: Request):
        data = await parse_request_data(request)
        payload = DisconnectPayload(**data)
        call_sid = payload.CallSid
        call_status = (payload.CallStatus or "").lower()

        try:
            if call_status == "completed":
                token = await get_jwt_token(
                    voice_ai_app_url=config["voice_ai_app"]["voice_ai_app_url"],
                    username=config["voice_ai_app"]["username"],
                    password=config["voice_ai_app"]["password"],
                    call_id=call_sid,
                    t_connect=config["voice_ai_app"]["timeout_connect"],
                    t_read=config["voice_ai_app"]["timeout_read"],
                )
                await terminate_call(
                    voice_ai_app_url=config["voice_ai_app"]["voice_ai_app_url"],
                    username=config["voice_ai_app"]["username"],
                    token=token,
                    call_id=call_sid,
                    t_connect=config["voice_ai_app"]["timeout_connect"],
                    t_read=config["voice_ai_app"]["timeout_read"],
                )
                msg = f"Call disconnected with status '{call_status}'"
            else:
                msg = f"Call status '{call_status}' received, no action taken"

            return JSONResponse(status_code=status.HTTP_200_OK, content={"message": msg})
        except Exception:
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": "Error disconnecting call"})

    return router
