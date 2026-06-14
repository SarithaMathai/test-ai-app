# TAP Environment Variables - Summary

Three `.env.tap` files have been created for TAP deployment testing and production use.

---

## Files Created

### 1. **plm-think-tank-ai/.env.tap**
- **Size:** 7 KB
- **Purpose:** Environment variables for Think Tank AI service
- **Key Variables:**
  - `APP_PORT=8080` - Service port
  - `APP_ENV=production` - Environment
  - `GUNICORN_WORKERS=4` - Worker processes
  - `THINKTANK_API_KEY=${THINKTANK_API_KEY}` - Injected by TAP
  - `MONGO_URL=mongodb://mongo-cluster:27017` - Database

### 2. **plm-tcin-mapper-api/.env.tap**
- **Size:** 12 KB
- **Purpose:** Environment variables for TCIN Mapper API service
- **Key Variables:**
  - `APP_PORT=8080` - Service port
  - `APP_ENV=production` - Environment
  - `GUNICORN_WORKERS=4` - Worker processes
  - `GUNICORN_TIMEOUT=120` - Request timeout
  - `MATCHING_AUTO_CONFIRM_THRESHOLD=0.85` - Algorithm tuning
  - `THINKTANK_API_KEY=${THINKTANK_API_KEY}` - Injected by TAP
  - `MONGO_URL=mongodb://mongo-cluster:27017` - Database

### 3. **plm-tcin-mapper-client/.env.tap**
- **Size:** 13 KB
- **Purpose:** Environment variables for Streamlit UI service
- **Key Variables:**
  - `APP_PORT=8080` - Service port
  - **`API_BASE_URL=http://plm-tcin-mapper-api:8080`** - CRITICAL
    - Points to the API service
    - Must be set correctly or UI won't work
    - Uses Kubernetes service DNS name

### 4. **TAP_DEPLOYMENT_GUIDE.md**
- **Size:** 14 KB
- **Purpose:** Complete guide for deploying on TAP with environment variables
- **Includes:**
  - Quick reference tables
  - Environment values by stage (dev/staging/prod)
  - Kubernetes configuration examples
  - Health check setup
  - Scaling configuration
  - Troubleshooting guide

---

## File Structure

Each `.env.tap` file contains:

```
✓ Core Application Settings
  └─ APP_PORT, APP_ENV, LOG_LEVEL, APP_NAME

✓ Gunicorn/ASGI Configuration
  └─ GUNICORN_WORKERS, GUNICORN_TIMEOUT

✓ Configuration Directory
  └─ APP_CONFIG_DIR (default or TAP override)

✓ Database Configuration
  └─ MONGO_URL, MONGO_DATABASE

✓ LLM Configuration
  └─ LLM_PROVIDER, LLM_MODEL

✓ Service-Specific Settings
  └─ Algorithm thresholds (API only)
  └─ API_BASE_URL (Client only)

✓ Secrets Placeholders
  └─ ${THINKTANK_API_KEY} - TAP injects from vault
  └─ ${THINKTANK_GATEWAY_API_KEY} - Optional
  └─ ${THINKTANK_OAUTH_CLIENT_ID} - Optional

✓ Detailed Comments
  └─ Explanation for each variable
  └─ Example values
  └─ TAP-specific notes
  └─ Troubleshooting guidance
```

---

## How to Use for TAP Testing

### Step 1: Review Environment Files

```bash
# Read the files to understand what each variable does
cat apps/plm-think-tank-ai/.env.tap
cat apps/plm-tcin-mapper-api/.env.tap
cat apps/plm-tcin-mapper-client/.env.tap
```

### Step 2: Identify Secrets to Inject

From the files, you'll see secrets that need to be in TAP vault:

```bash
THINKTANK_API_KEY=${THINKTANK_API_KEY}
THINKTANK_GATEWAY_API_KEY=${THINKTANK_GATEWAY_API_KEY}
THINKTANK_OAUTH_CLIENT_ID=${THINKTANK_OAUTH_CLIENT_ID}
MONGO_URL=mongodb://mongo-cluster:27017  # May need credentials
```

### Step 3: Configure TAP

Use `TAP_DEPLOYMENT_GUIDE.md` to:
1. Create Kubernetes services
2. Configure secrets in TAP vault
3. Create deployments with environment variables
4. Set up health checks
5. Configure service dependencies

### Step 4: Deploy

```bash
# TAP will:
# 1. Mount /tap/config with base.yaml
# 2. Inject secrets from vault
# 3. Set environment variables from .env.tap
# 4. Start containers with health checks
# 5. Monitor using health endpoints
```

---

## Key Values for TAP

### For DEV Environment

```bash
# API services
APP_ENV=development
LOG_LEVEL=DEBUG
GUNICORN_WORKERS=2
MONGO_URL=mongodb://mongo-dev:27017

# Client
API_BASE_URL=http://plm-tcin-mapper-api-dev:8080
```

### For STAGING Environment

```bash
# API services
APP_ENV=staging
LOG_LEVEL=INFO
GUNICORN_WORKERS=4
MONGO_URL=mongodb://mongo-stage:27017

# Client
API_BASE_URL=http://plm-tcin-mapper-api-stage:8080
```

### For PRODUCTION Environment

```bash
# API services
APP_ENV=production
LOG_LEVEL=INFO
GUNICORN_WORKERS=8
MONGO_URL=mongodb://mongo-prod:27017

# Client
API_BASE_URL=http://plm-tcin-mapper-api:8080
```

---

## Critical Configuration Points

### 🔴 API_BASE_URL (Client)

