# plm-tcin-mapper System Overview

> **A complete guide to understanding, operating, and improving the TCIN color-to-impression mapper**

---

## What This System Does

The `plm-tcin-mapper` takes two views of the same product (guest-facing TCIN colors and design-time impression names) and automatically maps them using a **deterministic + LLM matching engine**. Humans review low-confidence mappings, and the system tracks improvement metrics.

**Example:**
```
Guest-Facing (TCIN)          Design/Manufacturing
PID: 009E83                   PID: 009E83
TcinId: 94447439              ImpressionId: dd948247-...
Color: Red                    ImpressionName: ROMANTIC RUBY
colorName: Maroon       ←→     Size: 1X
Size: 1X                      

Mapping: "Maroon" → "ROMANTIC RUBY"
Confidence: 0.92 (HIGH tier) → AUTO_CONFIRM status
```

---

## System Components

### 1. API Layer (FastAPI, port 8001)

**Routes:**
- `POST /api/v1/ingest` — Load CSV data into MongoDB
- `POST /api/v1/mappings/run` — Run matching pipeline
- `GET /api/v1/mappings` — Query results
- `POST /api/v1/feedback` — Submit human review decision
- `POST /api/v1/eval/run` — Compute quality metrics
- `GET /api/v1/eval/latest` — Get last evaluation snapshot

**Start:**
```bash
make run-tcin-mapper  # or: uv run uvicorn plm_tcin_mapper.main:app --reload
```

### 2. Streamlit UI (optional, port 8501)

**Pages:**
- **PID Lookup** — Search a PID, review by color, CONFIRM/REJECT/CORRECT impressions
- **Department View** — Filter by department, bulk review statistics
- **LLM Quality** — (stub) Audit LLM call cost/latency/accuracy

**Start:**
```bash
make run-tcin-ui  # or: uv run --group ui streamlit run plm_tcin_mapper/ui/streamlit_app.py
```

### 3. Matching Engine (Pure Python)

**Three-round algorithm:**
1. **Greedy** — Lock high-confidence pairs first (score ≥ 0.85)
2. **Hungarian** — Solve remaining colors optimally (scipy.optimize)
3. **Fallback** — Catch stragglers with any positive score

**Scoring signals (priority order):**
1. **Token overlap** — "maroon" in "ROMANTIC MAROON" → 0.70-0.99
2. **Keyword base match** — both map to "red" → 0.88-0.92
3. **Fuzzy string** — Levenshtein + penalty → up to 0.82

**LLM fallback:**
- If color_confidence < 0.60 AND use_llm=true
- Call ThinkTank (gemini-1.5-pro) to pick from candidates
- Enrich mapping with LLM rationale

### 4. Data Storage (MongoDB)

**Collections:**
- `tcin_records` — Guest-facing TCIN color rows (50K-100K docs)
- `variation_records` — Design impression rows (30K-50K docs)
- `mappings` — Match results (one per TCIN) (50K-100K docs)
- `feedback` — Human review decisions (1K-10K docs)
- `eval_runs` — Quality snapshots (persisted on demand)

### 5. Configuration System (ai-core)

**Priority (lowest to highest):**
1. `config/base.yaml` — Committed defaults
2. `config/local.yaml` — Dev overrides (not committed)
3. `.env` — Secrets (Mongo URL, ThinkTank token)
4. `APP__*` env vars — Cloud overrides (TAP)

**Key sections:**
```yaml
matching:
  auto_confirm_threshold: 0.85     # Status AUTO_CONFIRM if ≥
  llm_fallback_threshold: 0.60     # Call LLM if <
  no_match_threshold: 0.75         # Status NO_MATCH if <

ingestion:
  batch_size: 500                  # MongoDB bulk write size
  data_dir: data/normalized        # CSV location

eval:
  min_high_confidence_pct: 0.40    # Alert if pct_high <
  max_low_confidence_pct: 0.20     # Alert if pct_low >
  review_queue_backlog_limit: 1000 # Alert if NEEDS_REVIEW >
  min_avg_confidence: 0.60         # Alert if avg <
```

---

## Data Flow: End-to-End

