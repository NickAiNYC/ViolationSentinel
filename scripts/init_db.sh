#!/bin/bash
# Initialize Database Script

set -e

echo "🚀 ViolationSentinel - Database Initialization"
echo "================================================"

# Check if PostgreSQL is running
echo "📊 Checking PostgreSQL connection..."
python3 -c "
import sys
sys.path.insert(0, '.')
from backend.config import settings
import psycopg2
try:
    conn = psycopg2.connect(settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://'))
    conn.close()
    print('✅ PostgreSQL connection successful')
except Exception as e:
    print(f'❌ PostgreSQL connection failed: {e}')
    print('💡 Make sure PostgreSQL is running: docker-compose up -d postgres')
    sys.exit(1)
"

# Run migrations
echo ""
echo "🔄 Running Alembic migrations..."
cd /home/runner/work/ViolationSentinel/ViolationSentinel
alembic upgrade head

echo ""
echo "✅ Database initialization complete!"
echo "================================================"
