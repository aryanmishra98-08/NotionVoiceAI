from setup_loader import config_data, logger
from notion_client import Client
from notion_client.errors import APIResponseError, RequestTimeoutError
from datetime import datetime


class NotionManager:
    """
    A manager class for interacting with Notion.

    This class provides high-level helpers to create:
    - Daily journal entries under a given parent page
    - Daily to-do lists under a given parent page
    """

    def __init__(self):
        """
        Initialize the NotionManager with API credentials and parent page IDs.

        Args:
            token (str): Notion integration token.
            journal_page_id (str): Parent page ID for journal entries.
            todo_page_id (str): Parent page ID for to-do lists.
        """
        self.notion = Client(auth=config_data['notion']['token'])
        self.journal_page_id = config_data['notion']['journal_page_id']
        self.todo_page_id = config_data['notion']['todo_page_id']

    def _get_date_title(self):
        """
        Build a date string used in page titles.

        Returns:
            str: Date formatted as YYYY-MM-DD.
        """
        return datetime.now().strftime("%Y-%m-%d")

    def _make_title_property(self, title):
        """
        Construct a Notion title property payload.

        Args:
            title (str): The page title.

        Returns:
            dict: Notion "title" property for page creation.
        """
        # Mirrors your original structure for compatibility
        return {
            "title": [
                {
                    "type": "text",
                    "text": {"content": title}
                }
            ]
        }

    # ---------- Public Methods ----------

    def create_journal_entry(self, content):
        """
        Create a dated journal entry under the configured journal parent page.

        Args:
            content (str): The journal entry text.

        Returns:
            dict: Structured response with page object on success.
        """
        try:
            date_title = self._get_date_title()
            title = f"Journal - {date_title}"

            payload = {
                "parent": {"page_id": self.journal_page_id},
                "properties": self._make_title_property(title),
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": content}
                            }]
                        }
                    }
                ]
            }

            page = self.notion.pages.create(**payload)
            logger.info("Notion journal entry created successfully")

            return {
                'status': True,
                'message': 'Journal entry created successfully',
                'output': page,
                'error': ''
            }

        except (APIResponseError, RequestTimeoutError) as e:
            error_message = f"Notion API error creating journal entry: {getattr(e, 'message', str(e))}"
            logger.exception(error_message)
            return {
                'status': False,
                'message': error_message,
                'output': [],
                'error': error_message
            }
        except Exception as e:
            error_message = f"Error creating journal entry: {e}"
            logger.exception(error_message)
            return {
                'status': False,
                'message': error_message,
                'output': [],
                'error': error_message
            }

    def create_to_do_list(self, tasks):
        """
        Create a dated to-do list page with unchecked tasks under the configured to-do parent page.

        Args:
            tasks (list): List of task strings.

        Returns:
            dict: Structured response with page object on success.
        """
        try:
            if not isinstance(tasks, list):
                raise ValueError("`tasks` must be a list of strings")

            date_title = self._get_date_title()
            title = f"To-Do - {date_title}"

            todo_blocks = [
                {
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": str(task)}
                        }],
                        "checked": False
                    }
                }
                for task in tasks
            ]

            payload = {
                "parent": {"page_id": self.todo_page_id},
                "properties": self._make_title_property(title),
                "children": todo_blocks
            }

            page = self.notion.pages.create(**payload)
            logger.info("Notion to-do list created successfully")

            return {
                'status': True,
                'message': 'To-do list created successfully',
                'output': page,
                'error': ''
            }

        except (APIResponseError, RequestTimeoutError) as e:
            error_message = f"Notion API error creating to-do list: {getattr(e, 'message', str(e))}"
            logger.exception(error_message)
            return {
                'status': False,
                'message': error_message,
                'output': [],
                'error': error_message
            }
        except Exception as e:
            error_message = f"Error creating to-do list: {e}"
            logger.exception(error_message)
            return {
                'status': False,
                'message': error_message,
                'output': [],
                'error': error_message
            }