```
Week 1: Ingest Data
┌─────────────────────────────────────┐
│ CSV Files in data/normalized/       │
│ chunk_01/tcin.csv                  │
│ chunk_01/variation.csv             │
│ ... chunk_14 ...                   │
└─────────────────────────────────────┘
         ↓ POST /api/v1/ingest
    MongoDB: tcin_records, variation_records
         ↓ 50K TCIN + 30K variation records

Week 2: Run Matching
┌─────────────────────────────────────┐
│ POST /api/v1/mappings/run           │
│ {use_llm: true}                     │
└─────────────────────────────────────┘
  ├─ Load TCIN + variation records per PID
  ├─ Three-round deterministic matching
  ├─ LLM fallback for confidence < 0.60
  ├─ Assign status (AUTO_CONFIRM, NEEDS_REVIEW, ...)
  └─ MongoDB: 50K mappings
         ↓ 70% AUTO_CONFIRM, 27% NEEDS_REVIEW, 3% other

Week 3: Human Review (Optional)
┌─────────────────────────────────────┐
│ Streamlit UI / REST API             │
│ Review NEEDS_REVIEW mappings        │
│ CONFIRM / REJECT / CORRECT          │
└─────────────────────────────────────┘
         ↓ 1,200 mappings reviewed
    MongoDB: feedback (1,200 docs)
    MongoDB: mappings (status updated to CONFIRMED/REJECTED/CORRECTED)
         ↓ correction_rate = 25%

Week 4: Evaluation
┌─────────────────────────────────────┐
│ POST /api/v1/eval/run               │
│ Compute: pct_high, pct_low, etc.   │
│ Check 4 guardrails                  │
└─────────────────────────────────────┘
         ↓ MongoDB: eval_runs (1 doc)
    Output:
      pct_high: 68%
      correction_rate: 25%
      Alerts: REVIEW QUEUE BACKLOG (3,500 > 1,000)

Week 5+: Iterate (v2)
  ├─ Mine feedback for keyword improvements (Gap #2)
  ├─ Propose threshold changes (Gap #3)
  ├─ A/B test via shadow mode (Gap #7)
  └─ Promote best config to production
```

---

## How to Use This System

### Scenario 1: Ingest New Data

```bash
# 1. Place CSV files in data/normalized/chunk_01, chunk_02, etc.
ls data/normalized/chunk_01/
# → tcin.csv, variation.csv

# 2. Start API server
make run-tcin-mapper

# 3. Dry run (validate before writing)
curl -X POST http://localhost:8001/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# 4. Real ingest
curl -X POST http://localhost:8001/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{}'

# 5. Verify counts
mongo
  > use plm_tcin_mapper_dev
  > db.tcin_records.countDocuments({})
  > db.variation_records.countDocuments({})
```

### Scenario 2: Run Matching

```bash
# 1. Match all unmatched PIDs with LLM fallback
curl -X POST http://localhost:8001/api/v1/mappings/run \
  -H "Content-Type: application/json" \
  -d '{"use_llm": true}'

# 2. Response shows batch_id and status counts
# {
#   "batch_id": "batch_abc123...",
#   "total_pids": 5000,
#   "pids_matched": 4800,
#   "status_counts": {
#     "AUTO_CONFIRM": 3360,
#     "NEEDS_REVIEW": 1440,
#     ...
#   }
# }

# 3. View mappings
curl "http://localhost:8001/api/v1/mappings?status=NEEDS_REVIEW&page=1&page_size=20"
```

### Scenario 3: Review Mappings

**Via Streamlit UI:**
```bash
# 1. Start UI
make run-tcin-ui

# 2. Open http://localhost:8501
# 3. Go to "Search by PID"
# 4. Enter a PID (e.g., "009E83")
# 5. See all colors grouped
# 6. For each color:
#    • Click CONFIRM to accept
#    • Click CORRECT and select new impression
#    • Click REJECT to clear
# 7. Submit review
```

**Via REST API:**
```bash
curl -X POST http://localhost:8001/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "mapping_id": "550e8400-...",
    "pid": "009E83",
    "tcin_id": "94447439",
    "action": "CORRECT",
    "suggested_impression_name": "SOFT PINK",
    "reviewer": "alice@target.com"
  }'
```

### Scenario 4: Evaluate Quality

