# 📚 PLM AI Apps — Complete Documentation Inventory

## ✅ What's Included

### 🎯 Getting Started (Start Here)

1. **[SETUP_AND_API_GUIDE.md](SETUP_AND_API_GUIDE.md)** ⭐ **START HERE**
   - Complete step-by-step from `git clone` to testing APIs
   - Covers both services (Think Tank + TCIN Mapper)
   - All curl examples and Insomnia usage instructions
   - Troubleshooting guide

2. **[README.md](README.md)**
   - Monorepo structure & dependency graph
   - Quick start (one-liners)
   - Available make commands
   - CI/CD overview

### 🛠️ Developer Guides

3. **[apps/plm-think-tank-ai/DEVELOPER_GUIDE.md](apps/plm-think-tank-ai/DEVELOPER_GUIDE.md)**
   - Full setup instructions for Think Tank service
   - Environment variables reference
   - Project layout & architecture
   - Adding new prompt operations
   - Docker & TAP deployment

4. **[apps/plm-tcin-mapper/DEVELOPER_GUIDE.md](apps/plm-tcin-mapper/DEVELOPER_GUIDE.md)**
   - Full setup instructions for TCIN Mapper service
   - MongoDB configuration
   - Matching algorithm explained (3-round deterministic + LLM fallback)
   - Data flow overview
   - Docker & TAP deployment

### 📖 Service READMEs

5. **[apps/plm-think-tank-ai/README.md](apps/plm-think-tank-ai/README.md)**
   - Endpoints overview
   - Request/response examples
   - Quick start

6. **[apps/plm-tcin-mapper/README.md](apps/plm-tcin-mapper/README.md)**
   - Endpoints overview
   - Data ingestion explained
   - Operator UI (Streamlit)
   - Configuration reference

### 🔧 Configuration Files

7. **[.env.example](.env.example)** — Root env (shared by both services)
   - ThinkTank credentials (OAuth or API key)
   - LLM provider settings
   - Server configuration

8. **[apps/plm-tcin-mapper/.env.example](apps/plm-tcin-mapper/.env.example)** — TCIN Mapper app-specific env
   - MongoDB URL & database name
   - Server port

9. **[apps/plm-tcin-mapper/.env.secrets](apps/plm-tcin-mapper/.env.secrets)** ⭐ **NEW: Simplified secrets template**
   - Minimal version with only essential fields
   - Clear comments for each section
   - Examples for different MongoDB setups

### 🧪 API Testing

10. **[insomnia-collection.json](insomnia-collection.json)** ⭐ **NEW: Ready-to-import collection**
    - All endpoints for both services
    - Pre-configured with environment variables
    - Example payloads for every request
    - Filter & query examples

### 📊 Architecture & Design

11. **[apps/plm-tcin-mapper/docs/ARCHITECTURE.md](apps/plm-tcin-mapper/docs/ARCHITECTURE.md)**
    - Deep dive into matching algorithm
    - Data model & schema
    - Deterministic + LLM disambiguation flow

12. **[apps/plm-tcin-mapper/docs/DATA_FLOW_DESIGN.md](apps/plm-tcin-mapper/docs/DATA_FLOW_DESIGN.md)**
    - End-to-end data flow
    - Ingestion pipeline
    - Feedback & evaluation loops

---

## 🎯 Quick Reference

### For Different Users

#### I want to get started quickly
→ Read **[SETUP_AND_API_GUIDE.md](SETUP_AND_API_GUIDE.md)** (this covers everything in 5 mins)

#### I just cloned the repo
→ Run these 3 commands:
```bash
cp .env.example .env                          # Fill in THINKTANK_API_KEY
make init
make run-plm
```

#### I want to test APIs
→ Open **insomnia-collection.json** in Insomnia, or use curl examples from **[SETUP_AND_API_GUIDE.md](SETUP_AND_API_GUIDE.md)**

#### I need to set up MongoDB for TCIN Mapper
→ Follow section **4. Start MongoDB** in **[SETUP_AND_API_GUIDE.md](SETUP_AND_API_GUIDE.md)**

#### I need to configure .env for TCIN Mapper
→ Use **[apps/plm-tcin-mapper/.env.secrets](apps/plm-tcin-mapper/.env.secrets)** as a template (simplified with comments)

#### I want to understand the matching algorithm
→ Read **[apps/plm-tcin-mapper/docs/ARCHITECTURE.md](apps/plm-tcin-mapper/docs/ARCHITECTURE.md)**

#### I want to understand the data model
→ Read **[apps/plm-tcin-mapper/docs/DATA_FLOW_DESIGN.md](apps/plm-tcin-mapper/docs/DATA_FLOW_DESIGN.md)**

