from setup_loader_app import logger
import boto3
from botocore.exceptions import ClientError


class DynamoDBManager:
    """
    A manager class for interacting with AWS DynamoDB.

    This class provides methods for common DynamoDB operations, such as retrieving,
    scanning, inserting, updating, deleting, and querying items, as well as handling pagination
    and conditional updates.
    """

    def __init__(self, region_name, table_name):
        """
        Initialize the DynamoDBManager with the specified AWS credentials and table name.

        This function sets up the DynamoDB resource and table using the provided AWS credentials and region.

        Args:
            region_name (str): The AWS region name.
            table_name (str): The name of the DynamoDB table to manage.
        """
        self.table_name = table_name
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=region_name,
        )
        self.table = self.dynamodb.Table(table_name)

    def get_item_by_id(self, key):
        """
        Retrieve an item from the DynamoDB table by its key.

        This function retrieves an item from the DynamoDB table using the provided key.
        It logs the success or failure of the operation and returns a dictionary with the status, message, output, and error information.

        Args:
            key (dict): A dictionary representing the key of the item to retrieve.

        Returns:
            dict: A dictionary with status, message, output (item), and error information.
        """
        try:
            response = self.table.get_item(Key=key)
            item = response.get('Item', [])
            logger.info("Item retrieved successfully")
            return {
                'status': True,
                'message': '',
                'output': item,
                'error': ''
            }
        except ClientError as e:
            error_message = f"Error retrieving item: {e.response['Error']['Message']}"
            logger.exception(error_message)
            return {
                'status': False,
                'message': error_message,
                'output': [],
                'error': error_message
            }
        except Exception as e:
            error_message = f"Error retrieving item: {e}"
            logger.exception(error_message)
            return {
                'status': False,
                'message': error_message,
                'output': [],
                'error': error_message
            }

    def scan_entire_table(self, filter_expression=None, expression_attribute_values=None):
        """
        Scan the entire DynamoDB table with a filter expression and expression attribute values.

        This function scans the entire DynamoDB table using the provided filter expression and expression attribute values.
        It handles pagination by repeatedly scanning until all items are retrieved. It logs the success or failure of the operation
        and returns a dictionary with the status, message, output (items), and error information.

        Args:
            filter_expression (str, optional): The filter expression for scanning the table. Defaults to None.
            expression_attribute_values (dict, optional): A dictionary of expression attribute values used in the filter expression. Defaults to None.

        Returns:
            dict: A dictionary with status, message, output (items), and error information.
        """
        try:
            items = []
            last_evaluated_key = None
            while True:
                scan_params = {}
                if filter_expression:
                    scan_params['FilterExpression'] = filter_expression
                if expression_attribute_values:
                    scan_params['ExpressionAttributeValues'] = expression_attribute_values
                # Include ExclusiveStartKey only if it's not None
                if last_evaluated_key:
                    scan_params['ExclusiveStartKey'] = last_evaluated_key
                # Perform the scan operation
                response = self.table.scan(**scan_params)
                # Collect the items from this scan
                items.extend(response.get('Items', []))
                # Check if there's more data to be retrieved
                last_evaluated_key = response.get('LastEvaluatedKey')
                # If no more data, break the loop
                if not last_evaluated_key:
                    break
            logger.info("Table scanned successfully")
            return {
                'status': True,
                'message': '',
                'output': items,
                'error': ''
            }
        except ClientError as e:
            error_message = f"Error scanning table: {e.response['Error']['Message']}"
            logger.exception(error_message)
            return {
                'status': False,
                'message': error_message,
                'output': [],
                'error': error_message
            }
        except Exception as e:
            error_message = f"Error scanning table: {e}"
            logger.exception(error_message)
            return {
                'status': False,
                'message': error_message,
                'output': [],
                'error': error_message
            }

    def insert_item(self, item_data):
        """
        Insert an item into the DynamoDB table.

        This function inserts an item into the DynamoDB table using the provided item data.
        It logs the success or failure of the operation and returns a dictionary with the status, message, output, and error information.

        Args:
            item_data (dict): A dictionary representing the item to insert.

        Returns:
            dict: A dictionary with status, message, output (response), and error information.
        """
        try:
            response = self.table.put_item(
                Item=item_data
            )
            logger.info("Item inserted successfully")
            return {
                'status': True,
                'message': 'Item inserted successfully',
                'output': response,
                'error': ''
            }
        except ClientError as e:
            error_message = f"Error inserting item: {e.response['Error']['Message']}"
            logger.exception(error_message)
            return {
                'status': False,
                'message': error_message,
                'output': [],
                'error': error_message
            }
        except Exception as e:
            error_message = f"Error inserting item: {e}"
            logger.exception(error_message)
            return {
                'status': False,
                'message': error_message,
                'output': [],
                'error': error_message
            }

    def update_item(self, key, update_expression, expression_attribute_values, condition_expression):
        """
        Update an item in the DynamoDB table by key with an update expression and condition expression.

        This function updates an item in the DynamoDB table using the provided key, update expression, expression attribute values,
        and condition expression. It logs the success or failure of the operation and returns a dictionary with the status, message, output, and error information.

        Args:
            key (dict): A dictionary representing the key of the item to update.
            update_expression (str): The update expression for modifying the item.
            expression_attribute_values (dict): A dictionary of expression attribute values used in the update expression.
            condition_expression (str): The condition expression for conditional updates.

        Returns:
            dict: A dictionary with status, message, output (response), and error information.
        """
        try:
            response = self.table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ConditionExpression=condition_expression
            )
            logger.info("Item updated successfully")
            return {
                'status': True,
                'message': 'Item updated successfully',
                'output': response,
                'error': ''
            }
        except ClientError as e:
            error_message = f"Error updating item: {e.response['Error']['Message']}"
            logger.exception(error_message)
            return {
                'status': False,
                'message': error_message,
                'output': [],
                'error': error_message
            }
        except Exception as e:
            error_message = f"Error updating item: {e}"
            logger.exception(error_message)
            return {
                'status': False,
                'message': error_message,
                'output': [],
                'error': error_message
            }

    def update_item_with_dict_payload(self, update_key, data, condition_expression):
        """
        Update specific attributes of a record in DynamoDB.

        This function updates specific attributes of a record in DynamoDB using the provided key, data, and condition expression.
        It constructs the update expression and expression attribute values from the data dictionary.
        It logs the success or failure of the operation and returns a dictionary with the status and message.

        Args:
            update_key (dict): A dictionary representing the key of the item to update.
            data (dict): A dictionary containing the fields to update and their corresponding new values.
            condition_expression (str): The condition expression for conditional updates.

        Returns:
            dict: A dictionary indicating the success or failure of the operation.
        """
        try:
            update_expression = "SET " + \
                ", ".join([f"{k} = :{k}" for k in data.keys()])
            expression_attribute_values = {
                f":{k}": v for k, v in data.items()
            }
            result = self.update_item(
                update_key, update_expression, expression_attribute_values, condition_expression)

            if result['status']:
                return {
                    "status": True,
                    "message": result['message']
                }
            else:
                return {
                    "status": False,
                    "message": result['message']
                }
        except Exception as e:
            return {
                "status": False,
                "message": str(e)
            }
