# TAP Deployment Guide - Environment Variables

Guide for deploying the three applications on Target Application Platform (TAP) with proper environment variable configuration.

---

## Overview

Three `.env.tap` files have been created for TAP deployment:

```
apps/plm-think-tank-ai/.env.tap           # Think Tank API env vars
apps/plm-tcin-mapper-api/.env.tap         # TCIN Mapper API env vars
apps/plm-tcin-mapper-client/.env.tap      # TCIN Mapper UI env vars
```

Each file contains:
- ✅ Production-appropriate values
- ✅ Detailed comments explaining each variable
- ✅ Placeholder syntax for secrets to be injected by TAP
- ✅ Service dependency information
- ✅ Health check configuration
- ✅ Troubleshooting guidance

---

## File Locations

```
test-ai-app/
├── apps/
│   ├── plm-think-tank-ai/
│   │   └── .env.tap              ← Think Tank environment
│   ├── plm-tcin-mapper-api/
│   │   └── .env.tap              ← TCIN Mapper API environment
│   └── plm-tcin-mapper-client/
│       └── .env.tap              ← TCIN Mapper Client environment
└── TAP_DEPLOYMENT_GUIDE.md       ← This file
```

---

## Quick Reference

### plm-think-tank-ai

| Variable | Value | Notes |
|----------|-------|-------|
| APP_PORT | 8080 | TAP standard |
| APP_ENV | production | Use staging for staging env |
| LOG_LEVEL | INFO | Set to DEBUG for troubleshooting |
| GUNICORN_WORKERS | 4 | Adjust based on CPU allocation |
| GUNICORN_TIMEOUT | 120 | Increase for long operations |
| MONGO_URL | mongodb://mongo-cluster:27017 | TAP will inject actual URL |
| THINKTANK_API_KEY | ${THINKTANK_API_KEY} | Injected by TAP from vault |

### plm-tcin-mapper-api

| Variable | Value | Notes |
|----------|-------|-------|
| APP_PORT | 8080 | TAP standard |
| APP_ENV | production | Use staging for staging env |
| LOG_LEVEL | INFO | Set to DEBUG for troubleshooting |
| GUNICORN_WORKERS | 4 | Adjust based on CPU allocation |
| GUNICORN_TIMEOUT | 120 | Increase for batch operations |
| MONGO_URL | mongodb://mongo-cluster:27017 | TAP will inject actual URL |
| MATCHING_AUTO_CONFIRM_THRESHOLD | 0.85 | Tuning parameter |
| MATCHING_NO_MATCH_THRESHOLD | 0.75 | Tuning parameter |
| THINKTANK_API_KEY | ${THINKTANK_API_KEY} | Injected by TAP from vault |

### plm-tcin-mapper-client

| Variable | Value | Notes |
|----------|-------|-------|
| APP_PORT | 8080 | Streamlit port |
| **API_BASE_URL** | **http://plm-tcin-mapper-api:8080** | **CRITICAL** - Points to API |

---

## TAP Configuration Example

### 1. Service Configuration (TAP Pipeline)

```yaml
---
# plm-think-tank-ai Service
apiVersion: v1
kind: Service
metadata:
  name: plm-think-tank-ai
  namespace: default
spec:
  selector:
    app: plm-think-tank-ai
  ports:
    - port: 8080
      targetPort: 8080
      protocol: TCP
---
# plm-tcin-mapper-api Service
apiVersion: v1
kind: Service
metadata:
  name: plm-tcin-mapper-api
  namespace: default
spec:
  selector:
    app: plm-tcin-mapper-api
  ports:
    - port: 8080
      targetPort: 8080
      protocol: TCP
---
# plm-tcin-mapper-client Service
apiVersion: v1
kind: Service
metadata:
  name: plm-tcin-mapper-client
  namespace: default
spec:
  selector:
    app: plm-tcin-mapper-client
  ports:
    - port: 8080
      targetPort: 8080
      protocol: TCP
```

### 2. Secrets (TAP Vault)

Secrets should be stored in TAP vault and injected at runtime:

```
plmtools/thinktank_api_key            → THINKTANK_API_KEY
plmtools/thinktank_gateway_api_key    → THINKTANK_GATEWAY_API_KEY
plmtools/thinktank_oauth_client_id    → THINKTANK_OAUTH_CLIENT_ID
plmtools/mongo_url                    → MONGO_URL (with credentials)
```

