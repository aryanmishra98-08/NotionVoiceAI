from setup_loader_app import config_data, logger
import boto3
import json
from datetime import datetime, timezone
from modules.service_modules.DynamoDBManager import DynamoDBManager
from modules.service_modules.UltravoxAIManager import UltravoxAIManager

# Extract configuration values
# AWS Configuration
region_name = config_data['aws']['region']
call_records_table = config_data['aws']['dynamodb']['call_records_table']
call_termination_lambda = config_data['aws']['lambda']['call_termination_lambda']
to_do_list_agent_id = config_data['ultravox']['to_do_list_agent_id']
journaling_agent_id = config_data['ultravox']['journaling_agent_id']

# Initialize Managers
lambda_client = boto3.client(
    'lambda', region_name=region_name)
db_manager = DynamoDBManager(
    region_name, call_records_table)
ultravox_manager = UltravoxAIManager()


def handle_ultravox_agent_call_initiation(ccaas_call_id, call_type):
    """
    Handle the initiation of an Ultravox agent call.

    This function initiates an Ultravox agent call, updates the corresponding call record in DynamoDB with the call type,
    and performs any necessary setup for the call session.

    Args:
        ccaas_call_id (str): The unique identifier for the CCAAS call.
        call_type (str): The type of the call being initiated.

    Returns:
        A dict with status, message, output (call details), and error details.
    """
    try:
        # Get the call record from DynamoDB
        key = {'ccaas_call_id': ccaas_call_id}
        call_record = db_manager.get_item_by_id(key)
        if not call_record['status'] or (call_record['status'] and call_record['output'] == []):
            logger.error(
                "Call record not found for ccaas_call_id: %s", ccaas_call_id)
            return {
                "status": False,
                "message": "Call record not found",
                "output": None,
                "error": "Call record not found"
            }

        if call_record['output']['call_status'] == 'initiated':
            logger.error(
                "Call already initiated for ccaas_call_id: %s", ccaas_call_id)
            return {
                "status": False,
                "message": "Call already initiated",
                "output": None,
                "error": "Call already initiated"
            }

        # Create the Ultravox agent call
        if call_type == 'to-do-list':
            agent_id = to_do_list_agent_id
        elif call_type == 'journaling':
            agent_id = journaling_agent_id

        call_details = ultravox_manager.create_agent_call(
            agent_id, {"medium": {"twilio": {}}})
        if not call_details['status']:
            logger.error(
                "Failed to create Ultravox call for ccaas_call_id: %s - %s",
                ccaas_call_id, call_details['error'])
            return {
                "status": False,
                "message": "Failed to create Ultravox call",
                "output": None,
                "error": call_details['error']
            }

        join_url = call_details['output']['joinUrl']
        ultravox_call_id = call_details['output']['callId']

        # Update the call record with the call type
        update_result = db_manager.update_item_with_dict_payload(
            key,
            {
                'call_type': call_type,
                'call_status': 'initiated',
                'call_start_time': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                'ultravox_call_id': ultravox_call_id,
            },
            "attribute_exists(ccaas_call_id)"
        )
        if not update_result['status']:
            logger.error(
                "Failed to update call record for ccaas_call_id: %s - %s",
                ccaas_call_id, update_result['error'])
            return {
                "status": False,
                "message": "Failed to update call record",
                "output": None,
                "error": update_result['error']
            }

        logger.info(
            "Successfully initiated Ultravox call for ccaas_call_id: %s", ccaas_call_id)
        return {
            "status": True,
            "message": "Successfully initiated Ultravox call",
            "output": join_url,
            "error": None
        }

    except Exception as e:
        logger.exception(
            "An error occurred while initiating Ultravox call for ccaas_call_id %s: %s", ccaas_call_id, str(e))
        return {
            "status": False,
            "message": "An error occurred while initiating Ultravox call",
            "output": None,
            "error": str(e)
        }


def handle_ultravox_agent_call_termination(ccaas_call_id, call_type):
    """
    Handle the termination of an Ultravox agent call.
    """
    try:
        # Get the call record from DynamoDB
        key = {'ccaas_call_id': ccaas_call_id}
        call_record = db_manager.get_item_by_id(key)
        if not call_record['status'] or (call_record['status'] and call_record['output'] == []):
            logger.error(
                "Call record not found for ccaas_call_id: %s", ccaas_call_id)
            return {
                "status": False,
                "message": "Call record not found",
                "output": None,
                "error": "Call record not found"
            }

        if call_record['output']['call_status'] == 'terminated':
            logger.error(
                "Call already terminated for ccaas_call_id: %s", ccaas_call_id)
            return {
                "status": False,
                "message": "Call already terminated",
                "output": None,
                "error": "Call already terminated"
            }

        # Invokes a lambda function to initiate the call termination process
        payload = {
            'ccaas_call_id': ccaas_call_id,
            'call_type': call_type
        }

        lambda_client.invoke(
            FunctionName=call_termination_lambda,
            InvocationType='Event',  # Use 'Event' for async execution and RequestResponse for sync
            Payload=json.dumps(payload),
        )

        # Update the call record with the call type
        update_result = db_manager.update_item_with_dict_payload(
            key,
            {
                'call_status': 'terminated',
                'call_end_time': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            },
            "attribute_exists(ccaas_call_id)"
        )
        if not update_result['status']:
            logger.error(
                "Failed to update call record for ccaas_call_id: %s - %s",
                ccaas_call_id, update_result['error'])
            return {
                "status": False,
                "message": "Failed to update call record",
                "output": None,
                "error": update_result['error']
            }

        logger.info(
            "Successfully terminated Ultravox call for ccaas_call_id: %s", ccaas_call_id)
        return {
            "status": True,
            "message": "Successfully terminated Ultravox call",
            "output": None,
            "error": None
        }

    except Exception as e:
        logger.exception(
            "An error occurred while terminating Ultravox call for ccaas_call_id %s: %s", ccaas_call_id, str(e))
        return {
            "status": False,
            "message": "An error occurred while terminating Ultravox call",
            "output": None,
            "error": str(e)
        }
