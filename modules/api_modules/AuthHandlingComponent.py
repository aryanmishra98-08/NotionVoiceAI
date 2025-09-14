from setup_loader import config_data, logger
from datetime import datetime, timezone
from modules.service_modules.DynamoDBManager import DynamoDBManager
from modules.service_modules.JWTAuthentication import *

# Extract configuration values
# AWS Configuration
region_name = config_data['aws']['region']
service_account_table = config_data['aws']['dynamodb']['service_account_records_table']
call_records_table = config_data['aws']['dynamodb']['call_records_table']

# Initialize Managers
service_account_table_manager = DynamoDBManager(
    region_name, service_account_table
)
call_records_table_manager = DynamoDBManager(
    region_name, call_records_table
)


def handle_auth_with_service_acc_and_call_id(service_account_id, ccaas_call_id, caller_id, service_account_password):
    """
    Handle agent login authentication.

    This function verifies the agent's credentials by comparing the provided password with the stored password.
    If authentication is successful and the agent is active, it generates a JWT token for the session.

    Args:
        service_account_id (str): The ID of the service account.
        ccaas_call_id (str): The ID of the CCAAS call.
        caller_id (str): The caller ID associated with the CCAAS call.
        service_account_password (str): The password provided by the service account for login.

    Returns:
        A dict with status, message, output, and error details. If successful, a JWT token is included in the output.
    """
    try:
        # Define the key to locate the agent record
        key = {'service_account_id': service_account_id}
        record = service_account_table_manager.get_item_by_id(key)

        # Check if the agent record exists
        decrypt_password = decrypt_data_result(service_account_password)
        if record['status'] and record['output'] != []:
            stored_password_encrypted = record['output'].get(
                'service_account_password', '')
            account_status = record['output'].get(
                'service_account_status', '')
            stored_password = decrypt_data_result(
                stored_password_encrypted)

            # Verify the provided password against the stored password
            if stored_password == decrypt_password and account_status == 'true':

                # Generate JWT token
                jwt_result = sign_jwt_with_service_acc_and_call_id(
                    service_account_id, ccaas_call_id, caller_id)
                jwt_token = jwt_result.get("access_token", "")

                logger.info(
                    f"Authentication successful for service account ID {service_account_id}. JWT generated.")

                # Store user details in call_records_table
                call_record = call_records_table_manager.get_item_by_id(
                    {"ccaas_call_id": ccaas_call_id})
                if call_record['status'] and call_record['output'] != []:
                    logger.info(
                        f"User details already exist for call ID: {ccaas_call_id}.")
                    return {
                        "status": True,
                        "message": "Authentication Successful",
                        "output": {
                            "jwt_token": jwt_token
                        },
                        "error": ""
                    }

                logger.info(
                    f"Storing user details for call ID: {ccaas_call_id}")

                # Create record to insert
                record = {
                    "ccaas_call_id": ccaas_call_id,
                    "ultravox_call_id": "",
                    "caller_id": caller_id,
                    "call_start_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                    "call_end_time": "",
                    "call_type": "",
                    "call_status": "",
                }

                # Insert the record into call_records_table
                result = call_records_table_manager.insert_item(record)

                if result['status']:
                    logger.info(
                        f"Record inserted successfully for call ID: {ccaas_call_id}")
                else:
                    logger.error(
                        f"Authentication successful for ID {service_account_id}. BUT record insertion failed for ccaas call id: {ccaas_call_id}.")
                    return {
                        "status": False,
                        "message": "Authentication successful BUT record insertion failed",
                        "output": {},
                        "error": "Authentication successful BUT record insertion failed"
                    }

                return {
                    "status": True,
                    "message": "Authentication Successful",
                    "output": {
                        "jwt_token": jwt_token
                    },
                    "error": ""
                }
            else:
                logger.error(
                    f"Authentication failed: Incorrect password or account inactive for service account ID {service_account_id}.")
                return {
                    "status": False,
                    "message": "Authentication Failed - Wrong Password or Account Inactive",
                    "output": {},
                    "error": ""
                }
        else:
            logger.error(
                f"Authentication failed: Service account ID {service_account_id} does not exist.")
            return {
                "status": False,
                "message": "Authentication Failed - User does not exist",
                "output": {},
                "error": ""
            }

    except Exception as e:
        logger.error(
            f"Exception occurred during login for service account ID {service_account_id}: {e}")
        return {
            "status": False,
            "message": f"Authentication Failed - {str(e)}",
            "output": {},
            "error": ""
        }
