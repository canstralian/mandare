# Deployment Guide

## Overview

This guide covers deploying RIF Runtime to various environments: local Docker, cloud platforms, and Kubernetes.

## Deployment Environments

### Development

```bash
docker compose up --build
```

- Single container, hot reload enabled
- Data persisted locally in `data/`
- Healthcheck interval: 30s

### Production (Single Host)

```bash
docker compose -f docker-compose.prod.yml up -d
```

- 2 CPU cores, 1GB memory limit
- Read-only filesystem with tmpfs for temp files
- Security hardening: capability drops, no-new-privileges
- Persistent volumes for data and config
- Healthcheck with 40s startup period
- Restart policy: always

### Kubernetes (Production Multi-Node)

See `KUBERNETES.md` for full K8s deployment.

## Pre-Deployment Checklist

- [ ] Configuration reviewed: `rif.toml`
- [ ] Environment variables set: `.env.prod`
- [ ] Secrets provisioned: API keys, signing keys, DB passwords
- [ ] Data directories created and mounted
- [ ] Database initialized (if using SQL backend)
- [ ] Monitoring configured (Prometheus, logging)
- [ ] Backup strategy in place
- [ ] SSL/TLS certificates provisioned
- [ ] Firewall rules configured

## Configuration Management

### Development

```bash
cp .env.example .env
# Edit .env with local values
```

### Production

```bash
# Use Docker Secrets or environment variables
export RIF_SECURITY_SIGNING_KEY_FILE=/run/secrets/rif_signing_key
export RIF_STORAGE_DATA_DIR=/mnt/data
```

## Data Persistence

### Storage Backend Selection

**JSONL (Recommended for <1GB decisions/day)**

```yaml
RIF_STORAGE_BACKEND: jsonl
RIF_STORAGE_DECISIONS_FILE: /mnt/data/decisions.jsonl
```

**PostgreSQL (For high volume, querying)**

```yaml
RIF_STORAGE_BACKEND: postgres
RIF_DB_HOST: postgres.prod
RIF_DB_PORT: 5432
RIF_DB_NAME: rif_runtime
```

Initialize DB:

```bash
docker compose exec postgres psql -U rif_user -d rif_runtime \
  -f config/init.sql
```

### Backup Strategy

**JSONL**:

```bash
# Daily backup
0 2 * * * tar -czf backups/rif-data-$(date +%Y%m%d).tar.gz /mnt/data/

# Verify backup
tar -tzf backups/rif-data-20240115.tar.gz | head
```

**PostgreSQL**:

```bash
# Continuous replication
export PGPASSWORD=$(cat /run/secrets/db_password)
pg_dump -h postgres.prod -U rif_user rif_runtime | gzip > backups/db-$(date +%Y%m%d_%H%M%S).sql.gz

# Restore
gunzip < backups/db-20240115_020000.sql.gz | psql -U rif_user rif_runtime
```

## Scaling Considerations

### Single Instance (Development)

- Works for <10 requests/sec
- File-based storage (JSONL)
- Memory: 512MB

### Multi-Instance (Load Balanced)

Horizontal scaling requires shared storage:

```yaml
# docker-compose.yml (multi-instance)
services:
  server-1:
    <<: *server
    container_name: rif-server-1
    
  server-2:
    <<: *server
    container_name: rif-server-2
    
  server-3:
    <<: *server
    container_name: rif-server-3
    
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx.conf:/etc/nginx/nginx.conf:ro
```

**Considerations**:
- Shared database for audit trail consistency
- Session affinity not needed (stateless API)
- Evidence export coordinated via database lock
- Policy reload broadcast across instances

### High Availability

```bash
# K8s Deployment replicas
replicas: 3
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

## Networking

### Port Mapping

| Service | Port | Protocol | Use |
|---------|------|----------|-----|
| API | 8000 | HTTP/HTTPS | Main API |
| Metrics | 9090 | HTTP | Prometheus scrape |
| Tracing | 6831 | UDP | Jaeger |

### TLS/SSL

Terminate at reverse proxy or load balancer:

```nginx
server {
    listen 443 ssl;
    server_name api.example.com;
    
    ssl_certificate /etc/ssl/certs/api.example.com.crt;
    ssl_certificate_key /etc/ssl/private/api.example.com.key;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
}
```

### Network Policies (K8s)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: rif-network-policy
spec:
  podSelector:
    matchLabels:
      app: rif-runtime
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: TCP
          port: 443
```

