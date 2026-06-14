# TAP Environment Configuration - How .env.tap Translates to TAP

**Important Clarification:** `.env.tap` files are **documentation/reference** only. TAP does NOT directly read `.env` files. Instead, environment variables are set through TAP's configuration mechanisms.

---

## Overview

| Component | What it contains | How used |
|-----------|-----------------|----------|
| **.env.tap files** | Documentation of all env vars needed | Reference for what to configure in TAP |
| **/tap/config/** | YAML config files (base.yaml, etc.) | Read by application at startup |
| **Pod spec env vars** | Environment variables | Set by TAP deployment manifest |
| **Kubernetes Secrets** | Secret values (API keys, credentials) | Mounted or injected by TAP |
| **ConfigMaps** | Non-secret config data | Mounted or injected by TAP |

---

## How TAP Actually Sets Environment Variables

### Method 1: Pod Spec (Most Common)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: plm-tcin-mapper-api
spec:
  template:
    spec:
      containers:
      - name: api
        image: plm-tcin-mapper-api:latest
        env:
        # These come from your .env.tap files
        - name: APP_PORT
          value: "8080"
        - name: APP_ENV
          value: "production"
        - name: LOG_LEVEL
          value: "INFO"
        - name: GUNICORN_WORKERS
          value: "4"
```

### Method 2: From Kubernetes Secrets

```yaml
env:
- name: THINKTANK_API_KEY
  valueFrom:
    secretKeyRef:
      name: plm-secrets
      key: thinktank-api-key
- name: MONGO_URL
  valueFrom:
    secretKeyRef:
      name: plm-secrets
      key: mongo-url
```

### Method 3: From ConfigMap

```yaml
env:
- name: MATCHING_AUTO_CONFIRM_THRESHOLD
  valueFrom:
    configMapKeyRef:
      name: plm-config
      key: matching-auto-confirm-threshold
```

### Method 4: Mounted as Files (for base.yaml)

```yaml
volumeMounts:
- name: config
  mountPath: /tap/config
  readOnly: true
volumes:
- name: config
  configMap:
    name: base-yaml-config
```

---

## What `/tap/config/` Contains

`/tap/config/` is a **directory** that TAP mounts, containing actual configuration **files**, NOT environment variables:

```
/tap/config/
├── base.yaml          ← Application configuration (YAML)
├── secrets/           ← Secret files (if mounted)
└── certificates/      ← TLS certificates
```

### base.yaml (Example)

```yaml
app:
  name: "plm-tcin-mapper-api"
  env: "production"
  log_level: "INFO"

spark:
  host: "0.0.0.0"
  port: 8080

mongo:
  url: "mongodb://mongo-cluster:27017"
  database: "tcin_mapper"

matching:
  auto_confirm_threshold: 0.85
  no_match_threshold: 0.75
  llm_fallback_threshold: 0.60
```

**Not** a `.env` file with `KEY=value` syntax.

---

## How the Application Uses Configuration

```
┌─────────────────────────────────────────┐
│  TAP Pod Creation                       │
├─────────────────────────────────────────┤
│                                         │
│  1. Set pod environment variables       │
│     (from pod spec env:, Secrets)       │
│                                         │
│  2. Mount /tap/config volume            │
│     (contains base.yaml, certificates)  │
│                                         │
└────────┬────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│  Application Startup                    │
├─────────────────────────────────────────┤
│                                         │
│  1. Read environment variables          │
│     (APP_PORT, GUNICORN_WORKERS, etc)   │
│                                         │
│  2. Check for /tap/config/base.yaml     │
│     if not found, use /app/config       │
│                                         │
│  3. Load base.yaml into settings        │
│     (database URLs, thresholds, etc)    │
│                                         │
│  4. Application ready with config       │
│                                         │
└─────────────────────────────────────────┘
```

---

## Translating .env.tap to TAP Configuration

### Step-by-Step

#### 1. Read .env.tap file
```bash
# apps/plm-tcin-mapper-api/.env.tap contains:
APP_PORT=8080
APP_ENV=production
LOG_LEVEL=INFO
GUNICORN_WORKERS=4
MONGO_URL=mongodb://mongo-cluster:27017
THINKTANK_API_KEY=${THINKTANK_API_KEY}
```

#### 2. Categorize the variables

| Category | Variables | How to set in TAP |
|----------|-----------|------------------|
| **Direct env vars** | APP_PORT, APP_ENV, LOG_LEVEL, GUNICORN_WORKERS | Pod spec `env:` section |
| **Secrets** | THINKTANK_API_KEY, MONGO_URL (with auth) | Kubernetes Secret, inject as env |
| **Config file** | Matching thresholds, database URL | base.yaml (mounted at /tap/config) |

#### 3. Create Kubernetes Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: plm-secrets
  namespace: default
type: Opaque
stringData:
  thinktank-api-key: "your-actual-api-key"
  mongo-url: "mongodb://user:pass@mongo-cluster:27017"
  thinktank-gateway-api-key: "gateway-key-if-needed"
  thinktank-oauth-client-id: "oauth-id-if-needed"
```

#### 4. Create ConfigMap for base.yaml

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: base-yaml-config
  namespace: default
data:
  base.yaml: |
    app:
      name: "plm-tcin-mapper-api"
      env: "production"
      log_level: "INFO"
    
    spark:
      host: "0.0.0.0"
      port: 8080
    
    mongo:
      url: "mongodb://mongo-cluster:27017"
      database: "tcin_mapper"
    
    matching:
      auto_confirm_threshold: 0.85
      no_match_threshold: 0.75
      llm_fallback_threshold: 0.60
      low_confidence_threshold: 0.50
      llm_ambiguity_band: 0.15
    
    llm:
      provider: "thinktank"
      model: "gemini-1.5-pro"
      temperature: 1.0
      max_tokens: 2048
      request_timeout: 120
      max_retries: 3
```

#### 5. Create Deployment with environment injection

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: plm-tcin-mapper-api
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: plm-tcin-mapper-api
  template:
    metadata:
      labels:
        app: plm-tcin-mapper-api
    spec:
      containers:
      - name: api
        image: docker.target.com/iam/spark/plm-tcin-mapper-api:latest
        imagePullPolicy: Always
        
        ports:
        - name: http
          containerPort: 8080
          protocol: TCP
        
        # ══════════════════════════════════════════════════════════
        # ENVIRONMENT VARIABLES (from .env.tap)
        # ══════════════════════════════════════════════════════════
        env:
        # Direct values
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
        - name: APP_CONFIG_DIR
          value: "/app/config"  # default, TAP overrides with /tap/config
        
        # From Secrets
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
        - name: THINKTANK_GATEWAY_API_KEY
          valueFrom:
            secretKeyRef:
              name: plm-secrets
              key: thinktank-gateway-api-key
        - name: THINKTANK_OAUTH_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: plm-secrets
              key: thinktank-oauth-client-id
        
        # ══════════════════════════════════════════════════════════
        # VOLUME MOUNTS (/tap/config with base.yaml)
        # ══════════════════════════════════════════════════════════
        volumeMounts:
        - name: config
          mountPath: /tap/config
          readOnly: true
        - name: certificates
          mountPath: /tap/certificates
          readOnly: true
        
        # ══════════════════════════════════════════════════════════
        # HEALTH CHECKS
        # ══════════════════════════════════════════════════════════
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 30
          periodSeconds: 15
          timeoutSeconds: 3
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 2
        
        # ══════════════════════════════════════════════════════════
        # RESOURCE LIMITS
        # ══════════════════════════════════════════════════════════
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      
      # ══════════════════════════════════════════════════════════
      # VOLUMES
      # ══════════════════════════════════════════════════════════
      volumes:
      - name: config
        configMap:
          name: base-yaml-config
          defaultMode: 0644
      - name: certificates
        secret:
          secretName: plm-certificates
          defaultMode: 0644
      
      # ══════════════════════════════════════════════════════════
      # SCHEDULING & AFFINITY
      # ══════════════════════════════════════════════════════════
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - plm-tcin-mapper-api
              topologyKey: kubernetes.io/hostname
      
      restartPolicy: Always
      terminationGracePeriodSeconds: 30
```

---

## For Streamlit Client

### .env.tap file content:
```bash
APP_PORT=8080
API_BASE_URL=http://plm-tcin-mapper-api:8080
```

### TAP Deployment:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: plm-tcin-mapper-client
spec:
  template:
    spec:
      containers:
      - name: client
        image: plm-tcin-mapper-client:latest
        env:
        - name: APP_PORT
          value: "8080"
        - name: API_BASE_URL
          value: "http://plm-tcin-mapper-api:8080"  # ← CRITICAL
        
        livenessProbe:
          httpGet:
            path: /_stcore/health
            port: 8080
          initialDelaySeconds: 45  # Streamlit takes longer
          periodSeconds: 15
```

---

## Important Notes

### 1. .env.tap is Documentation

The `.env.tap` files are **reference documentation**, showing:
- What variables are needed
- Their default values
- Where they come from (secret vs. config)
- How to override them

**TAP does NOT read .env files directly.**

### 2. /tap/config Contains YAML Files

`/tap/config/` is a mounted directory containing:
- `base.yaml` - Application configuration
- `certificates/` - TLS certificates
- `secrets/` - Secret files (if needed)

**Not environment variable files.**

### 3. Environment Variables Set Three Ways

1. **Directly in pod spec**
   ```yaml
   env:
   - name: APP_PORT
     value: "8080"
   ```

2. **From Kubernetes Secrets**
   ```yaml
   - name: API_KEY
     valueFrom:
       secretKeyRef:
         name: my-secret
         key: api-key
   ```

3. **From ConfigMaps**
   ```yaml
   - name: SETTING
     valueFrom:
       configMapKeyRef:
         name: my-config
         key: setting
   ```

### 4. Application Reads Both

At startup, the application reads:
1. **Environment variables** (from pod spec)
2. **config/base.yaml** (from /tap/config or /app/config)

The entrypoint.sh script handles this:
```bash
if [ -f "/tap/config/base.yaml" ]; then
    export APP_CONFIG_DIR=/tap/config
else
    export APP_CONFIG_DIR=/app/config
fi
```

---

## Workflow for TAP Deployment

### 1. Use .env.tap as Reference
```bash
cat apps/plm-tcin-mapper-api/.env.tap
# Shows all variables you need to configure
```

### 2. Create Kubernetes Secret
```bash
# In TAP console or via kubectl
kubectl create secret generic plm-secrets \
  --from-literal=thinktank-api-key=<your-key> \
  --from-literal=mongo-url=<your-url> \
  -n default
```

### 3. Create ConfigMap for base.yaml
```bash
# In TAP console or via kubectl
kubectl create configmap base-yaml-config \
  --from-file=base.yaml=config/base.yaml \
  -n default
```

### 4. Create Deployment YAML
Use the template above, filling in:
- Image URLs
- Secret names
- ConfigMap names
- Resource limits
- Replica count

### 5. Apply to TAP
```bash
# TAP will automatically:
# 1. Create pods
# 2. Mount /tap/config with base.yaml
# 3. Inject secrets as environment variables
# 4. Set direct environment variables
# 5. Start health checks
```

---

## Summary

| Concept | What it is | How TAP uses it |
|---------|-----------|-----------------|
| **.env.tap** | Documentation of required env vars | Reference for creating Secrets, ConfigMaps, and pod spec |
| **/tap/config/** | Directory with YAML config files | TAP mounts it, app reads base.yaml at startup |
| **Kubernetes Secret** | Encrypted key-value store | Hold API keys, passwords, credentials |
| **ConfigMap** | Non-secret configuration | Store config files, environment variables |
| **Pod spec env** | Direct environment variables | Set APP_PORT, LOG_LEVEL, GUNICORN_WORKERS, etc. |

**The .env.tap files guide you on what to configure in TAP, but TAP itself uses Kubernetes Secrets, ConfigMaps, and pod spec `env:` sections to actually set the values.**

---

**Created:** 2026-06-12
**Status:** ✅ Clarification Document
