# Files Reference - Complete Map

Quick reference for all files created/modified in the split.

---

## 📁 New Dockerfiles (Individual Per App)

| File | Purpose |
|------|---------|
| `apps/plm-think-tank-ai/Dockerfile` | Build image for think-tank service |
| `apps/plm-tcin-mapper-api/Dockerfile` | Build image for API service |
| `apps/plm-tcin-mapper-client/Dockerfile` | Build image for Streamlit UI |

**Note:** Old parameterized `Dockerfile` and `Dockerfile.client` removed from root.

---

## 📁 API Service Files

### Core Application
| File | Purpose |
|------|---------|
| `apps/plm-tcin-mapper-api/pyproject.toml` | Dependencies, package metadata |
| `apps/plm-tcin-mapper-api/entrypoint.sh` | Gunicorn startup script |
| `apps/plm-tcin-mapper-api/plm_tcin_mapper_api/main.py` | FastAPI app factory |

### New API Endpoints
| File | Endpoints Added |
|------|-----------------|
| `apps/plm-tcin-mapper-api/plm_tcin_mapper_api/routes/variations.py` | `GET /api/v1/variations` |
| `apps/plm-tcin-mapper-api/plm_tcin_mapper_api/routes/departments.py` | `GET /api/v1/departments` |
| `apps/plm-tcin-mapper-api/plm_tcin_mapper_api/routes/llm_quality.py` | `GET /api/v1/llm/quality` |
| `apps/plm-tcin-mapper-api/plm_tcin_mapper_api/routes/improvements.py` | `GET/POST /api/v1/improvements` |
| `apps/plm-tcin-mapper-api/plm_tcin_mapper_api/routes/admin.py` | `GET /api/v1/admin/stats` |
| `apps/plm-tcin-mapper-api/plm_tcin_mapper_api/routes/mappings.py` | Extended with `/summary` and `/clear` |

### Core Modules (Copied & Updated Imports)
| Directory | Contents |
|-----------|----------|
| `plm_tcin_mapper_api/services/` | Business logic services |
| `plm_tcin_mapper_api/pipeline/` | Pipeline orchestration |
| `plm_tcin_mapper_api/matching/` | Matching algorithms |
| `plm_tcin_mapper_api/llm/` | LLM integration |
| `plm_tcin_mapper_api/database/` | Database models |
| `plm_tcin_mapper_api/models/` | API schemas |
| `plm_tcin_mapper_api/cli/` | CLI utilities |

---

## 📁 Client Service Files

### Core Application
| File | Purpose |
|------|---------|
| `apps/plm-tcin-mapper-client/pyproject.toml` | Dependencies, package metadata |
| `apps/plm-tcin-mapper-client/entrypoint.sh` | Streamlit startup script |
| `apps/plm-tcin-mapper-client/plm_tcin_mapper_client/main.py` | CLI entry point |

### NEW: HTTP API Wrapper
| File | Purpose |
|------|---------|
| `apps/plm-tcin-mapper-client/plm_tcin_mapper_client/api_client.py` | **NEW** — HTTP wrapper for all API calls (40+ functions) |
| `apps/plm-tcin-mapper-client/plm_tcin_mapper_client/enums.py` | **NEW** — Shared enums (FeedbackAction, MappingStatus) |

### Streamlit Pages (REFACTORED)
| File | API Endpoints Used |
|------|-------------------|
| `plm_tcin_mapper_client/pages/pid_lookup.py` | Mappings, Variations, Feedback, Clear mapping |
| `plm_tcin_mapper_client/pages/review_panel.py` | Mappings, Variations, Feedback |
| `plm_tcin_mapper_client/pages/department_view.py` | Departments, Mapping summary |
| `plm_tcin_mapper_client/pages/data_pipeline.py` | Ingest, Mappings run |
| `plm_tcin_mapper_client/pages/evaluation_metrics.py` | Eval detailed |
| `plm_tcin_mapper_client/pages/threshold_optimizer.py` | Threshold tuning endpoints |
| `plm_tcin_mapper_client/pages/alias_mining_dashboard.py` | Alias mining endpoints |
| `plm_tcin_mapper_client/pages/llm_quality.py` | LLM quality endpoint |
| `plm_tcin_mapper_client/pages/improvement_tracker.py` | Improvements endpoints |
| `plm_tcin_mapper_client/pages/admin.py` | Admin stats endpoint |

### Utilities
| File | Purpose |
|------|---------|
| `plm_tcin_mapper_client/streamlit_app.py` | Main Streamlit app + navigation |
| `plm_tcin_mapper_client/utils.py` | Helper functions (size_sort_key, confidence_badge) |

---

## 📁 Configuration & CI/CD

### Updated Files
| File | Changes |
|------|---------|
| `.vela.yml` | ✅ Updated all 15 build steps to use individual Dockerfiles |
| | ✅ Removed APP_PACKAGE build args |
| | ✅ Updated PR dry-run, docker-build, and tap-deploy stages |
| `pyproject.toml` | ✅ Updated UI dependency group comment |

---

## 📁 Testing & Documentation

### Testing Files
| File | Purpose |
|------|---------|
| `test_integration.py` | **NEW** — Comprehensive test suite |
| | - Verifies Dockerfiles exist |
| | - Tests API endpoints |
| | - Tests Streamlit health |
| | - Tests UI ↔ API communication |