### 3. Deployment Configuration

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: plm-tcin-mapper-api
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: api
        image: docker.target.com/iam/spark/plm-tcin-mapper-api:latest
        ports:
        - containerPort: 8080
        env:
        # From .env.tap
        - name: APP_PORT
          value: "8080"
        - name: APP_ENV
          value: "production"
        - name: LOG_LEVEL
          value: "INFO"
        - name: GUNICORN_WORKERS
          value: "4"
        - name: GUNICORN_TIMEOUT
          value: "120"
        # From secrets
        - name: MONGO_URL
          valueFrom:
            secretKeyRef:
              name: plm-secrets
              key: mongo-url
        - name: THINKTANK_API_KEY
          valueFrom:
            secretKeyRef:
              name: plm-secrets
              key: thinktank-api-key
        # Health check
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 15
          timeoutSeconds: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 15
        # Volume mounts
        volumeMounts:
        - name: config
          mountPath: /tap/config
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: plm-config
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: plm-tcin-mapper-client
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: client
        image: docker.target.com/iam/spark/plm-tcin-mapper-client:latest
        ports:
        - containerPort: 8080
        env:
        - name: APP_PORT
          value: "8080"
        - name: API_BASE_URL
          value: "http://plm-tcin-mapper-api:8080"
        # Health check (Streamlit)
        livenessProbe:
          httpGet:
            path: /_stcore/health
            port: 8080
          initialDelaySeconds: 45
          periodSeconds: 15
          timeoutSeconds: 3
        readinessProbe:
          httpGet:
            path: /_stcore/health
            port: 8080
          initialDelaySeconds: 45
          periodSeconds: 15
```

---

## Environment Variable Values by Environment

### Development Environment

```bash
# API
APP_PORT=8080
APP_ENV=development
LOG_LEVEL=DEBUG
GUNICORN_WORKERS=2
MONGO_URL=mongodb://mongo-dev:27017

# Client
API_BASE_URL=http://plm-tcin-mapper-api-dev:8080
```

### Staging Environment

```bash
# API
APP_PORT=8080
APP_ENV=staging
LOG_LEVEL=INFO
GUNICORN_WORKERS=4
MONGO_URL=mongodb://mongo-stage:27017

# Client
API_BASE_URL=http://plm-tcin-mapper-api-stage:8080
```

### Production Environment

```bash
# API
APP_PORT=8080
APP_ENV=production
LOG_LEVEL=INFO
GUNICORN_WORKERS=8
MONGO_URL=mongodb://mongo-prod:27017

# Client
API_BASE_URL=http://plm-tcin-mapper-api:8080
```

---

## Critical Configuration Points

### 🔴 CRITICAL: API_BASE_URL (Client)

```bash
API_BASE_URL=http://plm-tcin-mapper-api:8080
```

**Why critical:**
- The client **CANNOT** function without a working API
- All 10 UI pages depend on API calls
- Wrong URL → all pages show "Connection Error"
- Must use service DNS name in TAP (not IP address)

**Troubleshooting:**
```bash
# From client pod, verify API connectivity
curl http://plm-tcin-mapper-api:8080/health

# Should return:
# {"status": "ok", "llm_provider": "thinktank", ...}
```

### 🔴 CRITICAL: Secrets Injection

**Required secrets in TAP vault:**
```
plmtools/thinktank_api_key            (API and Think Tank)
plmtools/thinktank_gateway_api_key    (optional)
plmtools/thinktank_oauth_client_id    (optional)
plmtools/mongo_url                    (if auth required)
```

**Verification:**
```bash
# Check if secrets were injected
env | grep THINKTANK
env | grep MONGO_URL

# Both should show values (not ${VAR_NAME})
```

### 🟡 IMPORTANT: Health Checks

Each service has a health endpoint:

```bash
# API health (both think-tank and mapper-api)
curl http://pod-ip:8080/health
# Returns: {"status": "ok", ...}

# Client health (Streamlit)
curl http://pod-ip:8080/_stcore/health
# Returns: 200 OK

# Different endpoints - note the difference!
```

---

## Scaling Configuration

### Adjust GUNICORN_WORKERS

Based on pod CPU allocation:

```bash
# CPU cores: 1 → WORKERS=3
# CPU cores: 2 → WORKERS=5
# CPU cores: 4 → WORKERS=9
# CPU cores: 8 → WORKERS=17

# Formula: (CPU_CORES × 2) + 1

# For TAP, check pod spec and adjust:
GUNICORN_WORKERS=<calculated_value>
```

### Adjust GUNICORN_TIMEOUT

For long-running operations:

```bash
# Default: 120 seconds
# For batch operations: 180-300 seconds

GUNICORN_TIMEOUT=240  # 4 minutes
```

### Adjust INGESTION_BATCH_SIZE

Based on available memory:

```bash
# Memory available: 512MB → BATCH_SIZE=250
# Memory available: 1GB   → BATCH_SIZE=500
# Memory available: 2GB   → BATCH_SIZE=1000

INGESTION_BATCH_SIZE=500
```

---

## Monitoring in TAP

### Health Endpoints

```bash
# API health
kubectl exec -it <api-pod> -- curl localhost:8080/health