```bash
# 1. Run evaluation
curl -X POST http://localhost:8001/api/v1/eval/run

# 2. Response shows metrics & guardrail alerts
# {
#   "total_mappings": 13050,
#   "pct_high": 0.68,
#   "pct_low": 0.03,
#   "correction_rate": 0.25,
#   "guardrail_alerts": [
#     "REVIEW QUEUE BACKLOG: 3500 > 1000"
#   ]
# }

# 3. Get latest eval (don't re-run)
curl http://localhost:8001/api/v1/eval/latest
```

### Scenario 5: Test Config Changes (Shadow Mode)

```bash
# 1. Edit config/base.yaml
# matching:
#   auto_confirm_threshold: 0.88  # raised from 0.85

# 2. Run matching in shadow mode
curl -X POST http://localhost:8001/api/v1/mappings/run \
  -H "Content-Type: application/json" \
  -d '{
    "shadow": true,
    "batch_id": "test_threshold_0.88"
  }'

# 3. Compare results (v2 feature, not yet implemented)
# See IMPLEMENTATION_REVIEW.md Gap #7
```

---

## Key Workflows

### Fast Path: Pre-Review Summary

**Goal:** Get a quick sense of quality before investing in review

```
1. POST /api/v1/mappings/run {use_llm: false}  [deterministic only]
   ├─ Faster (no network calls)
   └─ No LLM cost

2. POST /api/v1/eval/run
   ├─ Reads auto_confirm_threshold defaults (0.85)
   └─ Suggests how many need review

3. If pct_high > 0.60 → quality looks good, invest in review
   If correction_rate < 0.20 → past corrections support this
   If review_queue < 1000 → can handle manual review
```

### Quality Feedback Loop

**Goal:** Improve algorithm accuracy over time

```
Week 1:
  POST /mappings/run {use_llm: true, batch_id: "prod_w1"}
  POST /eval/run

Week 2:
  Review 1,000 NEEDS_REVIEW mappings
  POST /feedback 1,000 times
  Correction rate = 25%

Week 3:
  Analyze feedback (v2 feature):
  - Which signals are failing?
  - Which keywords need tweaking?
  - Which thresholds are off?

Week 4:
  Propose changes:
  - New keyword: rose → pink (instead of rose → red)
  - New threshold: auto_confirm 0.85 → 0.88

Week 5:
  Shadow test:
  POST /mappings/run {shadow: true, batch_id: "rose_fix_v1"}
  Compare: new keywords vs prod
  Estimate: -8% review queue, correction_rate 25% → 20%

Week 6:
  Approve & promote:
  Update config/base.yaml
  Commit to main
  Measure: next batch should show improvement
```

---

## Monitoring Checklist

**Daily:**
- [ ] Check if any PIDs are errored out (pids_errored > 0)
- [ ] Monitor review queue (NEEDS_REVIEW count)

**Weekly:**
- [ ] Run `/api/v1/eval/run`
- [ ] Check guardrail alerts (any RED?)
- [ ] Scan feedback for patterns (same color corrected repeatedly?)

**Monthly:**
- [ ] Analyze correction_rate trend (improving?)
- [ ] Review LLM cost (if using paid provider)
- [ ] Assess human review capacity (keeping up?)

**Quarterly:**
- [ ] Plan v2 improvements (feedback loop features)
- [ ] Tune thresholds based on accumulated feedback

---

## Common Issues & Fixes

### Issue: NEEDS_REVIEW count is 5,000 (too high)

**Root Cause:** One of these:
1. Thresholds too strict (auto_confirm_threshold too high)
2. Scoring signals are weak (color keywords missing)
3. Review capacity is low (not enough humans)

**Fix:**
```
Option A: Lower auto_confirm_threshold
  config/base.yaml: auto_confirm_threshold: 0.80  (from 0.85)
  Rationale: More AUTO_CONFIRM, fewer manual reviews
  Risk: May auto-confirm wrong matches
  
Option B: Enable LLM for ambiguous cases
  POST /mappings/run {use_llm: true}
  Rationale: LLM picks best from candidates
  Risk: Cost, latency, hallucinations
  
Option C: Hire more reviewers
  Capacity planning
  
Option D: Improve keywords (v2)
  Analyze feedback → mine new keywords → test → promote
```

### Issue: Correction rate is 35% (too high)

**Root Cause:** Algorithm is frequently wrong. Likely:
1. Missing keywords (e.g., "dusty" not recognized as color modifier)
2. Thresholds too aggressive (auto_confirming low-quality matches)
3. Fuzzy signal dominating over better signals

