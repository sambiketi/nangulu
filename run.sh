#!/bin/bash
set -e

# Load environment
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
