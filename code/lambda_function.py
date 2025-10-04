from setup_loader import config_data, logger
from modules.DynamoDBManager import DynamoDBManager
from modules.NotionManager import NotionManager
from modules.UltravoxAIManager import UltravoxAIManager
from modules.AIManager import AzureAIManager
from datetime import datetime
import json


def process_call(ccaas_call_id, call_type):
    try:
        dynamodb_manager = DynamoDBManager(
            region_name=config_data['aws']['region'],
            table_name=config_data['aws']['dynamodb']['call_records_table']
        )
        notion_manager = NotionManager()
        ultravox_ai_manager = UltravoxAIManager()
        azure_ai_manager = AzureAIManager()

        # Get call record
        call_record = dynamodb_manager.get_item_by_id({"ccaas_call_id": ccaas_call_id})
        if not call_record['status']:
            logger.warning(f"Call record not found for ID: {ccaas_call_id}")
            return {
                "status": False,
                "message": "Call record not found",
                "output": {},
                "error": "Call record not found"
            }
        
        # Capture Ultravox CallID
        ultravox_call_id = call_record['output'].get("ultravox_call_id", "")
        if not ultravox_call_id:
            logger.warning(f"Ultravox Call ID not found for ID: {ccaas_call_id}")
            return {
                "status": False,
                "message": "Ultravox Call ID not found",
                "output": {},
                "error": "Ultravox Call ID not found"
            }
        
        # Extract call conversationid using ultravox call id
        transcript = ultravox_ai_manager.list_call_messages(ultravox_call_id)
        if not transcript['status']:
            logger.warning(f"Failed to retrieve transcript for Ultravox Call ID: {ultravox_call_id}")
            return {
                "status": False,
                "message": "Failed to retrieve transcript",
                "output": {},
                "error": transcript['error']
            }

        formatted_transcript = transcript['output']

        # Get current date and time
        today = datetime.now()
        # Format: Monday, 04 October 2025
        formatted_date = today.strftime("%A, %d %B %Y")

        # Further processing of formatted transcript based on call type
        if call_type == "to-do-list":
            prompt = config_data['prompts']['todo_page'].replace("<<today>>", formatted_date)
            azure_response = azure_ai_manager.prompt_execution(
                prompt=formatted_transcript,
                system_prompt=prompt
            )
            if not azure_response['status']:
                logger.warning(f"Failed to process to-do prompt: {azure_response['error']}")
                return {
                    "status": False,
                    "message": "Failed to process to-do prompt",
                    "output": {},
                    "error": azure_response['error']
                }
            logger.info("Azure Response: %s", azure_response)
            notion_template = list(azure_response['output']['tasks'])

            notion_response = notion_manager.create_to_do_list(notion_template)
            if not notion_response['status']:
                logger.warning(f"Failed to create Notion to-do list: {notion_response['error']}")
                return {
                    "status": False,
                    "message": "Failed to create Notion to-do list",
                    "output": {},
                    "error": notion_response['error']
                }
            
            return {
                "status": True,
                "message": "Notion to-do list created successfully",
                "output": "",
                "error": ""
            }

        else:
            prompt = config_data['prompts']['journal_page'].replace("<<today>>", formatted_date)
            azure_response = azure_ai_manager.prompt_execution(
                prompt=formatted_transcript,
                system_prompt=prompt
            )
            if not azure_response['status']:
                logger.warning(f"Failed to process journal prompt: {azure_response['error']}")
                return {
                    "status": False,
                    "message": "Failed to process journal prompt",
                    "output": {},
                    "error": azure_response['error']
                }
            logger.info("Azure Response: %s", azure_response)
            notion_template = str(azure_response['output']['journal'])

            notion_response = notion_manager.create_journal_entry(notion_template)
            if not notion_response['status']:
                logger.warning(f"Failed to create Notion journal entry: {notion_response['error']}")
                return {
                    "status": False,
                    "message": "Failed to create Notion journal entry",
                    "output": {},
                    "error": notion_response['error']
                }

            return {
                "status": True,
                "message": "Notion journal entry created successfully",
                "output": "",
                "error": ""
            }
    
    except Exception as e:
        logger.error(f"Error processing call: {str(e)}")
        return {
            "status": False,
            "message": "Error processing call",
            "output": {},
            "error": str(e)
        }


def lambda_handler(event, context):
    try:
        # 1. Extract ccaas_call_id and call_type from the event
        ccaas_call_id = event.get('ccaas_call_id', '')
        call_type = event.get('call_type', '')

        if call_type or ccaas_call_id:
            logger.info(
                f"Processing call ID: {ccaas_call_id}, Call Type: {call_type}")
            result = process_call(ccaas_call_id, call_type)
            if result['status']:
                return {
                    'statusCode': 200,
                    'body': json.dumps({'status': 'success', 'ccaas_call_id': ccaas_call_id})
                }
            else:
                return {
                    'statusCode': 500,
                    'body': json.dumps({'status': 'error', 'message': 'Failed to process call'})
                }

        else:
            logger.warning(
                f"Missing call ID or type. Call ID: {ccaas_call_id}, Call Type: {call_type}")
            return {
                'statusCode': 400,
                'body': json.dumps({'status': 'error', 'message': 'Missing call ID or type'})
            }

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'status': 'error', 'message': str(e)})
        }
