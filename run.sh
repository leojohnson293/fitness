#!/bin/bash
# Usage:
#   ./run.sh       → starts dev (default)
#   ./run.sh dev   → starts dev  (port 8001, fitness_dev db)
#   ./run.sh prod  → starts prod (port 8000, fitness db)

ENV=${1:-dev}
ENV_FILE=".env.$ENV"

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Environment file '$ENV_FILE' not found."
  exit 1
fi

# Load env vars
export $(grep -v '^#' "$ENV_FILE" | xargs)

echo "🚀 Starting [$ENV] on port $PORT → db: $DATABASE_URL"
cd fitness_app
uvicorn main:app --host 0.0.0.0 --port "$PORT" --reload
