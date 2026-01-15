# ViolationSentinel Architecture

## System Overview

ViolationSentinel is a microservices-based PropTech platform built on a modern Python stack with enterprise-grade scalability and security.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   React UI   │  │  Mobile App  │  │  API Clients │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │         API Gateway / LB            │
          │         (HTTPS/TLS)                 │
          └──────────────────┬──────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                   Application Layer                          │
│  ┌────────────────────────────────────────────────────┐     │
│  │              FastAPI Application                   │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │     │
│  │  │Properties│ │Violations│ │   Risk   │          │     │
│  │  │   API    │ │   API    │ │   API    │  ...     │     │
│  │  └──────────┘ └──────────┘ └──────────┘          │     │
│  │                                                     │     │
│  │  ┌─────────────────────────────────────────────┐  │     │
│  │  │         Middleware Layer                     │  │     │
│  │  │  - Authentication (OAuth2/JWT)              │  │     │
│  │  │  - Authorization (RBAC)                     │  │     │
│  │  │  - Rate Limiting                            │  │     │
│  │  │  - CORS                                     │  │     │
│  │  │  - Security Headers                         │  │     │
│  │  │  - Request Logging                          │  │     │
│  │  │  - Error Handling                           │  │     │
│  │  └─────────────────────────────────────────────┘  │     │
│  └────────────────────────────────────────────────────┘     │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│                   Service Layer                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │ Risk Scoring │ │    Alert     │ │  Ingestion   │      │
│  │   Engine     │ │   Engine     │ │   Services   │      │
│  └──────────────┘ └──────────────┘ └──────────────┘      │
│                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │  ML Models   │ │Normalization │ │Notifications │      │
│  │  (XGBoost)   │ │   Service    │ │   Service    │      │
│  └──────────────┘ └──────────────┘ └──────────────┘      │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│                    Data Layer                              │
│  ┌────────────────────────────────────────────────────┐   │
│  │              PostgreSQL 15                         │   │
│  │  - Properties                                      │   │
│  │  - Violations                                      │   │
│  │  - Risk Scores                                     │   │
│  │  - Users & Organizations                           │   │
│  │  - Alerts & Alert Rules                            │   │
│  │  - Audit Logs                                      │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │                  Redis 7                           │   │
│  │  - Caching (API responses, risk scores)           │   │
│  │  - Session storage                                 │   │
│  │  - Celery message broker                          │   │
│  │  - Rate limiting counters                         │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Background Workers                          │
│  ┌────────────────────────────────────────────────────┐     │
│  │              Celery Workers                        │     │
│  │  - Data ingestion tasks                           │     │
│  │  - Risk score calculations                        │     │
│  │  - Alert checks                                   │     │
│  │  - Notification sending                           │     │
│  │  - ML model training                              │     │
│  │  - Report generation                              │     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │              Celery Beat                           │     │
│  │  - Scheduled tasks (cron-like)                    │     │
│  │  - Daily ingestion (2 AM)                         │     │
│  │  - Risk scoring (every 6 hours)                   │     │
│  │  - Alert checks (every 15 minutes)                │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                External Services                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ NYC Open Data│ │   SendGrid   │ │    Twilio    │        │
│  │  (SOCRATA)   │ │    (Email)   │ │     (SMS)    │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │    Slack     │ │   Stripe     │ │     AWS      │        │
│  │ (Webhooks)   │ │  (Billing)   │ │   (S3/ECS)   │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│             Monitoring & Observability                       │
│  ┌────────────────────────────────────────────────────┐     │
│  │              Prometheus                            │     │
│  │  - Metrics collection                             │     │
│  │  - API performance                                │     │
│  │  - Database queries                               │     │
│  │  - Celery tasks                                   │     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │           Structured Logging                       │     │
│  │  - JSON format                                    │     │
│  │  - Request/Response logging                       │     │
│  │  - Error tracking                                 │     │
│  │  - Audit trails                                   │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. API Gateway
- **Technology**: FastAPI with Uvicorn
- **Features**:
  - OpenAPI/Swagger documentation
  - Async request handling
  - WebSocket support (future)
  - Request validation (Pydantic)

### 2. Authentication & Authorization
- **OAuth2 with JWT**: Stateless token-based auth
- **API Keys**: Scoped access for integrations
- **RBAC**: Role-based access control
  - Admin: Full access
  - Manager: Read/write properties, alerts
  - Viewer: Read-only access
  - API User: Programmatic access

### 3. Database Layer
- **PostgreSQL 15**:
  - JSONB for flexible metadata
  - PostGIS for geospatial queries (future)
  - Connection pooling (SQLAlchemy)
  - Read replicas for scaling
- **Redis 7**:
  - L1 cache (hot data)
  - Session storage
  - Rate limiting
  - Pub/sub (future)

