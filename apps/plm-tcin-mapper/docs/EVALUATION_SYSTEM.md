# Evaluation System — How Algorithm Quality is Measured

> **Complete walkthrough of the evaluation pipeline**
>
> Date: 2026-06-11  
> Version: 2.0 — Extended evaluation metrics (Gap #4) now integrated

---

## Table of Contents

1. [Overview](#overview)
2. [Basic Evaluation (v1)](#basic-evaluation-v1)
3. [Extended Evaluation (v2 — Gap #4)](#extended-evaluation-v2--gap-4)
4. [Per-Signal Accuracy Analysis](#per-signal-accuracy-analysis)
5. [Per-Department Performance](#per-department-performance)
6. [LLM Impact Analysis](#llm-impact-analysis)
7. [Confidence Calibration](#confidence-calibration)
8. [Running Evaluations](#running-evaluations)
9. [Interpreting Results](#interpreting-results)
10. [Use Cases & Examples](#use-cases--examples)

---

## Overview

**Goal:** Measure how well the matching algorithm is performing in production.

**Inputs:**
- All mappings from a batch (e.g., 50,000 TCIN→impression matches)
- All feedback records from human reviews (e.g., 1,200 corrections)

**Outputs:**
- v1: 4 aggregate metrics (pct_high, correction_rate, avg_confidence, guardrail alerts)
- v2: **20+ detailed metrics** breaking down performance by signal, department, LLM, confidence

**Key Insight:** Basic metrics hide problems. Extended metrics reveal *why* the algorithm is struggling.

```
Example:
  Overall correction_rate: 27%  ← OK-ish, but hides problems
  
  With extended metrics:
    Token overlap: 12% correction rate  ← Working well
    Keyword match: 38% correction rate  ← Problem signal!
    Fuzzy match:   48% correction rate  ← Very weak!
    
    → Insight: Fuzzy signal is hurting more than helping
```

---

## Basic Evaluation (v1)

### What Gets Measured

**Endpoint:** `POST /api/v1/eval/run`

```python
# Input: All mappings + feedback from database
mappings = db.mappings.find({})  # e.g., 50,000 docs
feedback = db.feedback.find({})  # e.g., 1,200 docs

# Output: Single EvalRun document
{
  "total_mappings": 50000,
  "by_status": {
    "AUTO_CONFIRM": 35000,    # ← No review needed
    "NEEDS_REVIEW": 13500,    # ← Needs human attention
    "LLM_ASSISTED": 1200,     # ← LLM helped
    "NO_MATCH": 300
  },
  "by_tier": {
    "HIGH": 34000,        # ≥ 0.85 confidence
    "GOOD": 12000,        # ≥ 0.70 confidence
    "FAIR": 3000,         # ≥ 0.50 confidence
    "LOW": 1000           # < 0.50 confidence
  },
  "pct_high": 0.68,             # 68% of mappings are high-confidence
  "pct_good": 0.24,
  "pct_fair": 0.06,
  "pct_low": 0.02,
  "avg_color_confidence": 0.79,
  "correction_rate": 0.27,      # 27% of reviewed were wrong
  "guardrail_alerts": [
    "HIGH_CORRECTION_RATE: 27% > 25% target",
    "REVIEW_QUEUE_BACKLOG: 13,500 > 1,000 limit"
  ]
}
```

### Guardrails (v1)

Four thresholds that trigger alerts if breached:

| Guardrail | Default | Meaning |
|-----------|---------|---------|
| `min_high_confidence_pct` | 40% | Alert if < 40% of mappings are HIGH tier |
| `max_low_confidence_pct` | 20% | Alert if > 20% of mappings are LOW tier |
| `review_queue_backlog_limit` | 1,000 | Alert if NEEDS_REVIEW count > 1,000 |
| `min_avg_confidence` | 0.60 | Alert if average confidence < 0.60 |

**Config location:** `config/base.yaml`

```yaml
eval:
  min_high_confidence_pct: 0.40
  max_low_confidence_pct: 0.20
  review_queue_backlog_limit: 1000
  min_avg_confidence: 0.60
```

### How Correction Rate is Computed

**Definition:** (# mappings with feedback where action=CORRECT) / (# mappings with any feedback)

```
Example:
  Reviewed mappings: 1,200
    • 850 CONFIRM (reviewer agreed)
    • 220 CORRECT (reviewer fixed it) ← Corrections!
    • 130 REJECT (reviewer cleared it)
  
  Correction rate = 220 / 1,200 = 0.183 (18.3%)
```

**Why this matters:**
- < 15%: Algorithm is working well
- 15–25%: Acceptable, some improvement needed
- 25–40%: Concerning, needs tuning
- > 40%: Algorithm is frequently wrong

---

## Extended Evaluation (v2 — Gap #4)

### What Gets Measured

**Endpoint:** `POST /api/v1/eval/detailed`

Same inputs as v1, but now computes **6 additional metric families:**

```python
{
  # v1 metrics (same as before)
  "total_mappings": 50000,
  "by_status": {...},
  "by_tier": {...},
  "pct_high": 0.68,
  "correction_rate": 0.27,
  
  # NEW: Per-Signal Accuracy (Gap #4)
  "per_signal_accuracy": {
    "token_overlap": {
      "signal_type": "token_overlap",
      "occurrences": 25000,    # ← How many mappings used this signal?
      "corrections": 3000,     # ← How many were corrected?
      "correction_rate": 0.12, # ← 12% of token_overlap matches were wrong
      "avg_confidence": 0.82,
      "confidence_by_tier": {
        "HIGH": 18000,
        "GOOD": 5000,
        "FAIR": 1500,
        "LOW": 500
      }
    },
    "keyword_match": {
      "signal_type": "keyword_match",
      "occurrences": 18000,
      "corrections": 6840,     # ← 38% correction rate!
      "correction_rate": 0.38,
      "avg_confidence": 0.75,
      "confidence_by_tier": {...}
    },
    "fuzzy_match": {
      "signal_type": "fuzzy_match",
      "occurrences": 7000,
      "corrections": 3360,     # ← 48% correction rate (very weak!)
      "correction_rate": 0.48,
      "avg_confidence": 0.62,
      "confidence_by_tier": {...}
    }
  },
  
  # NEW: Per-Department Metrics (Gap #4)
  "per_department_metrics": [
    {
      "department": "clothing",
      "total_mappings": 22000,
      "pct_high_confidence": 0.72,
      "correction_rate": 0.18,  # ← Good performance
      "avg_confidence": 0.82,
      "by_match_round": {
        "GREEDY": 15000,
        "HUNGARIAN": 6000,
        "FALLBACK": 800,
        "LLM": 200
      }
    },
    {
      "department": "home_textiles",
      "total_mappings": 12000,
      "pct_high_confidence": 0.58,
      "correction_rate": 0.35,  # ← Problem area!
      "avg_confidence": 0.71,
      "by_match_round": {...}
    },
    {
      "department": "shoes",
      "total_mappings": 16000,
      "pct_high_confidence": 0.70,
      "correction_rate": 0.22,
      "avg_confidence": 0.80,
      "by_match_round": {...}
    }
  ],
  
  # NEW: LLM Impact (Gap #4)
  "llm_impact": {
    "total_llm_calls": 850,              # ← How many times did LLM run?
    "llm_corrected": 180,                # ← How many LLM picks were wrong?
    "llm_correction_rate": 0.21,         # ← 21% of LLM picks were wrong
    "llm_avg_confidence": 0.68,
    "deterministic_corrected": 40,       # ← How many deterministic picks were wrong?
    "deterministic_correction_rate": 0.08, # ← 8% of deterministic were wrong
    "llm_vs_deterministic_improvement": 0.13  # ← LLM is 13% WORSE than deterministic!
  },
  
  # NEW: Confidence Calibration (Gap #4)
  "confidence_calibration_error": 0.08,  # ← ECE: Expected Calibration Error
  
  # NEW: High-Confidence Accuracy (Gap #4)
  "high_confidence_actual_correction_rate": 0.05,  # ← Only 5% wrong in HIGH tier
  
  # NEW: Low-Confidence Accuracy (Gap #4)
  "low_confidence_actual_correction_rate": 0.72    # ← 72% wrong in LOW tier (as expected)
}
```

---

## Per-Signal Accuracy Analysis

### Why This Matters

Three different scoring signals contribute to the final confidence score. If one signal is weak, it drags down quality.

```
Scoring Pipeline:
  
  1. Token Overlap Signal    → score1 = 0.85
  2. Keyword Match Signal    → score2 = 0.60
  3. Fuzzy Match Signal      → score3 = 0.45
  
  Final Score = max(score1, score2, score3) = 0.85
```

**Problem:** Final score is HIGH (0.85), but two signals are weak. If the top scorer is ever wrong, the others can't help.

**Solution:** Per-signal metrics reveal which signals are failing:

```
Per-Signal Correction Rates:
  • Token Overlap: 12% corrections (strong!)
  • Keyword Match: 38% corrections (weak!)
  • Fuzzy Match:   48% corrections (very weak!)
  
Insight: Fuzzy signal is hurting more than helping. 
Consider reducing its weight or disabling it.
```

### How It's Calculated

For each mapping, track **which signal was the strongest**:

```python
# Example mapping:
{
  "pid": "F123456",
  "tcin_id": "50123456",
  "matched_impression_name": "RUBY RED",
  "color_confidence": 0.82,
  "color_possible_values": [
    {"impression_name": "RUBY RED", "score": 0.82, "reason": "fuzzy_match"},
    {"impression_name": "CHERRY RED", "score": 0.80, "reason": "keyword_match"},
    {"impression_name": "CRIMSON RED", "score": 0.75, "reason": "token_overlap"}
  ],
  "match_round": "HUNGARIAN",
  "signal_type": "fuzzy_match"  # ← The winning signal
}

# Later, feedback shows it was corrected:
{
  "mapping_id": "...",
  "action": "CORRECT",
  "suggested_impression_name": "CHERRY RED"  # ← Reviewer chose the 2nd option
}

# → Increment fuzzy_match correction count
```

---

## Per-Department Performance

### Why This Matters

Different product categories have different naming conventions. Clothing names are literal; home textiles are poetic. Algorithm may be better at one than the other.

```
Example naming styles:
  
  Clothing (literal):
    • "Navy Blue Cardigan" → "NAVY BLUE"
    • "Red T-Shirt" → "RED"
    → Easy to match: token overlap, keywords work well
  
  Home Textiles (poetic):
    • "Tranquil Sunset Throw" → ??? (could be orange, pink, or red)
    • "Cozy Morning Blanket" → ??? (vague, emotional name)
    → Hard to match: needs human interpretation or LLM
```

### Metrics by Department

```python
"per_department_metrics": [
  {
    "department": "clothing",
    "total_mappings": 22000,
    "pct_high_confidence": 0.72,      # ← 72% of clothing is high-confidence
    "correction_rate": 0.18,           # ← 18% correction rate
    "avg_confidence": 0.82,
    "by_match_round": {
      "GREEDY": 15000,                # ← Mostly easy greedy matches
      "HUNGARIAN": 6000,
      "FALLBACK": 800,
      "LLM": 200
    }
  },
  {
    "department": "home_textiles",
    "total_mappings": 12000,
    "pct_high_confidence": 0.58,      # ← Only 58% high-confidence
    "correction_rate": 0.35,           # ← 35% correction rate (problematic!)
    "avg_confidence": 0.71,
    "by_match_round": {
      "GREEDY": 6000,                 # ← Fewer easy matches
      "HUNGARIAN": 4000,
      "FALLBACK": 1500,
      "LLM": 500                      # ← More LLM calls needed
    }
  }
]

# Insight: Home textiles need special handling
# Options:
#   1. Improve keyword dictionary for home_textiles
#   2. Raise llm_fallback_threshold just for this department
#   3. Hire dedicated reviewer for home_textiles
```

---

## LLM Impact Analysis

### Why This Matters

LLM is expensive (tokens, latency, potential hallucinations). Should we use it? Is it actually helping?

```python
"llm_impact": {
  "total_llm_calls": 850,              # ← 850 out of 50,000 needed LLM
  "llm_corrected": 180,                # ← 180 of those LLM picks were wrong
  "llm_correction_rate": 0.21,         # ← 21% of LLM picks were wrong
  "llm_avg_confidence": 0.68,          # ← LLM confidence is lower
  "deterministic_corrected": 40,       # ← 40 deterministic picks were wrong
  "deterministic_correction_rate": 0.08, # ← Only 8% of deterministic wrong
  "llm_vs_deterministic_improvement": 0.13  # ← LLM is 13% WORSE!
}

# Interpretation:
#   LLM correction rate (21%) > Deterministic (8%)
#   → LLM is making MORE mistakes than deterministic!
#
# Recommendation:
#   ❌ Disable LLM (it's hurting)
#   OR
#   ✅ Adjust llm_fallback_threshold higher
#       (only call LLM for truly ambiguous cases)
```

### When LLM Helps vs Hurts

**LLM Helps When:**
- Deterministic confidence is genuinely ambiguous (0.45–0.55)
- Multiple candidates are equally good
- Impression names are creative/poetic

**LLM Hurts When:**
- Deterministic confidence is already high (> 0.70)
- LLM hallucinates answers not in candidate list
- Token usage is unexpectedly high (e.g., buggy prompt)

---

## Confidence Calibration

### Why This Matters

If the system says "95% confident", how often is it actually right?

**Calibration Error (ECE):** Expected Calibration Error — gap between predicted and actual accuracy.

```
Perfect calibration:
  When algorithm says "95% confident" → actually right 95% of the time
  When algorithm says "70% confident" → actually right 70% of the time
  
Miscalibration (typical):
  When algorithm says "85% confident" → actually right only 72% of the time
  → Calibration error = 0.13 (13 percentage points off)
```

### How It's Computed

```python
# For each confidence bin:
bins = {
  0.90: {
    "predictions": 8000,      # 8,000 mappings with 85–95% confidence
    "actual_accuracy": 0.88   # 88% of them were actually correct
    "delta": 0.88 - 0.90 = -0.02  # Slightly overconfident
  },
  0.70: {
    "predictions": 5000,
    "actual_accuracy": 0.62,  # Only 62% correct!
    "delta": 0.62 - 0.70 = -0.08  # Significantly overconfident
  },
  0.50: {
    "predictions": 3000,
    "actual_accuracy": 0.49,
    "delta": 0.49 - 0.50 = -0.01  # Well-calibrated
  }
}

# Overall ECE = average(|delta|) = (0.02 + 0.08 + 0.01) / 3 = 0.037
```

**Interpretation:**
- ECE < 0.05: Well-calibrated (confidence scores are trustworthy)
- ECE 0.05–0.10: Moderately calibrated (confidence scores are roughly right)
- ECE > 0.10: Poorly calibrated (don't trust confidence scores)

---

## Running Evaluations

### v1: Basic Evaluation

```bash
# Via REST API
curl -X POST http://localhost:8001/api/v1/eval/run

# Response:
{
  "total_mappings": 50000,
  "pct_high": 0.68,
  "correction_rate": 0.27,
  "guardrail_alerts": [...]
}

# Stored in: db.eval_runs collection
```

### v2: Extended Evaluation

```bash
# Via REST API
curl -X POST http://localhost:8001/api/v1/eval/detailed

# Response: (same structure as above, but with 20+ metrics)

# Stored in: db.extended_eval_runs collection
```

### Via Streamlit UI

**Page:** Admin → Evaluation Metrics

1. Click "Run Analysis"
2. See results in 4 tabs:
   - **Overview** — KPI cards + guardrail alerts
   - **Per-Signal** — Which signals are weak?
   - **Per-Department** — Which categories need work?
   - **LLM Impact** — Is LLM helping?

---

## Interpreting Results

### Quick Diagnosis Guide

| Symptom | Cause | Fix |
|---------|-------|-----|
| **High correction_rate (> 30%)** | Algorithm often wrong | Improve keywords (Gap #2) or lower thresholds (Gap #3) |
| **Low pct_high (< 40%)** | Few mappings are confident | Improve scoring signals or accept more ambiguity |
| **High per_signal correction_rate for one signal** | That signal is weak | Reduce its weight or disable it |
| **High per_department correction_rate** | That category is hard | Special handling for that department |
| **LLM correction_rate > deterministic** | LLM is hurting | Raise llm_fallback_threshold |
| **High confidence_calibration_error** | Confidence scores are lies | Recalibrate scoring function |

### Example: Diagnosis Walkthrough

**Scenario:** Overall correction_rate is 35% (bad). What do we do?

```
Step 1: Check per_signal metrics
  
  token_overlap:    correction_rate = 0.08 ✅ (strong)
  keyword_match:    correction_rate = 0.42 ❌ (weak!)
  fuzzy_match:      correction_rate = 0.68 ❌ (very weak!)
  
  → Problem: Keyword and fuzzy signals are failing

Step 2: Check per_department metrics
  
  clothing:         correction_rate = 0.18 ✅ (good)
  home_textiles:    correction_rate = 0.58 ❌ (very bad!)
  
  → Problem: Home textiles is dragging down the average

Step 3: Check LLM impact
  
  llm_correction_rate:        0.28
  deterministic_correction_rate: 0.33
  
  → LLM is actually helping (28% vs 33%)

Step 4: Recommendation
  
  ✅ Fix #1: Improve keywords for home_textiles (Gap #2)
  ✅ Fix #2: Reduce fuzzy signal weight (Gap #3 → threshold tuning)
  ✅ Validate: Run shadow test before promoting (Gap #7)
```

---

## Use Cases & Examples

### Use Case 1: Weekly Quality Check

**Goal:** Monitor if quality is degrading over time.

```bash
# Monday morning: Run evaluation
curl -X POST http://localhost:8001/api/v1/eval/detailed

# Check if any guardrails are broken
# Compare to previous week's eval_runs collection

# If correction_rate increased from 20% → 28%:
#   → Something changed; investigate
#   → Compare per_signal metrics to see which signal got worse
#   → Check if new data arrived (different departments?)
```

### Use Case 2: Testing Algorithm Changes

**Goal:** Validate that a keyword change actually helps.

```
Baseline batch:
  POST /api/v1/mappings/run {batch_id: "baseline_001", use_llm: true}
  
  Eval result:
    correction_rate: 0.27
    per_signal accuracy (keyword_match): 0.42

Update keywords (Gap #2):
  + pink → magenta, pink_hue (was too broad)
  
Shadow test:
  POST /api/v1/mappings/run {batch_id: "shadow_001", shadow: true}
  
  Eval result:
    correction_rate: 0.23 ✅ (improved!)
    per_signal accuracy (keyword_match): 0.35 ✅ (improved!)
  
Shadow comparison (Gap #7):
  POST /api/v1/shadow-compare {
    baseline_batch_id: "baseline_001",
    shadow_batch_id: "shadow_001"
  }
  
  p_value: 0.002 ✅ (statistically significant)
  
Decision: Deploy the keyword change
```

---

## Summary

**Basic Evaluation (v1):**
- 4 aggregate metrics
- 4 guardrails
- Good for: Quick health check

**Extended Evaluation (v2 — Gap #4):**
- 20+ detailed metrics
- Diagnoses problems at 3 levels: signal, department, LLM
- Good for: Root-cause analysis and targeted improvements

**Next Step:** Use evaluation metrics to feed Gap #3 (threshold tuning) and Gap #2 (alias mining) for automated improvements.

---

**Last Updated:** 2026-06-11  
**Version:** 2.0 (Gap #4: Extended Evaluation Metrics)
