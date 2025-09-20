# Notion Voice CoPilot - Outbound IVR Service

The Outbound IVR Service is responsible for handling outgoing calls in the Notion Voice CoPilot system. It manages the Interactive Voice Response (IVR) functionality, call initiation, scheduling, and integration with the main application service.

## Directory Structure

```
outbound/
├── outbound_ivr.py                    # Main outbound IVR entry point
├── requirements.txt                   # Python dependencies
├── setup_loader_ivr.py                # Configuration loader for IVR
├── start_service.sh                   # Service start script
├── stop_service.sh                    # Service stop script
├── config/                            # Configuration files folder
│   └── ivr_config.yaml                # Main IVR configuration
├── keys/                              # Authentication keys and .env folder
│   ├── .env                           # Environment variables
│   ├── private_key.pem                # Private key for JWT
│   └── public_key.pem                 # Public key for JWT
├── logs/                              # Application logs folder
└── modules/                           # IVR modules folder
    ├── routes.py                      # API route definitions
    └── telephony.py                   # Telephony service integration
```

## Setup & Installation

### Prerequisites

- Python 3.11 or later
- AWS Account with appropriate permissions and resources created
- Twilio account

### Installation Steps

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables:
   - Ensure the `.env` file in the `keys/` directory contains all required variables (see below)

3. Configure IVR settings:
   - Review and update `config/ivr_config.yaml` as needed

### Required Environment Variables

Create or update the `.env` file in the `keys/` directory with the following variables (all of these are referenced in `ivr_config.yaml`):

```
# App Configuration
CCAAS_APP_OUTBOUND_URL=<your-outbound-ivr-service-url>

# Voice AI App Configuration
VOICE_AI_APP_URL=<your-voice-app-service-url>
CCAAS_USERNAME=<your-voice-app-username>
CCAAS_PASSWORD=<your-voice-app-password>

# Twilio Configuration
TWILIO_AUTH_TOKEN=<auth-token-from-twilio>
TWILIO_ACCOUNT_SID=<account-sid-from-twilio>
TWILIO_TO_NUMBER=<default-recipient-phone-number>
TWILIO_FROM_NUMBER=<twilio-phone-number>
TWILIO_ERROR_VOICE_URL=<function-url-form-twilio>
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
