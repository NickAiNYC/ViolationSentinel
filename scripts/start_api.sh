#!/bin/bash
# Start ViolationSentinel API

set -e

echo "🚀 Starting ViolationSentinel API"
echo "================================================"

# Navigate to project root (one level up from scripts/)
cd "$(dirname "$0")/.."

# Check if virtual environment should be activated
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start Uvicorn
echo "📡 Starting API server on http://0.0.0.0:8000"
echo "📄 API Documentation: http://localhost:8000/docs"
echo "================================================"

uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
