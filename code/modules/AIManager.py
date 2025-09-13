from setup_loader import config_data, logger
import json
from openai import AzureOpenAI


class AzureAIManager:
    """
    A manager class for interacting with the Azure AI service.

    This class initializes an AzureOpenAI client for the Azure AI service and provides methods to execute prompts
    using the Azure AI model.
    """

    def __init__(self):
        """
        Initialize the AzureAIManager with the necessary credentials and configuration.

        Sets up the logger, loads Azure credentials from the configuration, and initializes the AzureOpenAI client.
        """
        self.logger = logger
        self.azure = AzureOpenAI(
            api_version=config_data['azure']['api_version'],
            api_key=config_data['azure']['api_key'],
            azure_endpoint=config_data['azure']['api_base']
        )

    def prompt_execution(self, prompt, system_prompt=""):
        """
        Execute a prompt using the Azure AI model.

        This method constructs the message payload, invokes the Azure AI model, and processes the response.

        :param prompt: The prompt to be executed by the Azure AI model.
        :param system_prompt: The system prompt to be used by the AI model.
        :return: A dictionary containing the status, output, message, and error details (if any).
        """
        try:
            self.logger.info('Azure AI Call')

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

            response = self.azure.chat.completions.create(
                model=config_data['azure']['openai']['model_id'],
                messages=messages,
                temperature=config_data['azure']['openai']['temperature'],
                response_format={"type": "json_object"}
            )

            raw_text = response.choices[0].message.content

            result_dict = json.loads(raw_text)
            return {
                'status': True,
                'message': 'GenAI processing completed',
                'output': result_dict,
                'error': ''
            }

        except Exception as e:
            error_message = f'Exception occurred: {e}'
            self.logger.exception(error_message)
            return {
                'status': False,
                'message': error_message,
                'output': '',
                'error': error_message
            }
