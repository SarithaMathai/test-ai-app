# Process: Human Feedback & Evaluation Loop

> **Purpose:** Collect human review decisions and compute quality metrics  
> **Entry Points:** Streamlit UI (pid_lookup page) + `POST /api/v1/feedback` + `POST /api/v1/eval/run`  
> **Core Logic:** `plm_tcin_mapper/services/feedback_service.py` + `plm_tcin_mapper/pipeline/evaluator.py`

---

## Part A: Feedback Collection Pipeline

### Data Flow Diagram

```
┌────────────────────────────────────────────────────────┐
│ Reviewer Action in Streamlit UI                        │
│ (plm_tcin_mapper/ui/pages/pid_lookup.py)              │
└────────────────────────────────────────────────────────┘
                            ↓
    Step 1: Load Mappings Needing Review
    ┌─────────────────────────────────────┐
    │ db.mappings.find({                  │
    │   status: {$in: [                   │
    │     NEEDS_REVIEW,                   │
    │     NEEDS_SPOT_CHECK,               │
    │     NO_MATCH                        │
    │   ]},                               │
    │   pid: (optional filter)            │
    │ })                                  │
    └─────────────────────────────────────┘
                            ↓
    Step 2: Group by Color
    ┌─────────────────────────────────────┐
    │ Streamlit displays:                 │
    │ • TCIN color / color_name           │
    │ • Current matched impression        │
    │ • Confidence badge + reason         │
    │ • Candidate alternatives            │
    │ • Size matching info                │
    └─────────────────────────────────────┘
                            ↓
    Step 3: Reviewer Decision
    ┌─────────────────────────────────────┐
    │ Three actions available:            │
    │                                     │
    │ ✅ CONFIRM                          │
    │    Accept current match             │
    │                                     │
    │ ❌ REJECT                           │
    │    Reject match (set to NO_MATCH)  │
    │                                     │
    │ ✏️  CORRECT                         │
    │    Enter different impression       │
    │    from dropdown list               │
    └─────────────────────────────────────┘
                            ↓
    Path A: CONFIRM
    ┌─────────────────────────────────────┐
    │ No changes to mapping               │
    │ Just record that human reviewed     │
    │ and approved the match              │
    └─────────────────────────────────────┘
                            ↓
    Path B: REJECT
    ┌─────────────────────────────────────┐
    │ Clear the impression:               │
    │ • matched_impression_name = null    │
    │ • matched_impression_id = null      │
    │ • status = NO_MATCH                 │
    └─────────────────────────────────────┘
                            ↓
    Path C: CORRECT
    ┌─────────────────────────────────────┐
    │ Reviewer selects new impression     │
    │ from variation_records dropdown     │
    │                                     │
    │ Steps:                              │
    │ 1. Fetch impression_id from         │
    │    db.variation_records             │
    │ 2. Create new mapping               │
    │ 3. Append FeedbackRecord            │
    │ 4. Update mapping status            │
    └─────────────────────────────────────┘
                            ↓
    ┌────────────────────────────────────────────┐
    │ Save Feedback (All Paths)                  │
    │ _save_pid_review_cb()                      │
    │ (pid_lookup.py:103-140)                    │
    └────────────────────────────────────────────┘
                            ↓
    For each changed color:
    ┌────────────────────────────────────────────┐
    │ 1. Extract current selection from          │
    │    st.session_state                        │
    │ 2. Compare to original value               │
    │ 3. If changed, take action:                │
    │    • CORRECT: call _save_correction()      │
    │    • REJECT:  call _clear_impression()     │
    └────────────────────────────────────────────┘
                            ↓
    ┌────────────────────────────────────────────┐
    │ _save_correction(mapping, new_impression) │
    │ (pid_lookup.py:26-64)                      │
    └────────────────────────────────────────────┘
                            ↓
    Create FeedbackRecord:
    ┌────────────────────────────────────────────┐
    │ FeedbackRecord(                            │
    │   mapping_id: str,                         │
    │   pid: str,                                │
    │   tcin_id: str,                            │
    │   action: FeedbackAction.CORRECT,          │
    │   reviewer: str (from session),            │
    │   notes: str (optional),                   │
    │                                            │
    │   tcin_color: str (captured),              │
    │   tcin_color_name: str (captured),         │
    │   tcin_size: str (captured),               │
    │   department_ids: [str],                   │
    │   match_round: str,                        │
    │   original_confidence_tier: str,           │
    │                                            │
    │   suggested_impression_id: str,            │
    │   suggested_impression_name: str,          │
    │   original_impression_name: str,           │
    │   original_color_confidence: float,        │
    │                                            │
    │   was_correct: bool (True if CONFIRM),     │
    │   created_at: datetime = now(UTC)          │
    │ )                                          │
    └────────────────────────────────────────────┘
                            ↓
    Write to MongoDB:
    ┌────────────────────────────────────────────┐
    │ db.feedback.insert_one(                    │
    │   feedback.model_dump(by_alias=True)       │
    │ )                                          │
    └────────────────────────────────────────────┘
                            ↓
    Update Mapping:
    ┌────────────────────────────────────────────┐
    │ db.mappings.update_one(                    │
    │   {_id: mapping_id},                       │
    │   {$set: {                                 │
    │     status: "CORRECTED",                   │
    │     matched_impression_name: new_name,     │
    │     matched_impression_id: new_id,         │
    │     updated_at: now(UTC)                   │
    │   }}                                       │
    │ )                                          │
    └────────────────────────────────────────────┘
                            ↓
    ┌────────────────────────────────────────────┐
    │ Streamlit UI:                              │
    │ • Close review form                        │
    │ • Show toast: "{saved} updated · {time}"   │
    │ • ⚠️ Page still shows old data              │
    │   (see Gap #6 in IMPLEMENTATION_REVIEW.md) │
    └────────────────────────────────────────────┘
```

