# Testing Guide - PLM TCIN Mapper Split

Complete guide to testing the API ↔ UI integration locally.

---

## Prerequisites

- Python 3.12
- `uv` package manager installed
- MongoDB running on `mongodb://localhost:27017`
- 2 terminal windows

---

## Quick Start (5 minutes)

### Terminal 1: Start API

```bash
cd C:\Saritha\Jun12\test-ai-app

# Install dependencies
uv sync --package plm-tcin-mapper-api

# Start API on port 8001
export APP_PORT=8001
uv run uvicorn plm_tcin_mapper_api.main:app --reload --port 8001
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete
```

**Test it:**
```bash
curl http://localhost:8001/health
# Returns JSON with status
```

---

### Terminal 2: Start Streamlit Client

```bash
cd C:\Saritha\Jun12\test-ai-app

# Install dependencies
uv sync --package plm-tcin-mapper-client

# Start UI on port 8080, pointing to API
export API_BASE_URL=http://localhost:8001
uv run streamlit run apps/plm-tcin-mapper-client/plm_tcin_mapper_client/streamlit_app.py --server.port 8080
```

**Expected Output:**
```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8080
  Network URL: http://192.168.x.x:8080
```

**Test it:**
```bash
curl http://localhost:8080/_stcore/health
# Returns 200 OK (Streamlit is responsive)
```

---

## Run Integration Tests

### Terminal 3: Run Test Suite

```bash
cd C:\Saritha\Jun12\test-ai-app

# Install httpx for tests
uv pip install httpx

# Run integration tests
python test_integration.py
```

**Expected Output:**
```
============================================================
                Testing API Health Endpoint
============================================================

✓ API health check passed
ℹ Response: {
    "status": "ok",
    "llm_provider": "thinktank",
    "llm_model": "gemini-1.5-pro",
    "mongo_ok": true
}

============================================================
              Testing Streamlit Client Health
============================================================

✓ Streamlit health check passed

============================================================
           Testing UI to API Communication
============================================================

✓ Admin stats endpoint works (UI can use this)
✓ Departments endpoint works (department_view.py will use this)
✓ Mappings query endpoint works (pid_lookup.py will use this)
✓ LLM quality endpoint works (llm_quality.py will use this)

============================================================
                     Test Summary
============================================================

Dockerfiles: PASS
API Health: PASS
API Endpoints: PASS
Client Health: PASS
UI-API Communication: PASS

Total: 5/5 test groups passed

🎉 All tests passed! UI ↔ API integration working perfectly!
```

---

## Test API Endpoints

### Get Admin Stats
```bash
curl http://localhost:8001/api/v1/admin/stats | jq
```

**Response:**
```json
{
  "mappings_count": 1234,
  "tcin_records_count": 5678,
  "variation_records_count": 9012,
  "feedback_count": 345,
  "eval_runs_count": 12,
  "llm_calls_count": 234,
  "correction_impacts_count": 56,
  "threshold_proposals_count": 3,
  "alias_proposals_count": 7
}
```

### Get Departments
```bash
curl http://localhost:8001/api/v1/departments | jq
```

**Response:**
```json
{
  "departments": ["dept-1", "dept-2", "dept-3"]
}
```

### Get Mappings
```bash
# Without filters
curl http://localhost:8001/api/v1/mappings?limit=5 | jq

# With PID filter
curl "http://localhost:8001/api/v1/mappings?pid=ABC123&limit=5" | jq

# With status filter
curl "http://localhost:8001/api/v1/mappings?status=MATCHED&limit=5" | jq
```

### Get Variations for a PID
```bash
curl "http://localhost:8001/api/v1/variations?pid=ABC123" | jq
```

---

## Test UI Pages

### Access Streamlit UI
Open browser: **`http://localhost:8080`**

### Test Each Page

All pages should load without errors and display data from the API:

1. **Search by PID** (default page)
   - Enter a PID in the search box
   - Should fetch variations from API
   - Should display mappings

2. **Department View**
   - Select a department from dropdown (populated via `/api/v1/departments`)
   - Should display department-level stats

3. **Review Queue**
   - Should display mappings with low confidence
   - Submit feedback via API

4. **Data Pipeline**
   - Ingest tab: calls `/api/v1/ingest`
   - Mapping tab: calls `/api/v1/mappings/run`

5. **Evaluation Metrics**
   - Calls `/api/v1/eval/detailed`
   - Shows eval results

6. **Threshold Optimizer**
   - Calls `/api/v1/threshold-tuning/*` endpoints

7. **Alias Mining Dashboard**
   - Calls `/api/v1/alias-mining/*` endpoints

8. **LLM Quality**
   - Calls `/api/v1/llm/quality`
   - Shows LLM metrics

