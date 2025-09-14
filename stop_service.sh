#!/usr/bin/env bash
# Provide the permissions to execute the script
# chmod +x stop_service.sh
set -euo pipefail

# Kill any process listening on TCP port $1 (SIGTERM only)
stop_service() {
  local port=$1
  local pids
  pids=$(lsof -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)

  if [[ -z "$pids" ]]; then
    echo "No process found listening on port $port."
  else
    echo "Killing process(es) $pids listening on port $port..."
    kill $pids
    echo "Sent SIGTERM to $pids."
  fi
}

echo "Stopping Twilio outbound call service on port 8007..."
stop_service 8007

echo "Twilio outbound call service stopped."