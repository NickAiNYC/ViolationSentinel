#!/bin/bash

echo "🚀 Starting ViolationSentinel API Server..."
echo "💰 Monetization Ready: $297/month per customer"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.8+"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary files
if [ ! -f "users.json" ]; then
    echo "📁 Creating users.json..."
    echo "{}" > users.json
fi

if [ ! -f "api_keys.json" ]; then
    echo "📁 Creating api_keys.json..."
    echo "{}" > api_keys.json
fi

# Start the server
echo ""
echo "✅ Setup complete!"
echo "🌐 API Server starting on http://localhost:8000"
echo "📚 API Documentation: http://localhost:8000/docs"
echo "💻 To stop server: Ctrl+C"
echo ""
echo "🎯 Next steps:"
echo "1. Open landing_page.html in browser"
echo "2. Send outreach emails to real estate investors"
echo "3. Process manual payments via PayPal/Venmo"
echo "4. Create API keys for paying customers"
echo ""

uvicorn simple_api:app --reload --host 0.0.0.0 --port 8000
END && chmod +x start_api.sh