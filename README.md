# Notion Voice CoPilot - Lambda Service

This AWS Lambda service acts as the central component of the **Notion Voice CoPilot** system.
It manages Notion webpages by processing and updating user conversations directly into Notion workspaces.

## 📁 Directory Structure

```
lambda/
├── lambda_policy_template.json     # IAM policy template defining Lambda roles
├── requirements.txt                # Python dependencies
├── lambda_config.txt               # Lambda configuration settings
├── .env                            # Environment variables
├── code/                           # Core Lambda codebase
│   └── lambda_function.py          # Main Lambda function logic
│   ├── setup_loader.py             # Configuration loader
│   ├── config/                     # Configuration files
│   │   └── app_config.yaml         # Main application configuration
│   └── modules/                    # Supporting modules
│      ├── AIManager.py             # Handles AI prompt calls
│      ├── DynamoDBManager.py       # AWS DynamoDB interface
│      ├── NotionManager.py         # Notion API integration
│      └── UltravoxAIManager.py     # Ultravox AI service integration
```

## Setup & Installation

### Prerequisites

1. **Create the Lambda Function** in AWS.
2. **Build the Lambda Layer** using the dependencies listed in `requirements.txt`.
3. **Package and upload the codebase** as a `.zip` file to your Lambda function.
4. **Create an IAM policy** using `lambda_policy_template.json` and attach it to the Lambda role.
5. **Configure environment variables** using the `.env` file (see below).
6. **Set the function metadata** — description, memory, and runtime — as per `lambda_config.txt`.

---

## 🔑 Environment Variables

Create then lambda env section with the following variables (all of these are referenced in `app_config.yaml`):

```
# AWS Configuration
AWS_REGION=<your-aws-region>
CALL_RECORDS_TABLE=<dynamodb-call-records-table-name>

# Azure Configuration
AZURE_API_VERSION=<azure-api-version>
AZURE_ACCESS_KEY=<azure-access-key>
AZURE_API_BASE=<azure-api-base-url>
AZURE_MODEL_ID=<azure-openai-model-id>

# Ultravox Configuration
ULTROVOX_API_KEY=<ultravox-api-key>
ULTROVOX_BASE_URL=<ultravox-base-url>

# Twilio Configuration
TWILIO_ACCOUNT_SID=<twilio-sid>
TWILIO_AUTH_TOKEN=<twilio-token>

# Notion Configuration
NOTION_API_TOKEN=<notion-api-key>
NOTION_JOURNAL_PAGE_ID=<notion-journal-page-id>
NOTION_TODO_PAGE_ID=<notion-todo-page-id>
```
