# ViolationSentinel Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Option 1: Docker Compose (Recommended)

**Prerequisites**: Docker & Docker Compose installed

```bash
# 1. Clone the repository
git clone https://github.com/NickAiNYC/ViolationSentinel.git
cd ViolationSentinel

# 2. Set up environment
cp .env.example .env
# Edit .env - at minimum, add your NYC_APP_TOKEN

# 3. Start all services
docker-compose up -d

# 4. Initialize database
docker-compose exec api alembic upgrade head

# 5. Access the API
open http://localhost:8000/docs
```

**That's it!** Your enterprise PropTech platform is running.

### Option 2: Manual Setup

**Prerequisites**: Python 3.11+, PostgreSQL 15, Redis 7

```bash
# 1. Clone and setup
git clone https://github.com/NickAiNYC/ViolationSentinel.git
cd ViolationSentinel

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Start PostgreSQL & Redis (with Docker)
docker run -d -p 5432:5432 \
  -e POSTGRES_DB=violation_sentinel \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  --name vs_postgres \
  postgres:15-alpine

docker run -d -p 6379:6379 \
  --name vs_redis \
  redis:7-alpine

# 5. Set up environment
cp .env.example .env
# Edit .env with your settings

# 6. Run migrations
alembic upgrade head

# 7. Start the API
./scripts/start_api.sh
# Or: uvicorn backend.api.main:app --reload

# 8. In separate terminals:
# Start Celery worker
celery -A backend.tasks.celery_app worker --loglevel=info

# Start Celery beat
celery -A backend.tasks.celery_app beat --loglevel=info
```

## 🔍 Verify Installation

```bash
# Run verification script
./scripts/verify_setup.sh

# Check health
curl http://localhost:8000/health

# Check detailed health (requires DB)
curl http://localhost:8000/health/detailed
```

## 📚 Next Steps

### 1. Explore the API
Visit http://localhost:8000/docs for interactive API documentation

### 2. View Monitoring
- Celery Flower: http://localhost:5555
- Prometheus: http://localhost:9090

### 3. Create Your First Organization (via API)
```bash
curl -X POST http://localhost:8000/api/v1/organizations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Property Management",
    "slug": "my-pm",
    "subscription_tier": "PRO"
  }'
```

### 4. Add a Property
```bash
curl -X POST http://localhost:8000/api/v1/properties \
  -H "Content-Type: application/json" \
  -d '{
    "bbl": "1012650001",
    "address_line1": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip_code": "10001",
    "borough": "MANHATTAN",
    "organization_id": "<org-id-from-step-3>"
  }'
```

### 5. Get Risk Score
```bash
curl http://localhost:8000/api/v1/properties/<property-id>/risk-score
```

## 🎓 Learn More

- **Full Documentation**: [docs/README_ENTERPRISE.md](docs/README_ENTERPRISE.md)
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Deployment**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **API Reference**: http://localhost:8000/docs

## 🐛 Troubleshooting

### Database Connection Failed
```bash
# Check PostgreSQL is running
docker ps | grep postgres
# Or
pg_isready -h localhost -p 5432
```

### Redis Connection Failed
```bash
# Check Redis is running
docker ps | grep redis
# Or
redis-cli ping
```

### API Won't Start
```bash
# Check logs
docker-compose logs api
# Or check if port 8000 is in use
lsof -i :8000
```

### Celery Not Processing Tasks
```bash
# Check worker status
celery -A backend.tasks.celery_app inspect active
# Check logs
docker-compose logs celery_worker
```

## 💡 Tips

1. **Get NYC Open Data Token**: Visit https://data.cityofnewyork.us/profile/app_tokens
2. **Use Docker for Development**: Easier setup and consistent environment
3. **Check Health Endpoints**: Use `/health/detailed` to debug connectivity issues
4. **Read the Logs**: Structured JSON logs make debugging easier
5. **Run Tests**: `pytest backend/tests/ -v` to verify everything works

## 🤝 Need Help?

- **Documentation**: Check docs/ directory
- **Issues**: https://github.com/NickAiNYC/ViolationSentinel/issues
- **API Docs**: http://localhost:8000/docs (interactive!)

## 🎯 What You Have Now

✅ **Production-ready backend** with FastAPI  
✅ **PostgreSQL database** with enterprise models  
✅ **Redis caching** for performance  
✅ **Celery workers** for async processing  
✅ **Docker setup** for easy deployment  
✅ **Health checks** for monitoring  
✅ **API documentation** with Swagger  
✅ **Test suite** for quality assurance  
✅ **Prometheus metrics** for observability  

## 🚀 Next: Build Your Features

The platform is ready for you to:
- Implement full authentication (OAuth2/JWT)
- Complete data ingestion from NYC Open Data
- Train ML models for risk scoring
- Build React frontend
- Add more endpoints as needed
- Scale to production

**Happy coding!** 🎉
