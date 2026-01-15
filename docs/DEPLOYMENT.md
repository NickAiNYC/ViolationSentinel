# ViolationSentinel Deployment Guide

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- PostgreSQL 15
- Redis 7

## Quick Start (Development)

### 1. Clone Repository
```bash
git clone https://github.com/NickAiNYC/ViolationSentinel.git
cd ViolationSentinel
```

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start with Docker Compose
```bash
docker-compose up -d
```

This will start:
- PostgreSQL database (port 5432)
- Redis (port 6379)
- FastAPI backend (port 8000)
- Celery workers
- Celery beat scheduler
- Flower monitoring (port 5555)
- Prometheus (port 9090)

### 4. Initialize Database
```bash
docker-compose exec api alembic upgrade head
```

### 5. Access Services
- API Documentation: http://localhost:8000/docs
- API Health Check: http://localhost:8000/health
- Celery Flower: http://localhost:5555
- Prometheus: http://localhost:9090

## Manual Setup (without Docker)

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Start PostgreSQL and Redis
```bash
# PostgreSQL
docker run -d -p 5432:5432 \
  -e POSTGRES_DB=violation_sentinel \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  postgres:15-alpine

# Redis
docker run -d -p 6379:6379 redis:7-alpine
```

### 3. Run Migrations
```bash
alembic upgrade head
```

### 4. Start API Server
```bash
./scripts/start_api.sh
# Or manually:
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Start Celery Worker (in separate terminal)
```bash
celery -A backend.tasks.celery_app worker --loglevel=info
```

### 6. Start Celery Beat (in separate terminal)
```bash
celery -A backend.tasks.celery_app beat --loglevel=info
```

## Production Deployment

### AWS ECS

1. **Build and push Docker image:**
```bash
docker build -t violation-sentinel:latest .
docker tag violation-sentinel:latest <ECR_REPOSITORY>:latest
docker push <ECR_REPOSITORY>:latest
```

2. **Create ECS Task Definition:**
- Use `docker-compose.yml` as reference
- Set environment variables via AWS Systems Manager Parameter Store
- Configure CloudWatch logs

3. **Deploy services:**
- API service (with load balancer)
- Celery worker service
- Celery beat service (single task)

### Database Migration

```bash
# In production, run migrations before deploying new code
alembic upgrade head
```

### Health Checks

- Liveness: `GET /liveness`
- Readiness: `GET /readiness`
- Detailed: `GET /health/detailed`

## Environment Variables

Key environment variables (see `.env.example` for full list):

```bash
# Application
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<strong-secret-key>

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Redis
REDIS_URL=redis://host:6379/0

# NYC Open Data
NYC_APP_TOKEN=<your-token>

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_USER=apikey
SMTP_PASSWORD=<sendgrid-api-key>
```

## Monitoring

### Prometheus Metrics
- Endpoint: `http://localhost:8000/metrics`
- Grafana dashboard: Import from `monitoring/grafana/`

### Celery Monitoring
- Flower UI: `http://localhost:5555`

### Logs
- Structured JSON logs
- Configure log aggregation (e.g., CloudWatch, ELK)

## Backup & Recovery

### Database Backup
```bash
pg_dump violation_sentinel > backup.sql
```

### Restore
```bash
psql violation_sentinel < backup.sql
```

## Scaling

- **API**: Horizontal scaling behind load balancer
- **Celery Workers**: Scale based on queue depth
- **Database**: Use read replicas for heavy read workloads
- **Redis**: Use Redis Cluster for high availability

## Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up VPC (AWS)
- [ ] Enable database encryption at rest
- [ ] Rotate API keys regularly
- [ ] Enable audit logging
- [ ] Configure rate limiting
- [ ] Set up DDoS protection
- [ ] Regular security updates

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker-compose ps postgres
# Check logs
docker-compose logs postgres
```

### Celery Not Processing Tasks
```bash
# Check worker status
celery -A backend.tasks.celery_app inspect active
# Check queue
celery -A backend.tasks.celery_app inspect active_queues
```

### API Errors
```bash
# Check API logs
docker-compose logs api
# Check health endpoint
curl http://localhost:8000/health/detailed
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/NickAiNYC/ViolationSentinel/issues
- Documentation: http://localhost:8000/docs