### 4. Background Processing
- **Celery Workers**:
  - Horizontal scaling
  - Task routing
  - Result backend
  - Retry logic
- **Celery Beat**:
  - Cron-like scheduling
  - Distributed locking

### 5. Data Ingestion Pipeline
```
NYC Open Data → Fetch → Normalize → Deduplicate → Store → Index
     ↓              ↓         ↓           ↓          ↓       ↓
  SOCRATA      Raw JSON   Clean    Hash Check   Postgres  Update
   API         Records    Transform            Risk Scores
```

### 6. Risk Scoring Engine
```
Property Data → Feature Engineering → ML Model → Risk Score
     ↓                  ↓                 ↓          ↓
Violations      - Violation count    XGBoost   Overall: 0-100
+ Metadata      - Severity weights   Model     Safety: 0-100
+ History       - Temporal features           Legal: 0-100
                - Property features           Financial: 0-100
                                              Trend: ↑↓→
```

### 7. Alert System
```
Alert Rule → Condition Check → Trigger → Notification
    ↓             ↓               ↓            ↓
Threshold    Query Data      Create Alert   Email/SMS/
 Config      Compare Values   Record        Slack/Webhook
```

## Data Flow

### 1. Property Risk Assessment Flow
```
1. User requests property risk score
2. API validates request & auth
3. Check Redis cache
4. If miss, query database
5. If stale, trigger async recalculation
6. Return current score
7. Cache result
```

### 2. Data Ingestion Flow
```
1. Celery beat triggers ingestion task
2. Worker fetches from NYC Open Data
3. Normalize and validate records
4. Check for duplicates (hash)
5. Insert/update database
6. Trigger risk score recalculation
7. Check alert rules
8. Send notifications if triggered
```

### 3. Alert Flow
```
1. Celery beat triggers alert check
2. Worker fetches active alert rules
3. For each rule:
   a. Query relevant data
   b. Evaluate condition
   c. If triggered, create alert
   d. Send notifications via channels
4. Log all activities
```

## Security Architecture

### Defense in Depth
1. **Network Layer**: VPC, Security Groups, WAF
2. **Application Layer**: HTTPS, CORS, Rate Limiting
3. **Authentication**: JWT, API Keys, MFA (future)
4. **Authorization**: RBAC, Scoped access
5. **Data Layer**: Encryption at rest, Connection encryption
6. **Audit**: Immutable logs, Access tracking

### Secrets Management
- Environment variables
- AWS Secrets Manager (production)
- Encrypted at rest
- Rotated regularly

## Scalability

### Horizontal Scaling
- **API**: Multiple instances behind load balancer
- **Workers**: Scale based on queue depth
- **Database**: Read replicas, Sharding (future)

### Caching Strategy
- **L1 (Redis)**: Hot data, 5-60 min TTL
- **L2 (Application)**: In-memory, 1-5 min TTL
- **CDN (future)**: Static assets

### Performance Targets
- API Response: < 200ms (p95)
- Database Queries: < 50ms (p95)
- Background Tasks: < 5 min (p95)
- Uptime: 99.9%

## Deployment Architecture

### Development
- Docker Compose
- Local PostgreSQL & Redis
- Hot reload enabled

### Staging
- AWS ECS Fargate
- RDS PostgreSQL
- ElastiCache Redis
- ALB with HTTPS

### Production
- Multi-AZ deployment
- Auto-scaling groups
- CloudWatch monitoring
- Automated backups
- Blue/green deployment

## Disaster Recovery

### Backup Strategy
- **Database**: Automated daily backups (7-day retention)
- **Redis**: RDB snapshots
- **Code**: Git repository
- **Configuration**: Infrastructure as Code (Terraform)

### Recovery Procedures
1. Database restore from backup (< 1 hour RTO)
2. Service restart from container images
3. Configuration from IaC
4. Traffic cutover

## Monitoring Strategy

### Metrics
- Request rate, latency, errors (RED method)
- Database connections, query time
- Cache hit rate
- Celery queue depth
- Business metrics (properties, violations, alerts)

### Alerts
- High error rate (> 1%)
- Slow responses (> 1s p95)
- High memory/CPU (> 80%)
- Failed background tasks
- Database connection exhaustion

### Logging
- Structured JSON logs
- Correlation IDs
- Request/response logging
- Error stack traces
- Audit trails

## Future Enhancements

### Phase 2 (Q3 2024)
- WebSocket for real-time updates
- GraphQL API
- Advanced ML models (time series)
- Multi-city expansion

### Phase 3 (Q4 2024)
- Mobile apps (iOS/Android)
- White-label deployments
- Advanced analytics dashboard
- Integration marketplace

### Phase 4 (2025)
- Predictive maintenance
- Insurance underwriting API
- Lender risk feeds
- AI-powered insights
