# ViolationSentinel - Enterprise Deployment Guide

## Quick Start (30 Minutes to Production)

This guide will get ViolationSentinel running in production in 30 minutes.

---

## Prerequisites

### Required
- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Kubernetes** cluster (EKS, GKE, or AKS) with kubectl configured
- **Terraform** 1.0+ (for infrastructure)
- **PostgreSQL** 14+ (or use our managed deployment)
- **Redis** 7+ (or use our managed deployment)

### Optional (for full features)
- **AWS/Azure/GCP** account (for managed services)
- **Domain name** for production deployment
- **SSL certificate** (or use Let's Encrypt)

---

## Deployment Options

### Option 1: Local Development (5 minutes)

**Perfect for**: Development, testing, demos

```bash
# Clone repository
git clone https://github.com/NickAiNYC/ViolationSentinel.git
cd ViolationSentinel

# Start all services with Docker Compose
docker-compose up -d

# Verify services are running
docker-compose ps

# Access the application
# API: http://localhost:8000/api/v1/docs
# Frontend: http://localhost:3000
# Grafana: http://localhost:3001 (admin/admin)
```

**Services Started**:
- ✅ PostgreSQL with TimescaleDB
- ✅ Redis cache
- ✅ ElasticSearch
- ✅ RabbitMQ message broker
- ✅ FastAPI backend (with hot reload)
- ✅ Celery workers
- ✅ React frontend
- ✅ Prometheus + Grafana monitoring

---

### Option 2: Kubernetes Production (30 minutes)

**Perfect for**: Production deployments, high availability, auto-scaling

#### Step 1: Prepare Infrastructure with Terraform (10 minutes)

```bash
cd terraform/aws  # or terraform/azure or terraform/gcp

# Initialize Terraform
terraform init

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
aws_region = "us-east-1"
environment = "production"
db_username = "postgres"
db_password = "CHANGE_THIS_STRONG_PASSWORD"
EOF

# Plan infrastructure
terraform plan

# Apply infrastructure (creates EKS, RDS, ElastiCache, etc.)
terraform apply

# This creates:
# ✅ EKS Cluster (3-20 nodes)
# ✅ RDS PostgreSQL with TimescaleDB
# ✅ ElastiCache Redis (Multi-AZ)
# ✅ S3 buckets for storage
# ✅ CloudFront CDN
# ✅ VPC with public/private subnets
# ✅ Security groups and IAM roles

# Save outputs
terraform output > ../outputs.txt
```

#### Step 2: Configure Kubernetes (5 minutes)

```bash
# Get EKS cluster credentials
aws eks update-kubeconfig --region us-east-1 --name violationsentinel-production

# Verify connection
kubectl cluster-info

# Create namespaces
kubectl create namespace production
kubectl create namespace monitoring

# Create secrets
kubectl create secret generic violationsentinel-secrets \
  --from-literal=database-url="postgresql://user:pass@rds-endpoint:5432/violationsentinel" \
  --from-literal=redis-url="redis://elasticache-endpoint:6379/0" \
  --from-literal=secret-key="$(openssl rand -base64 32)" \
  -n production
```

#### Step 3: Deploy Application (10 minutes)

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/base/ -n production

# Wait for deployments to be ready
kubectl rollout status deployment/violationsentinel-api -n production
kubectl rollout status deployment/violationsentinel-celery-worker -n production

# Verify pods are running
kubectl get pods -n production

# Check services
kubectl get svc -n production

# Get load balancer endpoint
kubectl get ingress -n production
```

#### Step 4: Configure DNS and SSL (5 minutes)

```bash
# Get load balancer DNS name
LB_DNS=$(kubectl get ingress violationsentinel-ingress -n production -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Point your domain to the load balancer
# Example: api.violationsentinel.com -> $LB_DNS

# Install cert-manager for SSL (if not already installed)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create Let's Encrypt issuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@violationsentinel.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# SSL certificate will be automatically provisioned
```

#### Step 5: Verify Deployment

```bash
# Health check
curl https://api.violationsentinel.com/health

# API documentation
open https://api.violationsentinel.com/api/v1/docs

# Grafana dashboard
kubectl port-forward -n monitoring svc/grafana 3000:3000
open http://localhost:3000  # admin/admin
```

---

### Option 3: Single-Node Production (15 minutes)

**Perfect for**: Small deployments, cost optimization

```bash
# On your production server (Ubuntu 20.04+)

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Clone and configure
git clone https://github.com/NickAiNYC/ViolationSentinel.git
cd ViolationSentinel

# Create production environment file
cat > .env <<EOF
ENVIRONMENT=production
DATABASE_URL=postgresql://postgres:password@postgres:5432/violationsentinel
REDIS_URL=redis://redis:6379/0
SECRET_KEY=$(openssl rand -base64 32)
STRIPE_SECRET_KEY=your-stripe-key
SENTRY_DSN=your-sentry-dsn
EOF

# Start with production compose file
docker-compose -f docker-compose.prod.yml up -d

# Setup nginx reverse proxy
sudo apt install nginx certbot python3-certbot-nginx
sudo nano /etc/nginx/sites-available/violationsentinel

# Add this config:
server {
    server_name api.violationsentinel.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Enable site and get SSL
sudo ln -s /etc/nginx/sites-available/violationsentinel /etc/nginx/sites-enabled/
sudo certbot --nginx -d api.violationsentinel.com
sudo systemctl restart nginx
```

---

## Configuration

### Environment Variables

**Required**:
```bash
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
SECRET_KEY=random-secret-key-min-32-chars
TENANT_HEADER=X-Tenant-ID
```

**Optional but Recommended**:
```bash
# Authentication
ACCESS_TOKEN_EXPIRE_MINUTES=11520  # 8 days
ALGORITHM=HS256

# External APIs
NYC_OPEN_DATA_TOKEN=your-token-here

# Monitoring
SENTRY_DSN=https://sentry.io/your-project
PROMETHEUS_ENABLED=true

# Payment
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# Webhooks
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
TEAMS_WEBHOOK_URL=https://outlook.office.com/...

# Features
CACHE_TTL=3600
RATE_LIMIT=100
```

### Database Initialization

```bash
# Run migrations (automatic on startup)
python -m alembic upgrade head

# Or manually:
docker-compose exec api alembic upgrade head

# Create first tenant and user
docker-compose exec api python scripts/create_admin.py \
  --tenant-name "My Company" \
  --tenant-slug "mycompany" \
  --email "admin@mycompany.com" \
  --password "SecurePassword123!"
```

---

## Scaling

### Horizontal Pod Autoscaler (HPA)

**Automatically scale based on load**:

```yaml
# Already configured in k8s/base/api-deployment.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: violationsentinel-api-hpa
spec:
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilization: 70%
```

**Manual scaling**:
```bash
# Scale API pods
kubectl scale deployment violationsentinel-api --replicas=10 -n production

# Scale worker pods
kubectl scale deployment violationsentinel-celery-worker --replicas=20 -n production
```

### Celery Workers

**Add more workers for background tasks**:

```bash
# Increase worker replicas
kubectl scale deployment violationsentinel-celery-worker --replicas=10 -n production

# Monitor queue length
kubectl exec -it deployment/violationsentinel-api -n production -- \
  celery -A app.celery_worker inspect stats
```

### Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_violations_tenant_property 
  ON violations(tenant_id, property_id, issued_date DESC);

CREATE INDEX CONCURRENTLY idx_violations_risk_score 
  ON violations(risk_score DESC) WHERE is_resolved = false;

-- Enable TimescaleDB hypertable for violations
SELECT create_hypertable('violations', 'issued_date', if_not_exists => TRUE);
```

---

## Monitoring

### Prometheus Metrics

**Access Prometheus**:
```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
open http://localhost:9090
```

**Key Metrics**:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `celery_queue_length` - Task queue depth
- `db_connection_pool_active` - Database connections

### Grafana Dashboards

**Access Grafana**:
```bash
kubectl port-forward -n monitoring svc/grafana 3000:3000
open http://localhost:3000  # admin/admin
```

**Pre-configured Dashboards**:
1. **API Performance**: Request rate, latency, errors
2. **Database Health**: Connections, queries, replication lag
3. **Celery Workers**: Queue length, task duration
4. **Infrastructure**: CPU, memory, disk, network

### Alerting

**Critical Alerts** (PagerDuty):
- Service down > 2 minutes
- Error rate > 5%
- P95 latency > 2 seconds

**Warning Alerts** (Slack):
- CPU usage > 80%
- Memory usage > 85%
- Queue backup > 1000 tasks

---

## Backup & Recovery

### Automated Backups

**Database** (Already configured in Terraform):
- Full backup: Daily at 3 AM UTC
- Incremental: Every 6 hours
- Retention: 30 days
- Cross-region replication: Enabled

**Manual Backup**:
```bash
# Backup database
kubectl exec -it deployment/postgres -n production -- \
  pg_dump -U postgres violationsentinel | gzip > backup-$(date +%Y%m%d).sql.gz

# Backup to S3
aws s3 cp backup-$(date +%Y%m%d).sql.gz s3://violationsentinel-backups/
```

### Disaster Recovery

**Recovery Time Objective (RTO)**: 1 hour
**Recovery Point Objective (RPO)**: 15 minutes

**Recovery Steps**:
```bash
# 1. Provision new infrastructure
terraform apply

# 2. Restore database
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier violationsentinel-restored \
  --db-snapshot-identifier latest-snapshot

# 3. Deploy application
kubectl apply -f k8s/base/ -n production

# 4. Verify health
curl https://api.violationsentinel.com/health
```

---

## Security

### SSL/TLS Configuration

**Let's Encrypt** (Automatic):
```bash
# Already configured in k8s/base/ingress.yaml
annotations:
  cert-manager.io/cluster-issuer: letsencrypt-prod
```

**Custom Certificate**:
```bash
kubectl create secret tls violationsentinel-tls \
  --cert=path/to/cert.pem \
  --key=path/to/key.pem \
  -n production
```

### Secrets Management

**HashiCorp Vault** (Recommended):
```bash
# Install Vault
helm install vault hashicorp/vault

# Store secrets
vault kv put secret/violationsentinel \
  database_url="postgresql://..." \
  stripe_key="sk_live_..."
```

**Kubernetes Secrets**:
```bash
# Rotate secrets quarterly
kubectl create secret generic violationsentinel-secrets \
  --from-literal=secret-key="$(openssl rand -base64 32)" \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart deployments to pick up new secrets
kubectl rollout restart deployment/violationsentinel-api -n production
```

---

## Troubleshooting

### Common Issues

#### **Pods not starting**
```bash
# Check pod status
kubectl get pods -n production

# View pod logs
kubectl logs -f deployment/violationsentinel-api -n production

# Describe pod for events
kubectl describe pod <pod-name> -n production
```

#### **Database connection errors**
```bash
# Test database connectivity
kubectl exec -it deployment/violationsentinel-api -n production -- \
  python -c "from app.db import engine; print(engine.connect())"

# Check database credentials
kubectl get secret violationsentinel-secrets -n production -o yaml
```

#### **High latency**
```bash
# Check HPA status
kubectl get hpa -n production

# Scale up if needed
kubectl scale deployment violationsentinel-api --replicas=10 -n production

# Check database query performance
kubectl exec -it deployment/postgres -n production -- \
  psql -U postgres -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

---

## Performance Tuning

### API Optimization

```python
# app/core/config.py
RATE_LIMIT = 100  # Increase for high-traffic
DB_POOL_SIZE = 20  # Increase for concurrent requests
DB_MAX_OVERFLOW = 40
CACHE_TTL = 3600  # Tune based on data freshness needs
```

### Database Optimization

```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM violations WHERE tenant_id = 'xxx';

-- Vacuum and analyze regularly
VACUUM ANALYZE;

-- Adjust PostgreSQL settings
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET max_connections = 200;
```

### Redis Optimization

```bash
# Increase maxmemory for cache
kubectl edit configmap redis-config -n production

# Add:
maxmemory 4gb
maxmemory-policy allkeys-lru
```

---

## Maintenance

### Regular Tasks

**Daily**:
- Check Grafana dashboards
- Review error logs
- Monitor API latency

**Weekly**:
- Review security alerts
- Check backup integrity
- Analyze usage patterns

**Monthly**:
- Update dependencies
- Review and optimize database
- Security patch updates

**Quarterly**:
- Rotate secrets
- Disaster recovery drill
- Capacity planning review

---

## Support

### Documentation
- **API Docs**: https://api.violationsentinel.com/api/v1/docs
- **Technical White Paper**: `/docs/technical_white_paper.md`
- **Architecture Diagrams**: `/docs/architecture/`

### Community
- **GitHub Issues**: https://github.com/NickAiNYC/ViolationSentinel/issues
- **Slack**: https://violationsentinel.slack.com
- **Email**: support@violationsentinel.com

### Enterprise Support
- **24/7 Support**: Available with Enterprise plan
- **SLA**: 99.95% uptime guarantee
- **Response Times**: 
  - Critical: 1 hour
  - High: 4 hours
  - Medium: 1 business day

---

## Success Criteria

After deployment, verify:

✅ **Health**: `/health` returns 200
✅ **API**: Can create tenant, user, property
✅ **Database**: Queries executing in < 50ms
✅ **Cache**: Hit rate > 80%
✅ **Monitoring**: Grafana dashboards showing data
✅ **SSL**: HTTPS with valid certificate
✅ **Backups**: Automated backups configured

**Congratulations! ViolationSentinel is now running in production!**

---

## Next Steps

1. **Create your first tenant and user**
2. **Import properties** via API or CSV
3. **Configure webhooks** for Slack/Teams notifications
4. **Generate compliance reports**
5. **Set up billing** with Stripe integration
6. **Invite team members** with appropriate roles

**Need help?** Contact support@violationsentinel.com
