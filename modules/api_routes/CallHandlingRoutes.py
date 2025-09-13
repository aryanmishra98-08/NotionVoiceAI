from setup_loader_app import logger
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from modules.service_modules.JWTAuthentication import JWTBearerWithServiceAccAndCallID
from modules.api_routes.APIResponse import APIResponse
from modules.api_routes.APISchemaComponent import CallRequest
from modules.api_modules.CallHandelingComponent import *

# Initialize the API router
router = APIRouter()

# Initialize managers
jwt_bearer_with_serv_acc_call_id = JWTBearerWithServiceAccAndCallID()

# Initialize the rate limiter with a key function based on the client's IP address
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/call/initiate-call",
    tags=["CCAAS"]
)
@limiter.limit("20/minute")
async def create_ultravox_call(
    request: Request,
    request_data: CallRequest,
    token: str = Depends(JWTBearerWithServiceAccAndCallID())
):
    """
    Create an Ultravox agent call.
    """
    try:
        # Verify JWT token
        if not jwt_bearer_with_serv_acc_call_id.verify_jwt(token, request_data.user_id, request_data.ccaas_call_id):
            logger.error(
                "Invalid JWT token provided for the ccaas_call_id: %s",
                request_data.ccaas_call_id
            )
            response = APIResponse(message="Invalid Token")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=response.__dict__
            )
        
        # Handle service request status check
        result = handle_ultravox_agent_call_initiation(
            request_data.ccaas_call_id, request_data.call_type)
        logger.info("Ultravox call creation result: %s", result)

        # Return response based on result
        if result["status"]:
            logger.info("Successfully created ultravox call: %s",
                        request_data.ccaas_call_id)
            response = APIResponse(
                output=result["output"],
                message=result["message"]
            )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response.__dict__
            )
        else:
            logger.error(
                "Failed to create ultravox call for Twilio call ID %s: %s",
                request_data.ccaas_call_id, result["message"]
            )
            response = APIResponse(message=result["message"])
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=response.__dict__
            )
    except Exception as e:
        logger.exception(
            "An error occurred while creating ultravox call: %s", str(e))
        response = APIResponse(message=str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.__dict__
        )


@router.post(
    "/call/terminate-call",
    tags=["CCAAS"]
)
@limiter.limit("20/minute")
async def terminate_ultravox_call(
    request: Request,
    request_data: CallRequest,
    token: str = Depends(JWTBearerWithServiceAccAndCallID())
):
    """
    Terminate an Ultravox agent call.
    """
    try:
        # Verify JWT token
        if not jwt_bearer_with_serv_acc_call_id.verify_jwt(token, request_data.user_id, request_data.ccaas_call_id):
            logger.error(
                "Invalid JWT token provided for the ccaas_call_id: %s",
                request_data.ccaas_call_id
            )
            response = APIResponse(message="Invalid Token")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=response.__dict__
            )
        
        # Handle service request status check
        result = handle_ultravox_agent_call_termination(
            request_data.ccaas_call_id, request_data.call_type)
        logger.info("Ultravox call termination result: %s", result)

        # Return response based on result
        if result["status"]:
            logger.info("Successfully terminated ultravox call: %s",
                        request_data.ccaas_call_id)
            response = APIResponse(
                output=result["output"],
                message=result["message"]
            )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response.__dict__
            )
        else:
            logger.error(
                "Failed to terminate ultravox call for Twilio call ID %s: %s",
                request_data.ccaas_call_id, result["message"]
            )
            response = APIResponse(message=result["message"])
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=response.__dict__
            )
    except Exception as e:
        logger.exception(
            "An error occurred while terminating ultravox call: %s", str(e))
        response = APIResponse(message=str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.__dict__
        )
