# 🏢 ViolationSentinel - Enterprise PropTech Platform

> Transform fragmented building violation data into predictive compliance and financial risk intelligence

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)

## 🎯 Overview

ViolationSentinel is an enterprise-grade PropTech compliance and risk intelligence platform designed for property managers, landlords, insurers, lenders, and PropTech platforms. It transforms NYC building violations data into actionable insights with ML-powered risk forecasting.

### Key Features

- **🏗️ Multi-Source Data Ingestion**: DOB, HPD, 311 complaints
- **🤖 ML-Powered Risk Scoring**: XGBoost & scikit-learn models
- **📊 Real-Time Dashboards**: React + TypeScript frontend
- **🔔 Smart Alerts**: Multi-channel notifications (Email, SMS, Slack, Webhooks)
- **🔐 Enterprise Security**: OAuth2, JWT, RBAC, API keys
- **📈 Scalable Architecture**: Docker, Celery, Redis, PostgreSQL
- **🎯 Multi-Tenant**: Full organization isolation
- **📡 REST API**: OpenAPI/Swagger documentation

## 🏗️ Architecture

```
┌─────────────────┐
│   React + TS    │  Frontend (Vite + TailwindCSS)
└────────┬────────┘
         │
┌────────▼────────┐
│    FastAPI      │  API Layer (Python 3.11)
└────────┬────────┘
         │
┌────────▼────────┬─────────────┬──────────────┐
│   PostgreSQL    │    Redis    │    Celery    │
│   (SQLAlchemy)  │  (Caching)  │  (Tasks)     │
└─────────────────┴─────────────┴──────────────┘
         │
┌────────▼────────────────────────────────────┐
│         NYC Open Data APIs                  │
│    (DOB, HPD, 311 via SOCRATA)            │
└─────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- PostgreSQL 15
- Redis 7

### 1. Clone & Setup

```bash
git clone https://github.com/NickAiNYC/ViolationSentinel.git
cd ViolationSentinel

# Copy environment template
cp .env.example .env
# Edit .env with your NYC Open Data token and other settings
```

### 2. Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# Initialize database
docker-compose exec api alembic upgrade head

# Check health
curl http://localhost:8000/health
```

### 3. Access Services

- **API Docs**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health
- **Celery Monitor**: http://localhost:5555
- **Prometheus**: http://localhost:9090

## 📦 Project Structure

```
ViolationSentinel/
├── backend/
│   ├── api/                    # FastAPI application
│   │   ├── main.py            # App entry point
│   │   └── routes/            # API endpoints
│   ├── data_models/           # SQLAlchemy models
│   │   ├── property.py        # Property entity
│   │   ├── violation.py       # Violation records
│   │   ├── risk_score.py      # Risk assessments
│   │   ├── alert.py           # Alert system
│   │   └── user.py            # Auth & RBAC
│   ├── data_ingestion/        # NYC Open Data ingestion
│   ├── normalization/         # Data cleaning & dedup
│   ├── risk_scoring/          # Risk engine
│   ├── ml/                    # ML models
│   ├── auth/                  # Authentication
│   ├── alerts/                # Alert system
│   ├── tasks/                 # Celery async tasks
│   └── monitoring/            # Metrics & observability
├── frontend/                  # React application
├── alembic/                   # Database migrations
├── tests/                     # Test suite
├── docs/                      # Documentation
├── monitoring/                # Prometheus config
├── docker-compose.yml         # Local development
├── Dockerfile                 # Production image
└── README.md
```

## 🔧 Development

### Local Setup (without Docker)

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Start PostgreSQL & Redis (with Docker)
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine

# Run migrations
alembic upgrade head

# Start API
./scripts/start_api.sh

# In separate terminals:
# Start Celery worker
celery -A backend.tasks.celery_app worker --loglevel=info

# Start Celery beat
celery -A backend.tasks.celery_app beat --loglevel=info
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## 📊 Data Models

### Core Entities

- **Property**: NYC properties with normalized addresses, BBL, BIN, geolocation
- **Violation**: DOB, HPD, 311 violations with severity classification
- **RiskScore**: ML-computed risk assessments with sub-scores
- **Alert**: Triggered alerts with multi-channel notifications
- **User/Organization**: Multi-tenant auth with RBAC

### Risk Scoring

```python
RiskScore = {
    "overall_score": 0-100,      # Composite risk
    "safety_score": 0-100,       # Safety violations
    "legal_score": 0-100,        # Legal compliance
    "financial_score": 0-100,    # Financial impact
    "trend_direction": "IMPROVING|STABLE|WORSENING",
    "confidence": 0.0-1.0,
    "forecast_30d": 0-100,       # 30-day forecast
}
```

## 🔐 Authentication

### API Keys

```bash
# Create API key (via API)
POST /api/v1/organizations/{org_id}/api-keys
{
  "name": "Production API Key",
  "scopes": ["read:properties", "read:violations", "read:risk_scores"]
}

# Use API key
curl -H "X-API-Key: vs_xxx..." http://localhost:8000/api/v1/properties
```

### JWT Tokens

```bash
# Login
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "secure_password"
}

# Use token
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/properties
```

## 🎯 API Examples

### Get Property Risk Score

```bash
GET /api/v1/properties/{property_id}/risk-score

Response:
{
  "property_id": "uuid",
  "overall_score": 75.5,
  "safety_score": 80.0,
  "legal_score": 70.0,
  "financial_score": 76.5,
  "trend_direction": "WORSENING",
  "confidence": 0.85,
  "calculated_at": "2024-01-15T12:00:00Z"
}
```

### List High-Risk Properties

```bash
GET /api/v1/properties?min_risk_score=80&limit=10
```

### Create Alert Rule

```bash
POST /api/v1/alerts/rules
{
  "name": "High Risk Alert",
  "alert_type": "RISK_THRESHOLD",
  "threshold_value": 80,
  "threshold_operator": ">=",
  "channels": ["EMAIL", "SLACK"]
}
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test
pytest tests/test_risk_scoring.py -v
```

## 📈 Monitoring

### Prometheus Metrics

- Request duration histograms
- Error rates
- Database query performance
- Celery task metrics
- Custom business metrics

### Health Checks

- `/health` - Basic health check
- `/health/detailed` - Check all dependencies
- `/readiness` - Kubernetes readiness probe
- `/liveness` - Kubernetes liveness probe

## 🚢 Deployment

### Docker Compose (Production)

```bash
# Build
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### AWS ECS

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed AWS ECS deployment guide.

### Environment Variables

Key production settings:

```bash
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<strong-random-key>
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
NYC_APP_TOKEN=<nyc-open-data-token>
SMTP_HOST=smtp.sendgrid.net
SMTP_PASSWORD=<sendgrid-api-key>
```

## 🔒 Security

- OAuth2 + JWT authentication
- API key management with scopes
- RBAC (Admin, Manager, Viewer)
- Multi-tenant data isolation
- Audit logging
- Rate limiting
- HTTPS/TLS required in production
- SQL injection prevention (SQLAlchemy)
- XSS protection headers

## 📚 Documentation

- [API Documentation](http://localhost:8000/docs) - Interactive Swagger UI
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment
- [Architecture](docs/ARCHITECTURE.md) - System design
- [API Reference](docs/API.md) - Complete API reference

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- NYC Open Data for comprehensive violation databases
- PropTech community for workflow validation
- Property managers for real-world testing

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/NickAiNYC/ViolationSentinel/issues)
- **Email**: support@violationsentinel.com
- **Docs**: http://localhost:8000/docs

---

**Built for the PropTech industry** | **Enterprise-ready** | **Production-tested**