**Why critical:**
- Tells Streamlit UI where to find the API
- All 10 UI pages depend on this
- Wrong value = UI pages can't load data

**Correct value for TAP:**
```bash
API_BASE_URL=http://plm-tcin-mapper-api:8080
```

**How to verify:**
```bash
# From client pod
curl $API_BASE_URL/health
# Should return: {"status": "ok", ...}
```

### 🔴 Secrets Injection

**Required in TAP vault:**
```
plmtools/thinktank_api_key
plmtools/thinktank_gateway_api_key
plmtools/thinktank_oauth_client_id
plmtools/mongo_url (if auth required)
```

### 🟡 Health Checks

**API health endpoint:**
```bash
GET /health
```

**Client health endpoint:**
```bash
GET /_stcore/health
```

---

## What Each File Contains

### plm-think-tank-ai/.env.tap

```
✓ 7 KB of environment variables
✓ Production-ready defaults
✓ Gunicorn worker configuration
✓ MongoDB connection settings
✓ ThinkTank API credentials placeholder
✓ Detailed comments (120+ lines)
✓ TAP deployment notes
✓ Troubleshooting guide
```

**Use when:**
- Deploying Think Tank AI service to TAP
- Configuring the service for dev/staging/prod
- Scaling workers based on load

### plm-tcin-mapper-api/.env.tap

```
✓ 12 KB of environment variables
✓ Production-ready defaults
✓ Algorithm tuning parameters
✓ Ingestion batch size configuration
✓ Evaluation metric settings
✓ Gunicorn worker configuration
✓ Detailed comments (170+ lines)
✓ API endpoint reference
✓ Performance tuning guide
```

**Use when:**
- Deploying TCIN Mapper API to TAP
- Tuning algorithm thresholds
- Scaling for high load
- Optimizing batch processing

### plm-tcin-mapper-client/.env.tap

```
✓ 13 KB of environment variables
✓ Critical API_BASE_URL configuration
✓ Streamlit server settings
✓ Service discovery DNS names
✓ Detailed comments (200+ lines)
✓ Complete deployment walkthrough
✓ Dependency chain explanation
✓ Troubleshooting guide
```

**Use when:**
- Deploying Streamlit UI to TAP
- Configuring API connectivity
- Setting up service-to-service communication
- Debugging connection issues

### TAP_DEPLOYMENT_GUIDE.md

```
✓ 14 KB deployment guide
✓ Quick reference tables
✓ Environment values by stage
✓ Kubernetes YAML examples
✓ Secrets configuration
✓ Health check setup
✓ Scaling guidelines
✓ Monitoring examples
✓ Comprehensive troubleshooting
✓ Network diagram
```

**Use when:**
- Planning TAP deployment
- Configuring Kubernetes services
- Setting up secrets
- Monitoring deployed services
- Troubleshooting issues

---

## Complete File List

```
test-ai-app/
├── apps/
│   ├── plm-think-tank-ai/
│   │   └── .env.tap                  (7 KB)
│   ├── plm-tcin-mapper-api/
│   │   └── .env.tap                  (12 KB)
│   └── plm-tcin-mapper-client/
│       └── .env.tap                  (13 KB)
├── environment.md                    (18 KB - Complete reference)
└── TAP_DEPLOYMENT_GUIDE.md           (14 KB - Deployment guide)
```

---

## Next Steps

1. **Review the files**
   ```bash
   cd test-ai-app
   cat apps/plm-tcin-mapper-client/.env.tap  # Review critical API_BASE_URL
   cat TAP_DEPLOYMENT_GUIDE.md                # Review deployment approach
   ```

2. **Identify your secrets**
   - What is your THINKTANK_API_KEY?
   - What is your MongoDB URL?
   - Do you have OAuth credentials?

3. **Prepare TAP vault**
   - Store secrets in TAP vault
   - Map secret names to environment variable names

4. **Create TAP services**
   - Use YAML examples from `TAP_DEPLOYMENT_GUIDE.md`
   - Configure service DNS names
   - Set up health checks

5. **Deploy**
   - Use Vela pipeline (automatically builds Docker images)
   - TAP picks up images and creates deployments
   - Monitor with health endpoints

---

## Testing Before TAP

To test locally before deploying to TAP:

```bash
# Use the same environment variables
export $(cat apps/plm-tcin-mapper-api/.env.tap | grep -v '^#' | grep -v '^$')

# Run the service
python -m plm_tcin_mapper_api.main

# Verify health
curl http://localhost:8080/health
```

---

## File Summary

| File | Size | Purpose |
|------|------|---------|
| `plm-think-tank-ai/.env.tap` | 7 KB | Think Tank environment variables |
| `plm-tcin-mapper-api/.env.tap` | 12 KB | TCIN Mapper API environment variables |
| `plm-tcin-mapper-client/.env.tap` | 13 KB | Streamlit UI environment variables |
| `TAP_DEPLOYMENT_GUIDE.md` | 14 KB | Complete TAP deployment guide |
| `environment.md` | 18 KB | Complete environment variable reference |

**Total:** 64 KB of comprehensive TAP deployment documentation

---

## Key Takeaways

✅ Each `.env.tap` file is production-ready
✅ All critical variables are documented
✅ Secrets use TAP injection syntax
✅ Comments explain every variable
✅ Examples for dev/staging/prod included
✅ Troubleshooting guides provided
✅ Health check endpoints configured
✅ Service dependencies documented

**Ready for TAP deployment!** 🚀

---

**Created:** 2026-06-12
**Status:** ✅ Complete
