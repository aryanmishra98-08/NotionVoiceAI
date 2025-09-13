from setup_loader_app import logger
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from modules.api_routes.APIResponse import APIResponse
from modules.api_routes.APISchemaComponent import LLMSignInRequest, CCAASSignInRequest
from modules.api_modules.AuthHandlingComponent import handle_auth_with_service_acc_and_call_id

# Initialize the API router
router = APIRouter()

# Initialize the rate limiter with a key function based on the client's IP address
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/auth/ccaas",
    tags=["Authentication"]
)
@limiter.limit("20/minute")
async def ccaas_login_endpoint(
    request: Request,
    request_data: CCAASSignInRequest
):
    """
    Authenticate a service account and provide a JWT token.
    """
    try:
        # Handle the login process
        result = handle_auth_with_service_acc_and_call_id(
            service_account_id=request_data.user_id,
            ccaas_call_id=request_data.ccaas_call_id,
            caller_id=request_data.caller_id,
            service_account_password=request_data.user_password.get_secret_value()
        )
        logger.info("Authentication handling result: %s", result)

        if result["status"]:
            logger.info("Authentication successful for user_id: %s",
                        request_data.user_id)
            response = APIResponse(
                output=result["output"],
                message=result["message"]
            )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response.__dict__
            )
        else:
            logger.error("Authentication failed for user_id: %s - %s",
                         request_data.user_id, result["message"])
            response = APIResponse(
                message=result["message"]
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=response.__dict__
            )
    except Exception as e:
        logger.exception(
            "An error occurred during authentication for user_id %s: %s", request_data.user_id, str(e))
        response = APIResponse(
            message=str(e)
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.__dict__
        )
