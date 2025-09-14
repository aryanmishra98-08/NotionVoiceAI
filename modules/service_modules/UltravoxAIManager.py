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

    def create_agent_call(self, agent_id, payload):
        """
        Create a call in Ultravox using the provided payload.

        Args:
            agent_id (str): The ID of the agent to create the call form.
            payload (dict): The payload to send in the API request.

        Returns:
            dict: A dictionary containing the status, a message, the call details,
                  and error information if applicable.
        """
        try:
            url = f"{self.base_url}/agents/{agent_id}/calls"
            response = requests.post(url, json=payload, headers=self.headers)

            logger.info("Request URL: %s", response.url)
            logger.info("Response Status: %s", response.status_code)
            logger.info("Response Body: %s", response.text)

            # Check for success (HTTP 200 or 201)
            if response.status_code in [200, 201]:
                call_details = response.json()
                logger.info("Call created successfully.")
                return {
                    'status': True,
                    'message': "Call created successfully",
                    'output': call_details,
                    'error': ''
                }
            else:
                error_message = f"Request failed with status code {response.status_code}: {response.text}"
                logger.error(error_message)
                return {
                    'status': False,
                    'message': "Failed to create call",
                    'output': '',
                    'error': error_message
                }
        except Exception as e:
            error_message = f"Exception occurred: {e}"
            logger.error(error_message)
            return {
                'status': False,
                'message': "Failed to create call",
                'output': '',
                'error': error_message
            }