### Feedback via REST API

**Endpoint:** `POST /api/v1/feedback`

**Request:**
```json
{
  "mapping_id": "550e8400-...",
  "pid": "009E83",
  "tcin_id": "94447439",
  "action": "CORRECT",
  "reviewer": "alice@target.com",
  "notes": "Maroon is more purple than red",
  "suggested_impression_id": "dd948247-...",
  "suggested_impression_name": "SOFT PINK"
}
```

**Process:**
```python
FeedbackService.submit(request)
├─ Create FeedbackRecord from request
├─ ⚠️ Gap #5: Missing context fields
│   (tcin_color, original_tier, etc.)
├─ Insert to db.feedback
├─ Update db.mappings status
└─ Return {status: "ok", feedback_id: str}
```

**Response:**
```json
{
  "status": "ok",
  "feedback_id": "660f9511-..."
}
```

### Feedback Record Schema

**Collection:** `feedback`

**Document Example:**
```javascript
{
  "_id": "660f9511-f40c-52e5-b827-557766551111",
  "mapping_id": "550e8400-e29b-41d4-a716-446655440000",
  "pid": "009E83",
  "tcin_id": "94447439",
  "action": "CORRECT",
  "reviewer": "alice@target.com",
  "notes": "Maroon is more purple than red",
  "tcin_color": "Red",
  "tcin_color_name": "Maroon",
  "tcin_size": "1X",
  "department_ids": ["Clothing"],
  "match_round": "GREEDY",
  "original_confidence_tier": "HIGH",
  "suggested_impression_id": "dd948247-...",
  "suggested_impression_name": "SOFT PINK",
  "original_impression_name": "ROMANTIC RUBY",
  "original_color_confidence": 0.92,
  "was_correct": false,
  "created_at": ISODate("2026-06-11T15:45:00.000Z")
}
```

**Field Descriptions:**

| Field | Type | Purpose |
|-------|------|---------|
| `action` | FeedbackAction | CONFIRM / REJECT / CORRECT |
| `was_correct` | bool | Derived: True if action == CONFIRM |
| `original_confidence_tier` | str | Used to diagnose: did HIGH tier get rejected? |
| `match_round` | str | Used to analyze: GREEDY worse than HUNGARIAN? |
| `original_color_confidence` | float | Track: which confidence ranges need improvement? |

---

## Part B: Evaluation Pipeline

### Data Flow Diagram

