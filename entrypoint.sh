#!/bin/bash

# Start FastAPI Backend
uvicorn simple_api:app --host 0.0.0.0 --port 8000 &

# Start Streamlit Dashboard
streamlit run landlord_dashboard.py --server.port 8501 --server.address 0.0.0.0 &

# Wait for any background process to exit
wait -n

# Exit with status of the first process that exited
exit $?
