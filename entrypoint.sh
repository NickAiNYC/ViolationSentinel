#!/bin/bash

echo "Starting ViolationSentinel Services..."

# Start FastAPI Backend
echo "Starting FastAPI backend on port 8000..."
uvicorn simple_api:app --host 0.0.0.0 --port 8000 --log-level info &
FASTAPI_PID=$!
echo "FastAPI started with PID: $FASTAPI_PID"

# Start Streamlit Dashboard
echo "Starting Streamlit dashboard on port 8501..."
streamlit run landlord_dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false &
STREAMLIT_PID=$!
echo "Streamlit started with PID: $STREAMLIT_PID"

echo "Both services running. Monitoring for failures..."

# Wait for any background process to exit
wait -n
EXIT_CODE=$?

# Determine which process exited
if ! kill -0 $FASTAPI_PID 2>/dev/null; then
    echo "ERROR: FastAPI backend exited unexpectedly"
elif ! kill -0 $STREAMLIT_PID 2>/dev/null; then
    echo "ERROR: Streamlit dashboard exited unexpectedly"
fi

# Exit with status of the first process that exited
exit $EXIT_CODE
