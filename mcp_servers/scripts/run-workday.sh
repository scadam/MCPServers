#!/usr/bin/env bash

set -euo pipefail

ENV_FILE=${1:-../env/workday.local.env}

if [[ -f "$ENV_FILE" ]]; then
  echo "Loading environment from $ENV_FILE"
  export $(grep -v '^#' "$ENV_FILE" | xargs -d '\n')
else
  echo "Warning: environment file not found at $ENV_FILE" >&2
fi

python -m mcp_servers.cli workday --transport http --host 0.0.0.0 --port 8080