```
┌────────────────────────────────────────────────────────┐
│ Evaluation Trigger                                      │
│ POST /api/v1/eval/run                                  │
└────────────────────────────────────────────────────────┘
                            ↓
                    EvalService
                (routes/eval.py)
                            ↓
                  service.run_eval()
                   [async wrapper]
                            ↓
        run_in_executor(None, _run_eval_sync)
                            ↓
            evaluator.run_eval(db, cfg, persist=True)
            [sync function, aggregation-heavy]
                            ↓
    Step 1: Count Mappings
    ┌────────────────────────────┐
    │ total_mappings =           │
    │   db.mappings.count({})    │
    │                             │
    │ If total == 0:              │
    │   return empty EvalRun      │
    │   with alert                │
    └────────────────────────────┘
                            ↓
    Step 2: Aggregate by Status
    ┌────────────────────────────┐
    │ db.mappings.aggregate([    │
    │   {$group: {               │
    │     _id: "$status",        │
    │     count: {$sum: 1}       │
    │   }}                       │
    │ ])                         │
    │                             │
    │ Returns: {                  │
    │   AUTO_CONFIRM: 7200,       │
    │   NEEDS_REVIEW: 3500,       │
    │   LLM_ASSISTED: 1200,       │
    │   CONFIRMED: 250,           │
    │   REJECTED: 50,             │
    │   CORRECTED: 150,           │
    │   NO_MATCH: 200             │
    │ }                           │
    └────────────────────────────┘
                            ↓
    Step 3: Aggregate by Tier
    ┌────────────────────────────┐
    │ db.mappings.aggregate([    │
    │   {$group: {               │
    │     _id: "$confidence_tier",│
    │     count: {$sum: 1}       │
    │   }}                       │
    │ ])                         │
    │                             │
    │ Returns: {                  │
    │   HIGH: 8900,               │
    │ GOOD: 2500,                 │
    │   FAIR: 1200,               │
    │   LOW: 450                  │
    │ }                           │
    └────────────────────────────┘
                            ↓
    Step 4: Average Confidence
    ┌────────────────────────────┐
    │ db.mappings.aggregate([    │
    │   {$group: {               │
    │     _id: null,             │
    │     avg: {$avg: "$color_   │
    │       confidence"}         │
    │   }}                       │
    │ ])                         │
    │                             │
    │ avg_color_confidence = 0.76 │
    └────────────────────────────┘
                            ↓
    Step 5: Compute Percentages & Rates
    ┌────────────────────────────┐
    │ For each tier:              │
    │   pct = round(count/total)  │
    │                             │
    │ pct_high = 8900/13050 = 0.68│
    │ pct_good = 2500/13050 = 0.19│
    │ pct_fair = 1200/13050 = 0.09│
    │ pct_low = 450/13050 = 0.03  │
    │                             │
    │ human_reviewed =            │
    │   CONFIRMED + REJECTED +    │
    │   CORRECTED                 │
    │   = 250 + 50 + 150 = 450    │
    │                             │
    │ correction_rate =           │
    │   CORRECTED / human_reviewed│
    │   = 150 / 450 = 0.33        │
    └────────────────────────────┘
                            ↓
    Step 6: Check Guardrails
    ┌────────────────────────────────────────┐
    │ Guardrail 1: Low High-Confidence Rate  │
    │ if pct_high < min_high_confidence_pct  │
    │   (default: 0.40)                      │
    │   alert: "LOW HIGH-CONFIDENCE RATE:    │
    │           68% (threshold: 40%)"        │
    │   ❌ Fails? No (0.68 > 0.40)           │
    │                                         │
    │ Guardrail 2: High Low-Confidence Rate  │
    │ if pct_low > max_low_confidence_pct    │
    │   (default: 0.20)                      │
    │   alert: "HIGH LOW-CONFIDENCE RATE:    │
    │           3% (threshold: 20%)"         │
    │   ✅ Passes (0.03 < 0.20)              │
    │                                         │
    │ Guardrail 3: Review Queue Backlog      │
    │ if needs_review_count >                │
    │    review_queue_backlog_limit          │
    │    (default: 1000)                     │
    │   count = NEEDS_REVIEW = 3500          │
    │   alert: "REVIEW QUEUE BACKLOG:        │
    │           3500 mappings awaiting human │
    │           review."                     │
    │   ❌ Fails (3500 > 1000)                │
    │                                         │
    │ Guardrail 4: Low Average Confidence    │
    │ if avg_color_confidence <              │
    │    min_avg_confidence                  │
    │    (default: 0.60)                     │
    │   score = 0.76                         │
    │   ✅ Passes (0.76 > 0.60)              │
    └────────────────────────────────────────┘
                            ↓
    Step 7: Build EvalRun & Persist
    ┌────────────────────────────────┐
    │ EvalRun {                      │
    │   id: uuid4(),                 │
    │   total_mappings: 13050,       │
    │   by_status: {...},            │
    │   by_tier: {...},              │
    │   pct_high: 0.68,              │
    │   pct_good: 0.19,              │
    │   pct_fair: 0.09,              │
    │   pct_low: 0.03,               │
    │   pct_confirmed: 0.02,         │
    │   pct_rejected: 0.004,         │
    │   correction_rate: 0.33,       │
    │   avg_color_confidence: 0.76,  │
    │   guardrail_alerts: [          │
    │     "REVIEW QUEUE BACKLOG:..." │
    │   ],                           │
    │   created_at: now(UTC)         │
    │ }                              │
    │                                 │
    │ db.eval_runs.insert_one(run)   │
    └────────────────────────────────┘
                            ↓
                    EvalResponse
    {
      id: "660f9511-...",
      total_mappings: 13050,
      by_status: {AUTO_CONFIRM: 7200, ...},
      by_tier: {HIGH: 8900, ...},
      pct_high: 0.68,
      pct_good: 0.19,
      pct_fair: 0.09,
      pct_low: 0.03,
      avg_color_confidence: 0.76,
      correction_rate: 0.33,
      guardrail_alerts: ["REVIEW QUEUE BACKLOG..."]
    }
                            ↓
                        200 OK
```

