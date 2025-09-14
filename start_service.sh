#!/usr/bin/env bash
# Provide the permissions to execute the script
# chmod +x start_service.sh
set -euo pipefail

# make sure a local logs/ directory exists
mkdir -p ./logs

echo "Starting app service on port 8005..."
nohup gunicorn app:app \
     --workers 2 \
     --worker-class uvicorn.workers.UvicornWorker \
     --reload \
     --timeout 7200 \
     --bind 0.0.0.0:8005 \
     > logs/app.log 2>&1 &

echo "App service started."