# Client health
kubectl exec -it <client-pod> -- curl localhost:8080/_stcore/health
```

### Logs

```bash
# API logs
kubectl logs -f deployment/plm-tcin-mapper-api

# Client logs
kubectl logs -f deployment/plm-tcin-mapper-client

# Follow real-time
kubectl logs -f <pod-name> --timestamps=true
```

### Metrics

```bash
# Check endpoints being called
kubectl logs <api-pod> | grep "GET /api/v1"

# Check error rates
kubectl logs <api-pod> | grep "ERROR"

# Monitor latency
kubectl logs <api-pod> | grep "response_time"
```

---

## Troubleshooting

### Client shows "Connection Error"

**Steps:**
1. Verify API_BASE_URL is set correctly
   ```bash
   kubectl exec -it <client-pod> -- env | grep API_BASE_URL
   ```

2. Check API health
   ```bash
   kubectl exec -it <client-pod> -- curl http://plm-tcin-mapper-api:8080/health
   ```

3. Check network policy
   ```bash
   # Verify client pod can reach API pod
   kubectl exec -it <client-pod> -- ping plm-tcin-mapper-api
   ```

4. Check API logs
   ```bash
   kubectl logs <api-pod> | tail -20
   ```

### API responds slow

**Steps:**
1. Check GUNICORN_WORKERS
   ```bash
   kubectl exec -it <api-pod> -- env | grep GUNICORN_WORKERS
   ```

2. Increase workers
   ```bash
   # Edit deployment and increase GUNICORN_WORKERS
   kubectl set env deployment/plm-tcin-mapper-api GUNICORN_WORKERS=8
   ```

3. Check MongoDB connection
   ```bash
   kubectl exec -it <api-pod> -- mongosh mongodb://mongo-cluster:27017
   ```

4. Monitor pod resources
   ```bash
   kubectl top pod <api-pod>  # CPU, memory usage
   ```

### Secrets not injected

**Steps:**
1. Verify secrets exist in TAP vault
   ```bash
   # In TAP console, check:
   # Vault → plmtools → thinktank_api_key
   ```

2. Check if secret is mounted
   ```bash
   kubectl get secrets
   kubectl describe secret plm-secrets
   ```

3. Verify environment variable
   ```bash
   kubectl exec -it <pod> -- env | grep THINKTANK
   ```

---

## Deployment Checklist

Before deploying to TAP:

- [ ] `.env.tap` files created for all 3 apps
- [ ] Secrets registered in TAP vault
- [ ] Service dependencies configured
- [ ] API_BASE_URL points to API service DNS
- [ ] Health endpoints configured in Dockerfile
- [ ] GUNICORN_WORKERS sized for CPU allocation
- [ ] MONGO_URL points to correct MongoDB cluster
- [ ] Log level set appropriately (INFO for prod)
- [ ] Replicas configured for HA (min 2)
- [ ] Resource requests/limits set

---

## Network Diagram

```
┌─────────────────────────────────────┐
│  TAP Kubernetes Cluster             │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────┐                   │
│  │   Client    │                   │
│  │  (Replica1) │                   │
│  └──────┬──────┘                   │
│         │ API_BASE_URL=            │
│         │ http://api:8080          │
│         │                           │
│  ┌──────▼──────────────┐           │
│  │  API Service        │           │
│  │  (2+ replicas)      │           │
│  │  DNS: api:8080      │           │
│  └──────┬──────────────┘           │
│         │                           │
│  ┌──────▼──────────────┐           │
│  │  MongoDB Cluster    │           │
│  │  (External or       │           │
│  │   in-cluster)       │           │
│  └─────────────────────┘           │
│                                     │
└─────────────────────────────────────┘
```

---

## Next Steps

1. **Prepare secrets in TAP vault**
   - Store THINKTANK_API_KEY
   - Store MONGO_URL with credentials

2. **Configure services in TAP**
   - Create ConfigMaps for base.yaml
   - Create secrets for API keys

3. **Deploy using Vela pipeline**
   - Push to repository
   - Vela builds Docker images
   - TAP deploys from images

4. **Verify deployment**
   - Check health endpoints
   - Test UI connectivity to API
   - Monitor logs for errors

---

## Reference Files

- `apps/plm-think-tank-ai/.env.tap` — Think Tank API environment
- `apps/plm-tcin-mapper-api/.env.tap` — TCIN Mapper API environment
- `apps/plm-tcin-mapper-client/.env.tap` — TCIN Mapper Client environment
- `environment.md` — Complete environment variables reference
- `ARCHITECTURE.md` — System architecture overview

---

**Last Updated:** 2026-06-12
**Status:** Ready for TAP deployment
