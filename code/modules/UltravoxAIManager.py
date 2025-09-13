from setup_loader import config_data, logger
import requests


class UltravoxAIManager:
    """
    A manager class for interacting with Ultravox.
    """

    def __init__(self):
        """
        Initialize the UltravoxAIManager with API credentials and headers.
        """
        self.base_url = config_data['ultravox']['base_url']
        self.headers = {
            "X-API-Key": config_data['ultravox']['api_key'],
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def list_call_messages(self, ultravox_call_id):
        """
        Retrieve and format all messages generated during a call.

        Args:
            ultravox_call_id (str): The call ID from Ultravox to retrieve messages.

        Returns:
            dict: A dictionary containing the status, a message, formatted output of messages,
                    and error information if applicable.
        """
        try:
            url = f"{self.base_url}/calls/{ultravox_call_id}/messages"
            response = requests.get(url, headers=self.headers)

            logger.info("Request URL: %s", response.url)
            logger.info("Response Status: %s", response.status_code)
            logger.info("Response Body: %s", response.text)

            if response.status_code == 200:
                conversation = response.json()
                formatted_messages = ""

                results = conversation.get('results', [])
                if isinstance(results, list):
                    for message in results:
                        text = message.get('text', '')
                        if text:
                            role = message.get('role', '')
                            if role == "MESSAGE_ROLE_USER":
                                formatted_messages += f"userMessage: '{text}'\n"
                            elif role == "MESSAGE_ROLE_AGENT":
                                formatted_messages += f"AgentMessage: '{text}'\n"

                    logger.info("Messages fetched and formatted successfully for call ID: %s",
                                ultravox_call_id)
                    logger.info("Formatted Messages: %s", formatted_messages)
                    return {
                        'status': True,
                        'message': f"Messages fetched and formatted successfully for call ID: {ultravox_call_id}",
                        'output': formatted_messages,
                        'error': ''
                    }

            error_message = f"Request failed with status code {response.status_code}: {response.text}"
            logger.error(error_message)
            return {
                'status': False,
                'message': f"Failed to fetch conversation for call ID: {ultravox_call_id}",
                'output': '',
                'error': error_message
            }

        except Exception as e:
            error_message = f"Exception occurred: {e}"
            logger.error(error_message)
            return {
                'status': False,
                'message': "Failed to fetch conversation",
                'output': '',
                'error': error_message
            }
