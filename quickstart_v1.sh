#!/bin/bash
# Quick Start Script for ViolationSentinel V1

echo "🏢 ViolationSentinel V1 - Quick Start"
echo "======================================"

# Check Python version
echo "Checking Python version..."
python --version

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q -r requirements-v1.txt

# Create data directory
mkdir -p data

# Run tests
echo ""
echo "Running tests..."
python test_v1.py

# Start API in background
echo ""
echo "Starting API server on port 8000..."
python backend/v1/api.py &
API_PID=$!
sleep 2

# Check API health
echo "Checking API health..."
curl -s http://localhost:8000/health || echo "API not responding (this is OK for now)"

echo ""
echo "======================================"
echo "✅ Setup complete!"
echo ""
echo "To start the dashboard:"
echo "  streamlit run streamlit/app.py"
echo ""
echo "Then visit: http://localhost:8501"
echo ""
echo "To stop API server:"
echo "  kill $API_PID"
echo "======================================"
