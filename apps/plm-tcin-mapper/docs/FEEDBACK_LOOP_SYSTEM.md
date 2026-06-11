# Feedback Loop System — From Human Feedback to Automated Improvements

> **Complete walkthrough of how feedback drives continuous improvement**
>
> Date: 2026-06-11  
> Version: 2.0 — Complete feedback loop with Gaps #2, #3, #7 implemented

---

## Table of Contents

1. [Overview & Architecture](#overview--architecture)
2. [Phase 1: Feedback Collection](#phase-1-feedback-collection)
3. [Phase 2: Feedback Analysis (Gap #2 — Alias Mining)](#phase-2-feedback-analysis-gap-2--alias-mining)
4. [Phase 3: Improvement Proposal (Gap #3 — Threshold Tuning)](#phase-3-improvement-proposal-gap-3--threshold-tuning)
5. [Phase 4: Validation (Gap #7 — Shadow Testing)](#phase-4-validation-gap-7--shadow-testing)
6. [Phase 5: Deployment](#phase-5-deployment)
7. [Complete End-to-End Example](#complete-end-to-end-example)
8. [Operational Workflows](#operational-workflows)

---

## Overview & Architecture

### The Closed-Loop System

```
┌─────────────────────────────────────────────────────────────┐
│                    FEEDBACK LOOP SYSTEM                      │
│                                                              │
│  Week 1: Production matching                                │
│    ↓                                                         │
│  Week 2: Human review & feedback collection                 │
│    ↓ (Gap #1: LLM auditing)                                │
│  Week 3: Feedback analysis                                  │
│    ↓ (Gap #2: Alias mining)                                │
│  Week 4: Proposal generation                                │
│    ↓ (Gap #3: Threshold tuning)                            │
│  Week 5: Shadow testing & validation                        │
│    ↓ (Gap #4: Extended evaluation)                         │
│    ↓ (Gap #7: Shadow comparison)                           │
│  Week 6: Deploy improvements                                │
│    ↓                                                         │
│  Week 7: Measure impact                                     │
│    ↓                                                         │
│  [Loop back to Week 1]                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Data Structures

**FeedbackRecord** (stored after human review):
```python
{
  "_id": "uuid",
  "mapping_id": "uuid",              # ← Which mapping is this feedback about?
  "pid": "F123456",
  "tcin_id": "50123456",
  "action": "CORRECT",               # ← What did reviewer do?
  "reviewer": "alice@target.com",
  "notes": "Impression name was too dark",
  
  # Context enriched from mapping
  "tcin_color_name": "Maroon",
  "original_impression_name": "RUBY RED",  # ← Original algorithm pick
  "suggested_impression_name": "BURGUNDY",  # ← What reviewer suggested
  "original_confidence_tier": "HIGH",
  "original_color_confidence": 0.88,
  "match_round": "HUNGARIAN",
  
  "created_at": "2026-06-10T14:30:00Z"
}
```

---

## Phase 1: Feedback Collection

### How Feedback Gets Created

**Two paths:**

**Path A: Via Streamlit UI (most common)**
```
1. Reviewer opens Streamlit → "Search by PID"
2. Enters PID "F123456"
3. Sees all colors grouped with current matches
4. For color "Maroon":
     Current: "RUBY RED" (confidence: 0.88)
     Candidates: ["RUBY RED", "BURGUNDY", "DARK CRIMSON"]
5. Reviewer clicks CORRECT
6. Selects "BURGUNDY" from dropdown
7. Clicks "Submit Review"
     ↓
   POST /api/v1/feedback {
     mapping_id: "uuid",
     action: "CORRECT",
     suggested_impression_name: "BURGUNDY",
     reviewer: "alice@target.com"
   }
     ↓
   Feedback record created + mapping status updated to CORRECTED
     ↓
   st.rerun() reloads page with fresh data (Gap #6)
```

**Path B: Via REST API**
```
curl -X POST http://localhost:8001/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "mapping_id": "uuid",
    "pid": "F123456",
    "tcin_id": "50123456",
    "action": "CORRECT",
    "suggested_impression_name": "BURGUNDY",
    "reviewer": "external-system"
  }'
```

### Feedback Actions

| Action | Meaning | Example | Impact |
|--------|---------|---------|--------|
| **CONFIRM** | Reviewer agrees with algorithm | User clicks ✓ | Validates algorithm (correction_rate—) |
| **CORRECT** | Reviewer disagrees, picks different | User selects BURGUNDY instead | Shows algorithm was wrong (correction_rate++) |
| **REJECT** | Reviewer clears the mapping | User clicks REJECT | Mapping set to NO_MATCH, needs manual resolution |

### Feedback Context Enrichment (Gap #5)

When feedback is submitted via REST API, the service enriches it with context from the mapping:

```python
# REST API request (minimal)
POST /api/v1/feedback {
  "mapping_id": "uuid",
  "pid": "F123456",
  "action": "CORRECT",
  "suggested_impression_name": "BURGUNDY"
}

# Service enriches with mapping context
mapping = db.mappings.find_one({"_id": request.mapping_id})

# FeedbackRecord saved (with enriched context)
{
  "mapping_id": "uuid",
  "action": "CORRECT",
  "suggested_impression_name": "BURGUNDY",
  
  # Enriched from mapping
  "tcin_color_name": mapping.get("tcin_color_name"),  # "Maroon"
  "original_impression_name": mapping.get("matched_impression_name"),  # "RUBY RED"
  "original_confidence_tier": mapping.get("confidence_tier"),  # "HIGH"
  "original_color_confidence": mapping.get("color_confidence"),  # 0.88
  "match_round": mapping.get("match_round"),  # "HUNGARIAN"
  ...
}
```

**Why:** Without context, REST API feedback is just "user said no to X". With context, we can analyze *why* the algorithm was wrong.

---

## Phase 2: Feedback Analysis (Gap #2 — Alias Mining)

### Goal

Extract **pattern-based keyword suggestions** from CORRECT feedback.

### What Gets Analyzed

From all CORRECT feedback records, we extract:
1. **Original impression name** (what algorithm picked)
2. **Suggested impression name** (what reviewer picked)
3. **Color keywords** in each

### Example: Single Correction

```
Feedback:
  Original:  "RUBY RED"      → Tokens: ["ruby", "red"]
  Suggested: "BURGUNDY"      → Tokens: ["burgundy"]
  
  Keyword mapping:
    "ruby"    → red color family
    "red"     → red color family
    "burgundy" → ??? (needs mapping)

Analysis:
  Problem: Reviewers chose "BURGUNDY" (which we don't recognize)
           when algorithm picked "RUBY RED"
  
  → Keyword "burgundy" should be added to color keywords
     and mapped to red (or dark_red, or maroon family)
```

### Extracting Patterns Across Feedback

```
Feedback records (20 corrections involving "rose"):

1. "ROMANTIC ROSE" → "PALE PINK"    (rose → pink, not red)
2. "WILD ROSE" → "MAUVE PINK"       (rose → pink, not red)
3. "ROSE GARDEN" → "DUSTY MAUVE"    (rose → purple-pink, not red)
4. "RUBY ROSE" → "CHERRY RED"       (rose stays in red family)
5. ... 16 more similar patterns

Summary:
  • "rose" keyword currently maps to: red
  • But reviewers chose pink/mauve 19 times
  • And chose red only 1 time
  
  → Proposal: Move "rose" keyword from red → pink
```

### How Alias Mining Works

**Endpoint:** `POST /api/v1/alias-mining/analyze`

```python
Request:
{
  "min_frequency": 3,        # ← Only suggest if ≥3 corrections
  "min_confidence": 0.60,    # ← Only if ≥60% confidence
  "limit": 10                # ← Top 10 proposals
}

Processing:
1. Query all CORRECT feedback records
2. For each: extract tokens from original vs suggested
3. Build frequency table:
     {
       "rose": {
         "original_color": "red",
         "correction_frequency": 19,
         "target_colors": {
           "pink": 12,        # ← 12 corrections preferred pink
           "mauve": 6,        # ← 6 corrections preferred mauve
           "red": 1           # ← 1 correction stayed with red
         },
         "correction_confidence": 19/20 = 0.95
       },
       ...
     }
4. Generate proposals:
     {
       "proposal_type": "ALIAS_MOVE",
       "base_color": "red",
       "keyword": "rose",
       "suggested_base_color": "pink",
       "frequency": 19,
       "confidence": 0.95,
       "rationale": "Keyword 'rose' currently maps to red but appears in 19 corrections where reviewers prefer pink. Correction rate: 95%."
     }

Response:
{
  "status": "ok",
  "proposals_generated": 7,
  "total_feedback_analyzed": 342,
  "proposals": [
    {proposal 1},
    {proposal 2},
    ...
  ]
}
```

### Proposal Storage

All proposals are stored in `alias_mining_proposals` collection:

```python
{
  "_id": "uuid",
  "proposal_type": "ALIAS_MOVE",
  "status": "PENDING",              # ← Awaiting human review
  "base_color": "red",
  "keyword": "rose",
  "suggested_base_color": "pink",
  "frequency": 19,
  "confidence": 0.95,
  "supporting_feedback_ids": ["uuid1", "uuid2", ...],
  "rationale": "...",
  "estimated_impact": "With this change, ~45 mappings may improve...",
  "created_at": "2026-06-10T..."
}
```

### Approval Workflow

**UI:** Admin → Alias Mining Dashboard

```
1. See all PENDING proposals
2. For each proposal:
     • Review rationale
     • See supporting feedback records
     • Estimate impact
3. Click APPROVE or REJECT
4. If APPROVE: status → APPROVED (ready for shadow testing)
5. If REJECT: status → REJECTED (archived)
```

---

## Phase 3: Improvement Proposal (Gap #3 — Threshold Tuning)

### Goal

Analyze evaluation metrics and propose **config parameter adjustments** to improve quality.

### What Gets Analyzed

From latest extended evaluation, analyze:
1. **Correction rate** — Are we wrong too often?
2. **Per-signal accuracy** — Which signals are weak?
3. **Confidence calibration** — Can we trust confidence scores?
4. **High-confidence mistakes** — Are we over-confident?
5. **LLM impact** — Is LLM helping or hurting?

### Example: High Correction Rate

```
Extended eval shows:
  correction_rate: 0.32      (32%, above 25% target)
  
  Diagnosis:
    pct_high: 0.58           (below 40% target)
    per_signal[fuzzy]: 0.48  (fuzzy is very weak)
  
Proposal:
  Lower auto_confirm_threshold from 0.85 → 0.82
  
  Rationale:
    "With correction_rate at 32%, raising confidence threshold
     will push more mappings to NEEDS_REVIEW. Human review
     will catch mistakes before they reach users."
  
  Impact estimate:
    • Mappings moving to NEEDS_REVIEW: ~8% (4,000 of 50K)
    • Estimated correction_rate improvement: 32% → 27% (5% better)
    • Confidence: 0.72 (medium confidence)
```

### How Threshold Tuning Works

**Endpoint:** `POST /api/v1/threshold-tuning/analyze`

```python
Processing:
1. Query latest extended_eval_run
2. Run 5 decision trees:
   
   IF correction_rate > 0.30:
     → Propose: Lower auto_confirm_threshold
   
   IF pct_high < 0.35:
     → Propose: Raise llm_fallback_threshold
   
   IF llm_impact.llm_correction_rate > 0.20:
     → Propose: Adjust llm_fallback_threshold higher
   
   IF per_signal[fuzzy].correction_rate > 0.40:
     → Propose: Reduce fuzzy signal weight
   
   IF confidence_calibration_error > 0.15:
     → Propose: Recalibrate confidence formula

3. For each proposal, simulate impact:
   
   "If we lower auto_confirm from 0.85 → 0.82:
     • ~4,000 more mappings go to NEEDS_REVIEW
     • Assuming 25% of those are actual errors caught:
       → 1,000 additional errors caught
       → Correction rate improves: 32% → 28% (4% better)"

4. Generate proposals with confidence scores
```

### Proposal Storage

```python
{
  "_id": "uuid",
  "status": "PENDING",
  "eval_run_id": "uuid",
  "proposal_type": "Lower auto_confirm threshold",
  "rationale": "Correction rate is 32%, above 25% target...",
  "changes": [
    {
      "parameter": "matching.auto_confirm_threshold",
      "current_value": 0.85,
      "proposed_value": 0.82,
      "delta": -0.03
    }
  ],
  "estimated_impact": [
    {
      "metric": "correction_rate",
      "current_value": 0.32,
      "estimated_value": 0.28,
      "improvement": -0.04
    },
    {
      "metric": "pct_high",
      "current_value": 0.58,
      "estimated_value": 0.52,
      "improvement": -0.06
    }
  ],
  "confidence": 0.72,
  "supporting_metrics": {...},
  "test_batch_id": null,
  "created_at": "2026-06-10T..."
}
```

### Approval Workflow

**UI:** Admin → Threshold Optimizer

```
1. See all PENDING proposals
2. For each:
     • Review rationale & estimated impact
     • Decide: APPROVE (for testing) or REJECT
3. If APPROVE:
     • Status → APPROVED
     • Automatically stages change in config
     • Awaiting shadow test (Phase 4)
4. If REJECT:
     • Status → REJECTED (archived)
```

---

## Phase 4: Validation (Gap #7 — Shadow Testing)

### Goal

**Test proposed improvements on a sample batch before deploying to production.**

### Shadow Testing Workflow

```
Step 1: Prepare baseline batch
  POST /api/v1/mappings/run {
    batch_id: "prod_baseline_week42"
    use_llm: true
  }
  
  Result: 50,000 mappings with current config
  Metrics: correction_rate=32%, pct_high=58%, ...

Step 2: Prepare shadow batch with proposed changes
  
  # Temporarily update config with proposed changes
  (In-memory or temporary config override)
  
  POST /api/v1/mappings/run {
    batch_id: "shadow_proposal_v1",
    shadow: true,     # ← Shadow mode: don't persist to production
    use_llm: true
  }
  
  Result: 50,000 mappings with PROPOSED config
  Metrics: correction_rate=28%, pct_high=52%, ...

Step 3: Compare results
  POST /api/v1/shadow-compare {
    baseline_batch_id: "prod_baseline_week42",
    shadow_batch_id: "shadow_proposal_v1"
  }
  
  Processing:
    1. Compute metrics for baseline batch
    2. Compute metrics for shadow batch
    3. Calculate deltas for each metric
    4. Run statistical significance test (t-test, p-value)
    5. Generate recommendation
```

### Comparison Results

```python
{
  "baseline_batch_id": "prod_baseline_week42",
  "shadow_batch_id": "shadow_proposal_v1",
  "total_baseline_mappings": 50000,
  "total_shadow_mappings": 50000,
  
  "metric_comparisons": [
    {
      "metric": "avg_confidence",
      "baseline_value": 0.78,
      "shadow_value": 0.76,
      "delta": -0.02,
      "pct_change": -2.6%,
      "is_improvement": false      # ← Confidence slightly lower
    },
    {
      "metric": "correction_rate",
      "baseline_value": 0.32,
      "shadow_value": 0.28,
      "delta": -0.04,
      "pct_change": -12.5%,
      "is_improvement": true       # ← Correction rate improved!
    },
    {
      "metric": "pct_high",
      "baseline_value": 0.58,
      "shadow_value": 0.52,
      "delta": -0.06,
      "pct_change": -10.3%,
      "is_improvement": false      # ← Fewer high-confidence
    },
    ...
  ],
  
  "overall_improvement_score": 0.67,  # ← 67% likely to be better
  "p_value": 0.002,                   # ← Statistically significant (< 0.05)
  "is_statistically_significant": true,
  
  "recommendation": "APPROVE"          # ← Safe to deploy
}
```

### Decision Logic

| p_value | Improvement Score | Recommendation |
|---------|-------------------|-----------------|
| < 0.05 | > 0.60 | ✅ APPROVE (significant & beneficial) |
| < 0.05 | 0.40–0.60 | ⚠️ REVIEW (significant but mixed) |
| < 0.05 | < 0.40 | ❌ REJECT (significant but harmful) |
| ≥ 0.05 | any | ❓ INCONCLUSIVE (not statistically significant) |

### Shadow Comparison Storage

```python
{
  "_id": "uuid",
  "baseline_batch_id": "prod_baseline_week42",
  "shadow_batch_id": "shadow_proposal_v1",
  "total_baseline_mappings": 50000,
  "total_shadow_mappings": 50000,
  
  "metric_comparisons": [...],
  
  "confidence_improvement": -0.02,
  "correction_rate_improvement": -0.04,  # ← Negative is GOOD
  "pct_high_improvement": -0.06,
  
  "overall_improvement_score": 0.67,
  "p_value": 0.002,
  "is_statistically_significant": true,
  "recommendation": "APPROVE",
  
  "created_at": "2026-06-11T..."
}
```

---

## Phase 5: Deployment

### Applying Approved Changes

**After shadow testing shows positive results:**

```
1. Review shadow comparison recommendation
2. If APPROVE:
     Click "Deploy Changes" in UI
3. Service:
     a. Update config/base.yaml with approved proposals
     b. Update alias_overrides.yaml with approved aliases
     c. Update proposal status → APPLIED
     d. Create git commit with changes
     e. Optionally: trigger CI/CD pipeline
4. Next batch uses new config automatically
```

### What Gets Updated

**For Alias Mining proposals:**
```yaml
# Before
color_keywords:
  rose: red
  ruby: red
  pink: pink

# After
color_keywords:
  rose: pink           # ← Changed per proposal
  ruby: red
  pink: pink
  burgundy: dark_red   # ← Added per proposal
```

**For Threshold Tuning proposals:**
```yaml
# Before
matching:
  auto_confirm_threshold: 0.85
  llm_fallback_threshold: 0.60

# After
matching:
  auto_confirm_threshold: 0.82   # ← Changed per proposal
  llm_fallback_threshold: 0.65   # ← Changed per proposal
```

---

## Complete End-to-End Example

### The Scenario

It's Monday morning. The merchandising team ran an evaluation Friday and found:
- Correction rate: 32% (target: < 25%)
- Home textiles department: 38% correction rate (highest)
- Keyword "rose" appears in 19 corrections where pink was preferred

### Week 1: Feedback Analysis

```bash
# Monday: Analyze feedback collected last week
curl -X POST http://localhost:8001/api/v1/alias-mining/analyze \
  -H "Content-Type: application/json" \
  -d '{"min_frequency": 3, "min_confidence": 0.60}'

# Response shows 7 proposals
# Top proposal: Move "rose" keyword from red → pink (confidence: 95%)

# UI: Analyst reviews proposals, approves top 3
# Status: PENDING → APPROVED (ready for validation)
```

### Week 2: Improvement Analysis

```bash
# Wednesday: Generate improvement proposals from eval metrics
curl -X POST http://localhost:8001/api/v1/threshold-tuning/analyze

# Response shows 3 proposals:
# 1. Lower auto_confirm_threshold 0.85 → 0.82
# 2. Raise llm_fallback_threshold 0.60 → 0.65
# 3. Reduce fuzzy_match weight (internal)

# UI: Analyst reviews, approves proposal #1 for validation
# Status: PENDING → APPROVED
```

### Week 3: Shadow Testing

```bash
# Friday: Run baseline batch
curl -X POST http://localhost:8001/api/v1/mappings/run \
  -H "Content-Type: application/json" \
  -d '{"batch_id": "week43_baseline", "use_llm": true}'

# Result: 50,000 mappings
# Eval: correction_rate = 32%, pct_high = 58%

# Run shadow batch with approved alias changes + threshold changes
curl -X POST http://localhost:8001/api/v1/mappings/run \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "week43_shadow_v1",
    "shadow": true,
    "use_llm": true,
    "apply_proposals": ["alias_rose_to_pink", "lower_threshold"]
  }'

# Result: 50,000 mappings with new config
# Eval: correction_rate = 28%, pct_high = 54%

# Compare results
curl -X POST http://localhost:8001/api/v1/shadow-compare \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_batch_id": "week43_baseline",
    "shadow_batch_id": "week43_shadow_v1"
  }'

# Response:
# {
#   "p_value": 0.003,
#   "is_statistically_significant": true,
#   "overall_improvement_score": 0.72,
#   "recommendation": "APPROVE"
# }
```

### Week 4: Deployment

```bash
# Monday: Analyst reviews shadow comparison
# Sees: correction_rate improved 32% → 28% (✓)
#       p-value: 0.003 (✓ significant)
#       recommendation: APPROVE (✓)

# Click "Deploy" in UI

# Service updates:
#   • config/base.yaml (threshold changes)
#   • alias_overrides.yaml (keyword changes)
#   • Proposal status: APPROVED → APPLIED

# Next production batch automatically uses new config
```

### Week 5: Validation

```bash
# Run evaluation on new production batch
curl -X POST http://localhost:8001/api/v1/eval/detailed

# Actual results:
{
  "correction_rate": 0.27,        # ← Improved from 32%!
  "pct_high": 0.55,               # ← Slightly lower (expected)
  "per_signal[fuzzy]": 0.45,      # ← Better (was 0.48)
  "per_department[home_textiles]": 0.33,  # ← Better (was 0.38)
  "guardrail_alerts": []          # ← No alerts! (was 2)
}

# Success! Changes delivered positive impact
# Loop back to Phase 1 for next round of improvements
```

---

## Operational Workflows

### Daily Operations

```
Every morning:
  • Check for new feedback (auto-collected from Streamlit)
  • Monitor mapping status distribution (AUTO_CONFIRM vs NEEDS_REVIEW)
  
Every Friday:
  • Run evaluation
  • Review any guardrail alerts
  • Export metrics for reporting
```

### Weekly Improvement Cycle

```
Monday:   Analyze feedback (Gap #2)
Tuesday:  Generate proposals (Gap #3)
Wednesday: Review & approve proposals
Thursday:  Run shadow tests (Gap #7)
Friday:    Deploy approved changes
Monday:    Evaluate impact
Tuesday:   Plan next improvements
```

### Monthly Review

```
1. Compare metrics month-over-month
2. Identify persistent problem areas
3. Plan targeted improvements (new keywords, signal weighting)
4. Review LLM cost vs benefit
5. Update baselines for next month
```

---

## Key Insights

### 1. Feedback Quality Matters

Better feedback (more detailed, from experienced reviewers) → better proposals → better improvements.

```
Example bad feedback:
  Action: CORRECT
  Suggested: NAVY BLUE
  (No context about why)

Example good feedback:
  Action: CORRECT
  Suggested: NAVY BLUE
  Notes: "Maroon is too dark, NAVY is closer shade"
  (Context helps understand pattern)
```

### 2. Frequency Matters

Proposals based on 1 correction = noise.  
Proposals based on 20+ corrections = signal.

```
Config: min_frequency = 3 (only suggest if ≥3 corrections)
```

### 3. Statistical Validation Is Critical

Never deploy changes based on "looks good". Always shadow test and validate significance.

```
Example:
  Proposal looks good: correction_rate 32% → 28%
  But shadow test shows: p_value = 0.12 (not significant)
  
  Recommendation: Don't deploy yet (could be random chance)
  Better: Collect more data or try different approach
```

### 4. Rollback Plan

Always keep previous config backed up.

```
If deployed changes make things worse:
  1. Revert config/base.yaml
  2. Revert alias_overrides.yaml
  3. Update proposal status → APPLIED_REVERTED
  4. Run evaluation to confirm rollback helped
  5. Analyze what went wrong
```

---

## Summary

**Complete Feedback Loop (v2.0):**

1. **Collect** (Week 1) — Users submit feedback (CONFIRM/CORRECT/REJECT)
2. **Analyze** (Week 2) — Gap #2 extracts keyword patterns from CORRECT feedback
3. **Propose** (Week 3) — Gap #3 generates config & keyword improvement proposals
4. **Validate** (Week 4) — Gap #7 shadow tests proposals on sample batch
5. **Deploy** (Week 5) — Apply approved changes to production config
6. **Measure** (Week 6) — Run evaluation, confirm improvements
7. **Loop** (Week 7+) — Repeat cycle with next round of improvements

**Result:** Continuous, data-driven algorithm improvements without code changes.

---

**Last Updated:** 2026-06-11  
**Version:** 2.0 (Complete feedback loop: Gaps #2, #3, #4, #5, #6, #7)
