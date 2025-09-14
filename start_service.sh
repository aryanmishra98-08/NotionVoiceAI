#!/usr/bin/env bash
# Provide the permissions to execute the script
# chmod +x start_service.sh
set -euo pipefail

# make sure a local logs/ directory exists
mkdir -p ./logs

echo "Starting Twilio outbound call service on port 8007..."
nohup gunicorn outbound_ivr:app \
     --workers 2 \
     --worker-class uvicorn.workers.UvicornWorker \
     --reload \
     --timeout 7200 \
     --bind 0.0.0.0:8007 \
     > ./logs/outbound_ivr.log 2>&1 &

echo "Twilio outbound call service started."