---

## How Feedback Drives Improvements

### The Feedback-to-Improvement Cycle (v2 Blueprint)

**Week 1: Matching**
```
POST /mappings/run
→ 13,050 mappings created
  • AUTO_CONFIRM: 7,200 (70%)
  • NEEDS_REVIEW: 3,500 (27%)
  • NO_MATCH: 200 (2%)
```

**Week 2: Human Review**
```
Reviewers use Streamlit UI
→ 1,200 mappings reviewed
  • CONFIRMED: 850 (71%)
  • REJECTED: 50 (4%)
  • CORRECTED: 300 (25%)
→ Correction rate = 300 / 1,200 = 25%
```

**Week 3: Analysis (v2 feature)**
```
CorrectionAnalyzer service (Gap #2):
1. Load all CORRECTED feedback from past 7 days
2. For each correction:
   - Extract: original_impression → suggested_impression
   - Compare: original_confidence_tier
   - Mine keywords: what color patterns are mismatched?

Example findings:
  "DUSTY ROSE" is suggested when deterministic picks:
    → "ROMANTIC RUBY": 15 times (12% of ROSE corrections)
    → "BOLD RED": 8 times (6% of ROSE corrections)
  
  Hypothesis: ROSE is being mapped to reds too often
  
  Proposed fix: Add keyword alias
    rose → pink (instead of current: rose → red)
```

**Week 4: Threshold Tuning (v2 feature)**
```
ThresholdTuner service (Gap #3):
1. Read EvalRun: correction_rate = 0.25
2. Analyze: which confidence tiers get corrected?
   - HIGH (≥0.85): 5% correction rate
   - GOOD (≥0.70): 18% correction rate
   - FAIR (≥0.50): 40% correction rate
   - LOW (<0.50): 65% correction rate

3. Model impact:
   If we raise auto_confirm_threshold 0.85 → 0.88:
   → Move 2% of GOOD tier to NEEDS_REVIEW
   → Expected: reduce GOOD corrections by 5-10%
   → Cost: increase human review by ~500 mappings

4. Propose: "Try threshold 0.88 on shadow batch"
```

**Week 5: Shadow Testing (v2 feature)**
```
Shadow mode (Gap #7):
1. Config test: use new keywords + thresholds
2. Operator runs:
   POST /mappings/run {shadow: true, batch_id: "rose_fix_v1"}

3. ShadowComparison service:
   Compare against last prod batch (same PIDs):
   
   Metric              | Prod      | Shadow    | Δ
   ─────────────────────┼───────────┼───────────┼──────
   NEEDS_REVIEW count   | 3,500     | 3,200     | -8.6%
   avg_confidence       | 0.76      | 0.78      | +2.6%
   correction_rate*     | unknown   | 0.20      | ~-20%
   
   *estimated on historical data
   
4. Result: "New keywords improve confidence, reduce
           review queue. Recommend promoting to production."
```

**Week 6: Promotion**
```
After human approval:
1. Update config/base.yaml with new keywords
2. Commit to main
3. Next prod batch uses new config
4. Track: correction_rate trend (should decline)
```