### Documentation Files
| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | **NEW** — Complete technical guide (architecture, running locally, API reference) |
| `SPLIT_SUMMARY.md` | **NEW** — Implementation completion summary |
| `TESTING_GUIDE.md` | **NEW** — How to test locally (quick start, troubleshooting) |
| `IMPLEMENTATION_COMPLETE.md` | **NEW** — Verification checklist |
| `FILES_REFERENCE.md` | **THIS FILE** — Quick file reference |

---

## 📁 Archived/Deprecated

### Old Monolith (Kept for Reference)
| File | Status |
|------|--------|
| `apps/plm_tcin_mapper.deprecated/` | Archived (not used) |
| `plm_tcin_mapper.deprecated/` | Archived (root-level, kept for reference) |

---

## 🔄 Import Path Updates

All imports in API service updated:
```
plm_tcin_mapper.*  →  plm_tcin_mapper_api.*
```

This affected 30 files in the API service.

All imports in Client service:
```
plm_tcin_mapper.*  →  plm_tcin_mapper_client.*
plm_tcin_mapper.database.models  →  plm_tcin_mapper_client.enums
plm_tcin_mapper.ui.db  →  (removed, use api_client instead)
```

---

## 📊 Statistics

| Metric | Count |
|--------|-------|
| **New Dockerfiles Created** | 3 |
| **Old Dockerfiles Removed** | 2 |
| **New API Endpoints** | 7 |
| **Streamlit Pages Refactored** | 10 |
| **Import Path Updates** | 30 files |
| **New Modules Created** | 2 (api_client.py, enums.py) |
| **Configuration Files Updated** | 2 (.vela.yml, pyproject.toml) |
| **Test Scripts Created** | 1 (test_integration.py) |
| **Documentation Files Created** | 4 (plus this reference) |

---

## 🚀 Build Commands

### Build Docker Images
```bash
# Think Tank
docker build -f apps/plm-think-tank-ai/Dockerfile -t plm-think-tank-ai:latest .

# Mapper API
docker build -f apps/plm-tcin-mapper-api/Dockerfile -t plm-tcin-mapper-api:latest .

# Mapper Client
docker build -f apps/plm-tcin-mapper-client/Dockerfile -t plm-tcin-mapper-client:latest .
```

### Run Locally
```bash
# Terminal 1: API
export APP_PORT=8001
uv run uvicorn plm_tcin_mapper_api.main:app --reload --port 8001

# Terminal 2: Streamlit
export API_BASE_URL=http://localhost:8001
uv run streamlit run apps/plm-tcin-mapper-client/plm_tcin_mapper_client/streamlit_app.py

# Terminal 3: Tests
python test_integration.py
```

---

## 📖 Reading Order

Start with these files in this order:

1. **IMPLEMENTATION_COMPLETE.md** — See what was done
2. **TESTING_GUIDE.md** — Run tests locally
3. **ARCHITECTURE.md** — Understand the design
4. **FILES_REFERENCE.md** — This file (find specific files)

---

## ✅ Verification Checklist

Run this to verify everything is in place:

```bash
# Check Dockerfiles exist
ls -la apps/plm-think-tank-ai/Dockerfile
ls -la apps/plm-tcin-mapper-api/Dockerfile
ls -la apps/plm-tcin-mapper-client/Dockerfile

# Check new API endpoints exist
ls -la apps/plm-tcin-mapper-api/plm_tcin_mapper_api/routes/variations.py
ls -la apps/plm-tcin-mapper-api/plm_tcin_mapper_api/routes/departments.py
ls -la apps/plm-tcin-mapper-api/plm_tcin_mapper_api/routes/llm_quality.py
ls -la apps/plm-tcin-mapper-api/plm_tcin_mapper_api/routes/improvements.py
ls -la apps/plm-tcin-mapper-api/plm_tcin_mapper_api/routes/admin.py

# Check client files exist
ls -la apps/plm-tcin-mapper-client/plm_tcin_mapper_client/api_client.py
ls -la apps/plm-tcin-mapper-client/plm_tcin_mapper_client/enums.py

# Check test script
ls -la test_integration.py

# Check documentation
ls -la ARCHITECTURE.md
ls -la TESTING_GUIDE.md
ls -la SPLIT_SUMMARY.md
ls -la IMPLEMENTATION_COMPLETE.md

# Check old code is archived
ls -la apps/plm_tcin_mapper.deprecated/
```

All should exist! ✅

---

## 🎯 Quick Reference

### Ports
- **API:** 8001 (host) → 8080 (container)
- **UI:** 8080 (host) → 8080 (container)

### Health Endpoints
- **API:** `curl http://localhost:8001/health`
- **UI:** `curl http://localhost:8080/_stcore/health`

### Test Suite
- **Run:** `python test_integration.py`
- **Location:** `C:\Saritha\Jun12\test-ai-app\test_integration.py`

### Environment Variables
- **API:** `APP_PORT=8001`, `GUNICORN_WORKERS=4`
- **UI:** `API_BASE_URL=http://localhost:8001`, `APP_PORT=8080`

---

## 📞 Getting Help

| Question | Document |
|----------|----------|
| "How do I run this locally?" | TESTING_GUIDE.md |
| "What's the architecture?" | ARCHITECTURE.md |
| "What files were created?" | FILES_REFERENCE.md (this file) |
| "What was done?" | SPLIT_SUMMARY.md or IMPLEMENTATION_COMPLETE.md |
| "How do I test?" | test_integration.py or TESTING_GUIDE.md |

---

**Last Updated:** 2026-06-12
**Status:** ✅ Complete and ready for testing
