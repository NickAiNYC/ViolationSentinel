#!/bin/bash
# Quick verification script for ViolationSentinel setup

set -e

echo "🔍 ViolationSentinel - System Verification"
echo "=========================================="

# Check Python version
echo ""
echo "📍 Checking Python version..."
python3 --version

# Check if in repo
if [ ! -f "backend/config.py" ]; then
    echo "❌ Not in ViolationSentinel root directory"
    exit 1
fi
echo "✅ In correct directory"

# Check Docker
echo ""
echo "🐳 Checking Docker..."
if command -v docker &> /dev/null; then
    docker --version
    echo "✅ Docker available"
else
    echo "⚠️  Docker not found - needed for production deployment"
fi

# Check structure
echo ""
echo "📁 Checking project structure..."
required_dirs=(
    "backend/api"
    "backend/data_models"
    "backend/data_ingestion"
    "backend/risk_scoring"
    "backend/alerts"
    "backend/tasks"
    "backend/tests"
    "alembic"
    "docs"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir"
    else
        echo "  ❌ $dir missing"
    fi
done

# Check key files
echo ""
echo "📄 Checking key files..."
key_files=(
    "backend/config.py"
    "backend/api/main.py"
    "docker-compose.yml"
    "Dockerfile"
    "alembic.ini"
)

for file in "${key_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file missing"
    fi
done

echo ""
echo "=========================================="
echo "✅ Verification complete!"
echo ""
echo "📚 Next steps:"
echo "  1. Install dependencies: pip install -r backend/requirements.txt"
echo "  2. Configure .env: cp .env.example .env"
echo "  3. Start services: docker-compose up -d"
echo "  4. Initialize DB: docker-compose exec api alembic upgrade head"
echo "  5. Visit: http://localhost:8000/docs"
echo "=========================================="