## Monitoring & Observability

### Health Checks

```bash
curl http://localhost:8000/health
```

Response (healthy):

```json
{
  "status": "healthy",
  "version": "0.3.0rc1",
  "uptime_seconds": 3600,
  "decisions_processed": 1250
}
```

### Metrics (Prometheus)

```bash
curl http://localhost:9090/metrics
```

Key metrics:

- `rif_policy_evaluations_total` — Total decisions
- `rif_policy_evaluation_duration_seconds` — Decision latency
- `rif_execution_duration_seconds` — Execution time
- `rif_storage_write_errors_total` — Storage failures
- `rif_active_executions` — In-flight requests

### Logging

**Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

```bash
export RIF_LOG_LEVEL=INFO
# Logs to stdout (Docker Compose will capture)
```

JSON structured logging:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "component": "policy_engine",
  "message": "Policy evaluation complete",
  "decision_id": "dec_abc123",
  "decision": "allow",
  "duration_ms": 45
}
```

### Tracing (Optional)

Enable Jaeger for distributed tracing:

```bash
export RIF_TRACING_ENABLED=true
export RIF_TRACING_JAEGER_ENDPOINT=http://jaeger:6831
# Access traces at http://localhost:16686
```

## Updating & Rollback

### Blue-Green Deployment

```bash
# Deploy new version (green)
docker compose -f docker-compose.prod.yml up -d rif-runtime-green

# Health check
curl http://localhost:8001/health

# Switch traffic (via nginx/LB config)
# If failure, revert to blue
```

### Rolling Update (K8s)

```bash
kubectl set image deployment/rif-runtime \
  rif-runtime=rif-runtime:0.4.0 --record
  
# Monitor rollout
kubectl rollout status deployment/rif-runtime

# Rollback if needed
kubectl rollout undo deployment/rif-runtime
```

## Security in Production

### Secrets Management

**Docker Secrets**:

```bash
echo "my_signing_key_content" | docker secret create rif_signing_key -

# Reference in compose.yml
secrets:
  rif_signing_key:
    external: true
```

**Kubernetes Secrets**:

```bash
kubectl create secret generic rif-secrets \
  --from-file=signing_key=/path/to/key \
  --from-file=db_password=/path/to/password
```

### Network Security

- Firewall ingress to port 8000 only from load balancer
- Egress restricted to approved API endpoints
- Internal mTLS between services (if multi-host)

### Audit & Compliance

- All decisions logged immutably to JSONL/DB
- Regular compliance audits: `rif audit query --since 30d`
- Evidence export for regulatory review: `rif evidence export compliance_bundle.zip`

## Disaster Recovery

### Runbook: Full Service Loss

1. **Verify storage integrity**:
   ```bash
   tar -tzf backups/rif-data-20240115.tar.gz | wc -l
   # Should show thousands of files
   ```

2. **Restore from backup**:
   ```bash
   rm -rf /mnt/data/*
   tar -xzf backups/rif-data-20240115.tar.gz -C /mnt/
   ```

3. **Restart service**:
   ```bash
   docker compose -f docker-compose.prod.yml restart server
   ```

4. **Verify recovery**:
   ```bash
   curl http://localhost:8000/health
   rif audit query --since 24h
   ```

### Runbook: Database Corruption

1. **Stop service**:
   ```bash
   docker compose -f docker-compose.prod.yml stop server
   ```

2. **Restore DB from backup**:
   ```bash
   gunzip < backups/db-20240114.sql.gz | psql -U rif_user rif_runtime
   ```

3. **Restart**:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

## Cost Optimization

- **Auto-scaling**: Scale down to 1 instance during low traffic
- **Storage tiering**: Archive old JSONL files to cold storage after 90 days
- **Resource limits**: Tune memory/CPU based on actual usage

## Troubleshooting

### Service Won't Start

```bash
docker compose logs server | tail -50
# Check for configuration errors, port conflicts, or missing secrets
```

### High Memory Usage

```bash
docker stats rif-runtime-server-1
# If persistent, check for memory leaks in policy engine
```

### Policy Reload Fails

```bash
rif policy reload config/policies.yaml --validate
# Check YAML syntax and schema validation
```

For more help, see `DEVELOPMENT.md` and `docs/TROUBLESHOOTING.md`.
