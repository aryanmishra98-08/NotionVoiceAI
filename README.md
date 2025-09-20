# Notion Voice CoPilot - App Service

The App Service is a FastAPI-based application that serves as the central component of the Notion Voice CoPilot system. It handles authentication, call management, and interfaces with various services to enable voice control of Notion workspaces.

## Directory Structure

```
app/
├── app.py                              # Main application entry point
├── requirements.txt                    # Python dependencies
├── setup_loader.py                     # Configuration loader
├── start_service.sh                    # Service start script
├── stop_service.sh                     # Service stop script
├── config/                             # Configuration files folder
│   └── app_config.yaml                 # Main app configuration
├── keys/                               # Authentication keys and .env folder
│   ├── .env                            # Environment variables
│   ├── private_key.pem                 # Private key for JWT
│   └── public_key.pem                  # Public key for JWT
├── logs/                               # Application logs folder
└── modules/                            # Application modules folder
    ├── api_modules/                    # API functionality modules folder
    │   ├── AuthHandlingComponent.py    # Authentication logic implementation
    │   └── CallHandlingComponent.py    # Call management implementation
    ├── api_routes/                     # API route definitions folder
    │   ├── APIResponse.py              # Standard API response formats
    │   ├── APISchemaComponent.py       # API schema definitions
    │   ├── AuthHandlingRoutes.py       # Authentication endpoints
    │   └── CallHandlingRoutes.py       # Call management endpoints
    └── service_modules/                # Service integration modules folder
        ├── DynamoDBManager.py          # AWS DynamoDB interface
        ├── JWTAuthentication.py        # JWT token management
        └── UltravoxAIManager.py        # Ultravox AI service integration
```

## Setup & Installation

### Prerequisites

- Python 3.11 or later
- AWS Account with appropriate permissions and resources created
- Ultravox Account

### Installation Steps

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables:
   - Ensure the `.env` file in the `keys/` directory contains all required variables (see below)

3. Configure application settings:
   - Review and update `config/app_config.yaml` as needed

### Required Environment Variables

Create or update the `.env` file in the `keys/` directory with the following variables (all of these are referenced in `app_config.yaml`):

```
# App Configuration
VOICE_AI_APP_URL=<your-voice-app-service-url>

# AWS Configuration
AWS_REGION=<your-aws-region>
CALL_RECORDS_TABLE=<dynamodb-call-records-table-name>
SERVICE_ACCOUNT_RECORDS_TABLE=<dynamodb-service-account-table-name>
CALL_TERMINATION_LAMBDA=<lambda-function-name-for-call-termination>

# Azure Configuration
AZURE_API_VERSION=<azure-api-version>
AZURE_ACCESS_KEY=<azure-access-key>
AZURE_API_BASE=<azure-api-base-url>
AZURE_MODEL_ID=<azure-openai-model-id>

# Ultravox Configuration
ULTROVOX_API_KEY=<ultravox-api-key>
ULTROVOX_BASE_URL=<ultravox-base-url>
ULTROVOX_TO_DO_LIST_AGENT_ID=<ultravox-to-do-list-agent-id>
ULTROVOX_JOURNALING_AGENT_ID=<ultravox-journaling-agent-id>

# JWT Authentication
JWT_AUTHENTICATION_ALGORITHM=<jwt-algorithm> # Typically "HS256" or "RS256"
JWT_AUTHENTICATION_ACCESS_TOKEN_EXPIRE_MINUTES=<token-expiry-in-minutes>
# These should point to key files in the keys folder
JWT_AUTHENTICATION_PRIVATE_KEY_SERV_ACC_CALL_ID_PATH=<path-to-private-key-in-keys-folder>
JWT_AUTHENTICATION_PUBLIC_KEY_SERV_ACC_CALL_ID_PATH=<path-to-public-key-in-keys-folder>

# Encryption Configuration
ENCRYPTION_KEY=<encryption-key>
DECRYPTION_PASSWORD_PLACEHOLDER=<password-placeholder>
DECRYPTION_SALT_PLACEHOLDER=<salt-placeholder>
```

## Running the Service

### Starting the Service

```bash
./start_service.sh
```

This script will start the application using the configuration defined in the script.

### Stopping the Service

```bash
./stop_service.sh
```