### Key Insight: Feedback as Training Signal

**Deterministic only (current):**
```
TCIN "maroon" + keyword_map {maroon: red}
→ Score all impressions
→ Pick highest (e.g., "ROMANTIC RUBY" = red-based)
→ Mapping created

Human says: "No, should be SOFT PINK"
→ Feedback recorded, but algorithm unchanged
→ Next "maroon" repeats same mistake
```

**With feedback loop (v2):**
```
TCIN "maroon" + keyword_map {maroon: pink}  ← UPDATED
→ Score all impressions with new keywords
→ "SOFT PINK" now scores higher
→ Next "maroon" has better chances
→ correction_rate metric tells us if improvement worked
```

---

## Metrics: What They Mean

| Metric | Definition | Good Range | Interpretation |
|--------|-----------|------------|-----------------|
| **pct_high** | % of mappings with confidence ≥ 0.85 | >0.60 | Higher = more AUTO_CONFIRM, fewer reviews needed |
| **pct_low** | % of mappings with confidence < 0.50 | <0.10 | Lower = more confident algorithm |
| **avg_color_confidence** | Mean of all color_confidence scores | >0.70 | Higher = overall stronger signal |
| **correction_rate** | (# CORRECTED) / (# human-reviewed) | <0.20 | Lower = algorithm is accurate; fewer corrections |
| **pct_confirmed** | % of human-reviewed marked CONFIRMED | >0.70 | Higher = algorithm is correct |
| **review_queue** | # NEEDS_REVIEW unmapped | <1000 | Lower = humans can keep up |

**Example interpretation:**
```
Current State:
  pct_high = 0.68 ✅
  pct_low = 0.03 ✅
  correction_rate = 0.25 ⚠️ (should be <0.20)
  review_queue = 3,500 ❌ (should be <1,000)

Diagnosis:
  • High confidence tiers are good (68% HIGH)
  • Low confidence tiers are minimal (3% LOW)
  • But: 25% of reviewed were wrong → signal issues
  • And: Queue is backed up (3,500 awaiting review)

Action:
  • Improve matching signal (color keywords)
  • Increase review capacity or batch size
```

---

## Configuration Parameters

**Evaluation thresholds** (`config/base.yaml`):

```yaml
eval:
  # Minimum percentage of mappings that should be HIGH tier
  min_high_confidence_pct: 0.40
  
  # Maximum percentage that should be LOW tier
  max_low_confidence_pct: 0.20
  
  # If NEEDS_REVIEW count exceeds this, raise alert
  review_queue_backlog_limit: 1000
  
  # Minimum acceptable average color confidence
  min_avg_confidence: 0.60
```

**Tuning guidance:**
- Raise `min_high_confidence_pct` if algorithm is too conservative
- Lower `max_low_confidence_pct` if low-confidence mappings are getting rejected
- Raise `review_queue_backlog_limit` if human review capacity is low
- Lower `min_avg_confidence` if scoring is fundamentally weak

---

## Monitoring Dashboard (Recommended)

**Real-time metrics to track:**

```
Dashboard: Mapping Quality

Row 1: Status Snapshot
  [Total Mappings]  [AUTO_CONFIRM %]  [NEEDS_REVIEW count]
  13,050            70%               3,500

Row 2: Confidence Tiers
  [HIGH %]  [GOOD %]  [FAIR %]  [LOW %]
  68%       19%       9%        3%

Row 3: Feedback Impact
  [Human Reviewed]  [Correction Rate]  [Confirmed %]
  1,200             25%               71%

Row 4: Alerts
  ❌ REVIEW QUEUE BACKLOG: 3,500 > threshold 1,000
  ✅ Other thresholds OK
```

**Trend lines (week over week):**
- Correction rate (should ↓ as algorithm improves)
- Avg confidence (should ↑ as keywords improve)
- Review queue (should ↓ as humans catch up)
- LLM call cost (should ↓ as confidence improves)

---

## Next Steps

1. **Post-Matching:** Ensure all mappings written to `mappings` collection
2. **Human Review:** Use Streamlit UI (pid_lookup page) to review NEEDS_REVIEW
3. **Evaluation:** Run `POST /api/v1/eval/run` to snapshot quality metrics
4. **Monitor:** Check guardrail alerts; if any fail, diagnose and iterate
5. **v2 Planning:** Use feedback data to drive improvements (alias mining, threshold tuning)