9. **Improvement Tracker**
   - Calls `/api/v1/improvements`
   - Displays correction impacts

10. **System Admin**
    - Calls `/api/v1/admin/stats`
    - Shows system statistics

---

## Docker Testing

### Build Docker Images

```bash
# Build API
docker build -f apps/plm-tcin-mapper-api/Dockerfile -t plm-tcin-mapper-api:latest .

# Build Client
docker build -f apps/plm-tcin-mapper-client/Dockerfile -t plm-tcin-mapper-client:latest .

# Build Think Tank
docker build -f apps/plm-think-tank-ai/Dockerfile -t plm-think-tank-ai:latest .
```

### Run with Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_DATABASE: tcin_mapper
    volumes:
      - mongo_data:/data/db

  api:
    image: plm-tcin-mapper-api:latest
    ports:
      - "8001:8080"
    environment:
      APP_PORT: 8080
      MONGO_URL: mongodb://mongo:27017
    depends_on:
      - mongo

  client:
    image: plm-tcin-mapper-client:latest
    ports:
      - "8080:8080"
    environment:
      APP_PORT: 8080
      API_BASE_URL: http://api:8080
    depends_on:
      - api

volumes:
  mongo_data:
```

Run:
```bash
docker-compose up
```

Access:
- **UI:** http://localhost:8080
- **API:** http://localhost:8001
- **API Docs:** http://localhost:8001/docs

---

## Troubleshooting

### API won't start

```bash
# Check if port 8001 is in use
netstat -ano | findstr :8001

# Kill the process and retry
taskkill /PID <process_id> /F
```

### Streamlit won't start

```bash
# Check if port 8080 is in use
netstat -ano | findstr :8080

# Make sure API_BASE_URL is set
echo $env:API_BASE_URL  # Should show http://localhost:8001
```

### MongoDB connection failed

```bash
# Check if MongoDB is running
mongosh --eval "db.adminCommand('ping')"

# Expected output:
# { ok: 1 }
```

### API returns 503 (MongoDB Error)

- MongoDB is not accessible at the configured URL
- Check `MONGO_URL` environment variable
- Verify MongoDB is running

### UI shows "Connection Error"

- Check `API_BASE_URL` is set correctly
- Verify API is running on the specified port
- Check browser console for specific error

---

## Expected File Structure After Setup

```
test-ai-app/
├── apps/
│   ├── plm-think-tank-ai/
│   │   ├── Dockerfile              ✅ Individual Dockerfile
│   │   └── entrypoint.sh
│   ├── plm-tcin-mapper-api/
│   │   ├── Dockerfile              ✅ Individual Dockerfile
│   │   ├── entrypoint.sh
│   │   └── pyproject.toml
│   ├── plm-tcin-mapper-client/
│   │   ├── Dockerfile              ✅ Individual Dockerfile
│   │   ├── entrypoint.sh
│   │   ├── pyproject.toml
│   │   └── plm_tcin_mapper_client/
│   │       ├── api_client.py       ✅ HTTP wrapper
│   │       ├── enums.py            ✅ Shared enums
│   │       ├── pages/              ✅ All refactored to use API
│   │       └── streamlit_app.py
│   └── plm_tcin_mapper.deprecated/ ✅ Old monolith (kept for reference)
├── .vela.yml                        ✅ Updated with individual Dockerfiles
├── test_integration.py              ✅ Integration test suite
├── ARCHITECTURE.md                  ✅ Architecture guide
├── SPLIT_SUMMARY.md                 ✅ Completion summary
└── TESTING_GUIDE.md                 ✅ This file
```

---

## Success Checklist

- [ ] API starts on port 8001 with `uvicorn`
- [ ] Streamlit starts on port 8080
- [ ] `curl http://localhost:8001/health` returns JSON
- [ ] `curl http://localhost:8080/_stcore/health` returns 200
- [ ] All 5 test groups pass with `test_integration.py`
- [ ] Streamlit UI loads at `http://localhost:8080`
- [ ] Can see data in each UI page (populated from API)
- [ ] Docker images build without errors
- [ ] Docker compose stack runs successfully

---

## Next Steps

1. ✅ **Local Testing** — Follow this guide
2. ✅ **Integration Testing** — Run `test_integration.py`
3. ⏭️ **Docker Testing** — Build and run with Docker Compose
4. ⏭️ **CI/CD** — Push to repo, Vela builds images
5. ⏭️ **TAP Deployment** — Deploy via TAP pipelines
6. ⏭️ **Production** — Monitor health endpoints

---

## Need Help?

- Check logs: Look at stdout of API and Streamlit
- Test API directly: `curl http://localhost:8001/api/v1/admin/stats`
- Check network: Ensure services can reach each other
- Review ARCHITECTURE.md for detailed setup info