**Fix:**
```
Step 1: Diagnose
  Analyze feedback: which CORRECTED mappings had confidence > 0.80?
  If many: thresholds are too loose

Step 2: Mine keywords (v2)
  Extract original_impression → suggested_impression
  Count failures: "ROMANTIC RUBY" → "SOFT PINK"
    Suggests: ruby is being over-weighted toward red
  Propose: ruby keyword adjustment

Step 3: Test & promote (v2)
  Shadow run with new keywords
  Compare: correction_rate should drop
```

### Issue: LLM calls are too expensive

**Problem:** Using LLM for every mapping < 0.60 confidence

**Fix:**
```
Option A: Raise llm_fallback_threshold
  0.60 → 0.70: fewer LLM calls, faster, cheaper
  Risk: miss ambiguous cases
  
Option B: Use cheaper LLM model
  gemini-1.5-pro → gemini-1.5-flash
  Fast config change (env var)
  
Option C: Improve deterministic scoring
  Better keywords → higher confidence → fewer LLM calls
  (Long-term, higher ROI)
```

---

## Performance Baselines

**Throughput:**

| Operation | Throughput | Time (5,000 PIDs) |
|-----------|-----------|------------------|
| Ingest (CSV → DB) | 3,000-5,000 rows/sec | 10-15 min |
| Match (deterministic) | 100-200 PIDs/sec | 25-50 sec |
| Match (with LLM) | 1-2 PIDs/sec | 40-80 min |
| Eval (aggregate) | 13K mappings/sec | <1 sec |

**Memory:** < 200MB for all operations

**Cost (if using ThinkTank/Gemini):**
- 1 LLM call ≈ $0.0001-0.001 (tokens-based)
- 1% of 50K mappings = 500 LLM calls ≈ $0.05-0.50

---

## Architecture Decisions

### Why Deterministic First, LLM Second?

**LLMs are:**
- Non-deterministic (different output each time)
- Slower (network latency)
- Expensive (token-based pricing)

**Deterministic engine is:**
- Instant (local computation)
- Cheap (zero cost)
- Predictable (same input → same output)

**Solution:** Use deterministic for 80% of cases, LLM only for ambiguous 20%.

### Why Three Rounds?

1. **Greedy (round 1):** Fast, handles obvious matches
2. **Hungarian (round 2):** Guarantees global optimality for hard cases
3. **Fallback (round 3):** Ensures complete assignment

**Trade-off:** Slight added complexity for significantly better results.

### Why Streamlit UI?

- Fast to develop (no frontend framework needed)
- Easy to iterate (reload page = code change)
- Tight integration with Python backend
- Internal-only tool (security not critical)

**Downside:** Can't deploy UI separately from server. *(Acceptable for v1.)*

---

## Roadmap: v2 Improvements

**See IMPLEMENTATION_REVIEW.md for full details.**

| Priority | Gap | Effort | Impact |
|----------|-----|--------|--------|
| 🔴 High | LLM call auditing | 2h | Unblock UI, cost tracking |
| 🔴 High | Feedback enrichment (API) | 2h | Consistent data capture |
| 🔴 High | UI auto-refresh | 1h | Better UX |
| 🟡 Medium | Alias mining | 12h | Data-driven keyword tuning |
| 🟡 Medium | Extended eval metrics | 8h | Diagnose weak signals |
| 🟢 Low | Threshold tuning | 16h | Automated config optimization |
| 🟢 Low | Shadow comparison | 6h | Safer config rollouts |

**Estimated v2 effort:** ~47 hours (1 sprint)

---

## Support & Questions

**For detailed processes:** See separate PROCESS_*.md documents
- `PROCESS_INGESTION.md` — CSV loading details
- `PROCESS_MATCHING.md` — Matching algorithm walkthrough
- `PROCESS_FEEDBACK_EVALUATION.md` — Review & metrics details

**For implementation gaps:** See `IMPLEMENTATION_REVIEW.md`
- Lists all 7 gaps with remediation plans
- Includes full code walkthroughs
- Provides deployment checklist

**For troubleshooting:**
1. Check logs: `docker logs plm-tcin-mapper`
2. Query MongoDB: `db.mappings.findOne({...})`
3. Run dry_run: `POST /ingest {dry_run: true}`

---

**Last Updated:** 2026-06-11  
**Status:** Production-ready v1, planned v2 features documented
