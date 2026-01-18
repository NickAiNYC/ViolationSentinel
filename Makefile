# ViolationSentinel Enterprise Makefile
# Development, Testing, and Deployment Automation

.PHONY: help dev dev-down test test-cov lint lint-fix format build push deploy deploy-staging deploy-prod clean install docker-build docker-run monitoring logs shell db-migrate db-upgrade health

# Default target
help:
	@echo "ViolationSentinel Enterprise Commands"
	@echo "======================================"
	@echo ""
	@echo "Development:"
	@echo "  make dev              - Start all services with docker-compose"
	@echo "  make dev-down         - Stop all services"
	@echo "  make install          - Install Python dependencies"
	@echo "  make shell            - Open shell in API container"
	@echo "  make logs             - View container logs"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - Run pytest test suite"
	@echo "  make test-cov         - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             - Run ruff and black checks"
	@echo "  make lint-fix         - Auto-fix linting issues"
	@echo "  make format           - Format code with black and isort"
	@echo ""
	@echo "Docker:"
	@echo "  make build            - Build Docker images"
	@echo "  make docker-build     - Build API Docker image"
	@echo "  make docker-run       - Run API container locally"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy           - Deploy to Kubernetes (kubectl apply)"
	@echo "  make deploy-staging   - Deploy to staging environment"
	@echo "  make deploy-prod      - Deploy to production environment"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate       - Create new migration"
	@echo "  make db-upgrade       - Apply migrations"
	@echo ""
	@echo "Monitoring:"
	@echo "  make monitoring       - Start monitoring stack (Prometheus/Grafana)"
	@echo "  make health           - Check service health endpoints"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            - Remove cache and temp files"

# ============================================================================
# Development
# ============================================================================

dev:
	docker-compose up -d

dev-down:
	docker-compose down

install:
	pip install -r requirements.txt

shell:
	docker-compose exec api /bin/bash

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

# ============================================================================
# Testing
# ============================================================================

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=backend --cov=api --cov=risk_engine --cov-report=term-missing --cov-report=html --cov-report=xml

test-unit:
	pytest tests/ -v -m "not integration"

test-integration:
	pytest tests/ -v -m "integration"

test-fast:
	pytest tests/ -v -x --tb=short

# ============================================================================
# Code Quality
# ============================================================================

lint:
	ruff check .
	black --check .

lint-fix:
	ruff check . --fix
	black .

format:
	black .
	isort .

type-check:
	mypy backend/ api/ risk_engine/ --ignore-missing-imports

# ============================================================================
# Docker
# ============================================================================

build:
	docker-compose build

docker-build:
	docker build -t violationsentinel-api:latest -f backend/Dockerfile ./backend

docker-run:
	docker run -p 8000:8000 --env-file .env violationsentinel-api:latest

docker-push:
	docker push ghcr.io/nickaicc/violationsentinel-api:latest

# ============================================================================
# Deployment
# ============================================================================

deploy:
	kubectl apply -f k8s/

deploy-staging:
	kubectl apply -f k8s/overlays/staging/

deploy-prod:
	kubectl apply -f k8s/overlays/production/

rollback:
	kubectl rollout undo deployment/violationsentinel-api

# ============================================================================
# Database
# ============================================================================

db-migrate:
	alembic revision --autogenerate -m "$(msg)"

db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

db-reset:
	docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS violationsentinel; CREATE DATABASE violationsentinel;"

# ============================================================================
# Monitoring
# ============================================================================

monitoring:
	docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d prometheus grafana

monitoring-down:
	docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml down

health:
	@echo "Checking health endpoints..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "API not responding"
	@curl -s http://localhost:8000/ready | python -m json.tool || echo "API not ready"

# ============================================================================
# Security
# ============================================================================

security-scan:
	trivy fs --severity HIGH,CRITICAL .

dependency-check:
	pip-audit

# ============================================================================
# Cleanup
# ============================================================================

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

clean-docker:
	docker-compose down -v --rmi local

# ============================================================================
# Utilities
# ============================================================================

api-docs:
	@echo "API Documentation: http://localhost:8000/api/v1/docs"
	@xdg-open http://localhost:8000/api/v1/docs 2>/dev/null || open http://localhost:8000/api/v1/docs 2>/dev/null || echo "Open http://localhost:8000/api/v1/docs in your browser"

grafana:
	@echo "Grafana Dashboard: http://localhost:3001 (admin/admin)"
	@xdg-open http://localhost:3001 2>/dev/null || open http://localhost:3001 2>/dev/null || echo "Open http://localhost:3001 in your browser"

prometheus:
	@echo "Prometheus: http://localhost:9090"
	@xdg-open http://localhost:9090 2>/dev/null || open http://localhost:9090 2>/dev/null || echo "Open http://localhost:9090 in your browser"

rabbitmq:
	@echo "RabbitMQ Management: http://localhost:15672 (admin/admin)"
	@xdg-open http://localhost:15672 2>/dev/null || open http://localhost:15672 2>/dev/null || echo "Open http://localhost:15672 in your browser"