#### I'm deploying to TAP/production
→ See **TAP deployment** sections in:
- [apps/plm-think-tank-ai/DEVELOPER_GUIDE.md](apps/plm-think-tank-ai/DEVELOPER_GUIDE.md#tap-deployment)
- [apps/plm-tcin-mapper/DEVELOPER_GUIDE.md](apps/plm-tcin-mapper/DEVELOPER_GUIDE.md#tap-deployment)

---

## 🔑 Key Information

### What is MongoDB for?

**MongoDB is ONLY required for plm-tcin-mapper.** It is NOT used by plm-think-tank-ai.

TCIN Mapper stores:
- **tcin_color_records** — guest-facing TCIN color variants
- **variation_records** — design impression names (from ingested CSVs)
- **mappings** — results of color → impression matching
- **feedback** — human corrections (CONFIRM / REJECT / CORRECT)
- **eval_snapshots** — accuracy metrics & guardrail alerts

### What are the 2 Services?

#### 1. plm-think-tank-ai (Port 8000)
- **Purpose:** Route PLM editor prompts to Claude/Gemini via ThinkTank gateway
- **Operations:** spell-check, unit-test generation
- **Data:** Stateless — no database
- **Credentials:** ThinkTank API key or OAuth
- **When to use:** Any prompt-based AI task

#### 2. plm-tcin-mapper (Port 8001)
- **Purpose:** Match design impression names to TCIN color records
- **Algorithm:** 3-round deterministic (greedy → Hungarian → fallback) + optional LLM disambiguation
- **Data:** Requires MongoDB for persistence
- **Credentials:** ThinkTank API key (optional, for LLM fallback)
- **When to use:** Matching product colors to design impressions; evaluation & feedback workflows

---

## 🚀 Common Workflows

### Workflow 1: Just Test the APIs

```bash
git clone ...
cd plm-ai-apps
cp .env.example .env                          # Set THINKTANK_API_KEY
make init
make run-plm
# Open insomnia-collection.json in Insomnia
# Click "Send" on any request
```

### Workflow 2: Full Stack with TCIN Mapper Data

```bash
git clone ...
cd plm-ai-apps

# Setup
cp .env.example .env                          # Set THINKTANK_API_KEY
cp apps/plm-tcin-mapper/.env.secrets apps/plm-tcin-mapper/.env
# Edit .env files as needed

# Start MongoDB
docker run -d --name tcin-mongo -p 27017:27017 mongo:7

# Install & start
make init
make run-plm

# In another terminal:
# Ingest data
curl -X POST http://localhost:8001/api/v1/ingest \
  -H "Content-Type: application/json" -d '{"chunk": "chunk_01"}'

# Run mappings
curl -X POST http://localhost:8001/api/v1/mappings/run \
  -H "Content-Type: application/json" -d '{"use_llm": true}'

# View results
curl http://localhost:8001/api/v1/mappings?page=1&page_size=50 | jq .

# Evaluate
curl http://localhost:8001/api/v1/eval/latest | jq .
```

### Workflow 3: Development & Testing

```bash
make test-unit       # Fast unit tests
make test-cov        # Full coverage report
make quality-gate    # lint + type-check + test (same as CI)
```

---

## 📝 Documentation Checklist

- [x] **README.md** — Monorepo overview, commands, quick start
- [x] **SETUP_AND_API_GUIDE.md** — Complete setup from clone to testing (NEW)
- [x] **apps/plm-think-tank-ai/README.md** — Service overview
- [x] **apps/plm-think-tank-ai/DEVELOPER_GUIDE.md** — Full dev setup & deployment
- [x] **apps/plm-tcin-mapper/README.md** — Service overview
- [x] **apps/plm-tcin-mapper/DEVELOPER_GUIDE.md** — Full dev setup & deployment
- [x] **apps/plm-tcin-mapper/docs/ARCHITECTURE.md** — Algorithm deep dive
- [x] **apps/plm-tcin-mapper/docs/DATA_FLOW_DESIGN.md** — Data model & flow
- [x] **.env.example** — Shared credentials template
- [x] **apps/plm-tcin-mapper/.env.example** — App-specific config
- [x] **apps/plm-tcin-mapper/.env.secrets** — Simplified secrets template (NEW)
- [x] **insomnia-collection.json** — Ready-to-import API collection (NEW)

---

## 🎁 What's New

### 1. SETUP_AND_API_GUIDE.md
- Single comprehensive guide covering BOTH services
- Step-by-step from `git clone` to testing
- All curl examples in one place
- Troubleshooting section
- Visual data flow diagrams

### 2. insomnia-collection.json
- Import-ready Insomnia collection
- All endpoints for both services
- Pre-configured environment variables
- Example payloads for every request
- One-click testing without typing curl

### 3. apps/plm-tcin-mapper/.env.secrets
- Simplified .env template (only secrets & essentials)
- Clear comments for MongoDB connection options
- MongoDB examples (local, auth, Atlas)
- Matches the user's original request: "fill in the secrets"

---

## 🔗 Navigation Map

```
README.md
├── SETUP_AND_API_GUIDE.md ⭐ Start here
│   ├── Quick Start
│   ├── Prerequisites
│   ├── Step-by-Step Setup
│   ├── Running Services
│   ├── Testing APIs (curl + Insomnia)
│   ├── Data Flow Explained
│   ├── Configuration Reference
│   ├── Troubleshooting
│   └── Full API Reference
│
├── apps/plm-think-tank-ai/
│   ├── README.md
│   ├── DEVELOPER_GUIDE.md
│   └── tests/
│
├── apps/plm-tcin-mapper/
│   ├── README.md
│   ├── DEVELOPER_GUIDE.md
│   ├── .env.secrets ⭐ Use for setup
│   ├── docs/
│   │   ├── ARCHITECTURE.md
│   │   └── DATA_FLOW_DESIGN.md
│   ├── data/normalized/ (CSV chunks)
│   ├── ui/ (Streamlit operator tool)
│   └── tests/
│
├── insomnia-collection.json ⭐ Import this
├── .env.example
└── Makefile
```

---

## ✨ Summary

You now have:

1. **Complete setup documentation** from clone to running both services
2. **Insomnia collection** for testing all APIs (no curl needed)
3. **Simplified .env template** for TCIN Mapper with clear secrets
4. **Clear separation:** MongoDB is documented as **TCIN Mapper only**, all other config is **shared**

All documentation is in place. You're ready to go! 🚀

---

For any questions, start with **[SETUP_AND_API_GUIDE.md](SETUP_AND_API_GUIDE.md)**.
