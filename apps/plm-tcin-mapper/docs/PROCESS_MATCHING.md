# Process: Deterministic + LLM Matching Pipeline

> **Purpose:** Map guest-facing TCIN colors to design/manufacturing impression names  
> **Entry Point:** `POST /api/v1/mappings/run`  
> **Core Logic:** `plm_tcin_mapper/pipeline/orchestrator.py` + `plm_tcin_mapper/matching/`

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│ Client Request                                                    │
│ POST /api/v1/mappings/run                                        │
│ {                                                                │
│   "pid": "009E83" | null,     # single PID or all unmatched     │
│   "use_llm": true,            # enable LLM fallback             │
│   "dry_run": false,           # parse & match but don't write    │
│   "force": false,             # re-match already-matched PIDs   │
│   "department": "Clothing" | null,   # filter by dept          │
│   "shadow": false,            # shadow mode (test config)        │
│   "batch_id": null            # custom batch ID or generated     │
│ }                                                                │
└──────────────────────────────────────────────────────────────────┘
                              ↓
                    MappingService
              (routes/mappings.py)
                              ↓
                  service.run(request)
                   [async wrapper]
                              ↓
        run_in_executor(None, _run_sync)
                              ↓
            _run_sync(request)
            [sync function, CPU-bound]
            1. Generate batch_id (or use provided)
            2. Get PIDs to match:
                              ↓
    orchestrator._get_pids_to_match(db, cfg, force, department)
    ├─ If force=true:
    │   → All PIDs in tcin_records
    │
    └─ Else (default):
        → PIDs in tcin_records NOT yet in mappings
        → Filter by department if specified
        → Sort ascending
                              ↓
    For each PID:
    orchestrator.match_pid(
        pid, tcin_records, variation_records,
        cfg, llm, use_llm, dry_run, batch_id
    )
                              ↓
        ┌──────────────────────────────────────────────────────┐
        │ STEP 1: Load Raw Data                                │
        ├──────────────────────────────────────────────────────┤
        │ • _load_tcin_records(db, pid)                        │
        │   → All TCIN records for this PID                    │
        │                                                       │
        │ • _load_variation_records(db, pid)                   │
        │   → All variation records for this PID               │
        │                                                       │
        │ Guard: if either is empty, skip this PID             │
        └──────────────────────────────────────────────────────┘
                              ↓
        ┌──────────────────────────────────────────────────────┐
        │ STEP 2: Deterministic Matching                       │
        │ match_pid_records(tcin_records, var_records, cfg)   │
        └──────────────────────────────────────────────────────┘
                              ↓
            ┌──────────────────────────────────────┐
            │ Extract distinct colors & impressions│
            ├──────────────────────────────────────┤
            │ distinct_colors =                     │
            │   [r.color_name for r in tcin_records]│
            │   deduplicated, preserving order      │
            │                                       │
            │ distinct_impressions =                │
            │   [r.impression_name for r in vars]   │
            │   deduplicated, preserving order      │
            └──────────────────────────────────────┘
                              ↓
            ┌──────────────────────────────────────────────┐
            │ STEP 2a: Build Color-Impression Score Matrix │
            ├──────────────────────────────────────────────┤
            │                                               │
            │           IMP1  IMP2  IMP3  IMP4            │
            │ Color1   0.92  0.45  0.65  0.38             │
            │ Color2   0.15  0.88  0.22  0.51             │
            │ Color3   0.34  0.52  0.79  0.26             │
            │                                               │
            │ build_score_matrix(distinct_colors,          │
            │                    distinct_impressions,     │
            │                    keyword_map)              │
            └──────────────────────────────────────────────┘
                              ↓
            Scoring Function: color_score(color_name, imp_name)
            ┌─────────────────────────────────────────────┐
            │ Signal 1: Direct Token Overlap              │
            ├─────────────────────────────────────────────┤
            │ if "maroon" in "ROMANTIC MAROON"            │
            │   → score = 0.70-0.99                       │
            │   → reason = "token_overlap"                │
            │                                              │
            │ Signal 2: Keyword Base Match                │
            ├─────────────────────────────────────────────┤
            │ color_keywords.get_merged_keyword_map()     │
            │ → {ruby: red, maroon: red, ...}             │
            │                                              │
            │ if keyword_to_base(maroon) ==               │
            │    keyword_to_base(ruby)                    │
            │   → score = 0.88-0.92                       │
            │   → reason = "keyword_match:red"            │
            │                                              │
            │ Signal 3: Fuzzy String Match                │
            ├─────────────────────────────────────────────┤
            │ if no token/keyword match:                  │
            │   score = fuzzy_wRatio(maroon, ruby)        │
            │   score *= penalty (0.95)                   │
            │   score = min(score, 0.82)                  │
            │   → reason = "fuzzy"                        │
            │                                              │
            │ Fallback                                     │
            ├─────────────────────────────────────────────┤
            │ if all signals fail:                        │
            │   → score = 0.0                             │
            │   → reason = "no_match"                     │
            └─────────────────────────────────────────────┘
                              ↓
            ┌──────────────────────────────────────┐
            │ STEP 2b: Three-Round Assignment      │
            │ _three_round_assign(colors,          │
            │                     impressions,     │
            │                     score_matrix)    │
            └──────────────────────────────────────┘
                              ↓
            Round 1: GREEDY High-Confidence
            ┌──────────────────────────────────┐
            │ threshold = cfg.matching.         │
            │            auto_confirm_threshold│
            │            (default: 0.85)        │
            │                                    │
            │ 1. Flatten matrix to list of      │
            │    (score, color_idx, imp_idx)   │
            │ 2. Filter: score ≥ 0.85           │
            │ 3. Sort DESC by score             │
            │ 4. For each pair:                 │
            │    - Lock if color & imp unassigned
            │    - Mark: GREEDY round           │
            │ 5. Continue if pairs remain      │
            └──────────────────────────────────┘
                              ↓
            Round 2: HUNGARIAN Optimal 1:1
            ┌──────────────────────────────────┐
            │ Sub-matrix: unassigned colors ×  │
            │            unassigned impressions│
            │                                    │
            │ scipy.optimize.linear_sum_       │
            │   assignment(-sub_matrix)         │
            │ (negative: scipy minimizes,      │
            │  so negate to maximize)           │
            │                                    │
            │ Result: globally optimal 1:1      │
            │ Mark: HUNGARIAN round             │
            └──────────────────────────────────┘
                              ↓
            Round 3: FALLBACK Best Available
            ┌──────────────────────────────────┐
            │ For each unassigned color:        │
            │   imp = argmax(row in sub_matrix)│
            │   (best available impression)     │
            │   Mark: FALLBACK round            │
            │                                    │
            │ Result: all colors assigned       │
            └──────────────────────────────────┘
                              ↓
            Output: Assignment Dict
            {
              "Maroon": "ROMANTIC RUBY",
              "Red": "BOLD RED",
              "Pink": "SOFT PINK"
            }
            With MatchRound for each color
                              ↓
            ┌──────────────────────────────────┐
            │ STEP 2c: Size Matching            │
            │ best_size_match(tcin_size,       │
            │                 variation_sizes) │
            └──────────────────────────────────┘
                              ↓
            For each TCIN record:
            1. Get assigned impression name
            2. Get all variation sizes for that impression
            3. Find closest match:
               - Normalize both: "1X" → "1x", "XL" → "xl"
               - Levenshtein distance
               - Ordinal-aware (1x < 2x < 3x)
            4. Return (best_size, confidence_0_to_1)
                              ↓
            ┌──────────────────────────────────┐
            │ STEP 2d: Build Result Dicts       │
            │ One dict per TCIN record          │
            └──────────────────────────────────┘
                              ↓
            raw_results = [
              {
                "pid": "009E83",
                "tcin_id": "94447439",
                "tcin_color": "Red",
                "tcin_color_name": "Maroon",
                "tcin_size": "1X",
                "matched_impression_id": "dd948247-...",
                "matched_impression_name": "ROMANTIC RUBY",
                "variation_size": "1x",
                "color_confidence": 0.92,
                "size_confidence": 0.95,
                "confidence_tier": "HIGH",  # ≥ 0.85
                "color_match_reason": "token_overlap",
                "color_possible_values": [  # top candidates
                  {impression_name, score, reason},
                  ...
                ],
                "match_round": "GREEDY",
                "status": "AUTO_CONFIRM",
                "candidates": ["ROMANTIC RUBY", "BOLD RED", ...],
                "used_llm": False
              },
              ...
            ]
                              ↓
        ┌──────────────────────────────────────────────────────┐
        │ STEP 3: LLM Disambiguation (Optional)                │
        │ if use_llm:                                          │
        │   disambiguate_low_confidence(raw_results, cfg, llm)│
        └──────────────────────────────────────────────────────┘
                              ↓
            threshold = cfg.matching.llm_fallback_threshold
            (default: 0.60)
                              ↓
            For each mapping in raw_results:
            ├─ if used_llm already: skip
            ├─ if color_confidence ≥ threshold: skip
            └─ else (low confidence):
                ┌──────────────────────────────────────┐
                │ Call disambiguator._call_llm()       │
                │ (plm_tcin_mapper/llm/disambiguator.py│
                │  99-117)                             │
                └──────────────────────────────────────┘
                        ↓
                Build prompt:
                ┌──────────────────────────────────────┐
                │ System: "You are a color expert..."  │
                │                                       │
                │ User:                                │
                │ "TCIN color: 'Maroon'                │
                │             (family: Red, size: 1X)  │
                │                                       │
                │  Deterministic top pick:             │
                │  'ROMANTIC RUBY'                     │
                │                                       │
                │  Candidates:                         │
                │  - ROMANTIC RUBY (0.45)              │
                │  - DUSTY ROSE (0.42)                 │
                │  - MUTED PLUM (0.38)"                │
                └──────────────────────────────────────┘
                        ↓
                Call LLM:
                llm.chat(ChatRequest(
                  messages=[system, user],
                  response_format="json"
                ))
                        ↓
                ⚠️ Gap #1: No llm_calls record written
                (Just logs the response)
                        ↓
                Parse JSON response:
                {
                  "chosen_impression": "DUSTY ROSE",
                  "confidence": 0.68,
                  "reasoning": "Maroon leans pink; DUSTY ROSE
                                is closer than ruby."
                }
                        ↓
                Update mapping dict:
                {
                  ...
                  "matched_impression_name": "DUSTY ROSE",
                  "color_confidence": 0.68,
                  "llm_rationale": "Maroon leans pink...",
                  "used_llm": True,
                  "match_round": "LLM"
                }
                        ↓
            End for-each loop
            raw_results now has LLM enhancements
                              ↓
        ┌──────────────────────────────────────────────────────┐
        │ STEP 4: Status Assignment                            │
        │ orchestrator.match_pid() finishes LLM pass           │
        └──────────────────────────────────────────────────────┘
                              ↓
            For each mapping:
            ┌─────────────────────────────────────────┐
            │ Apply Status Rules                       │
            ├─────────────────────────────────────────┤
            │                                          │
            │ if used_llm:                            │
            │   if color_conf ≥ auto_confirm_thresh: │
            │     status = LLM_ASSISTED                │
            │   else:                                 │
            │     status = NEEDS_SPOT_CHECK           │
            │                                          │
            │ elif color_conf ≥ auto_confirm_thresh:  │
            │   status = AUTO_CONFIRM                 │
            │                                          │
            │ elif color_conf < no_match_threshold:   │
            │   status = NO_MATCH                     │
            │   (clear impression fields)             │
            │                                          │
            │ else:                                   │
            │   status = NEEDS_REVIEW                 │
            └─────────────────────────────────────────┘
                              ↓
            Create Mapping objects (from raw dicts)
            ✅ Validates all fields
            ❌ On error: create minimal fallback Mapping
                              ↓
        ┌──────────────────────────────────────────────────────┐
        │ STEP 5: Persist to MongoDB                           │
        │ for each mapping:                                    │
        │   orchestrator._upsert_mapping(db, mapping)          │
        └──────────────────────────────────────────────────────┘
                              ↓
            If not dry_run:
            db.mappings.update_one(
              {pid: mapping.pid, tcin_id: mapping.tcin_id},
              {$set: mapping.model_dump(by_alias=True)},
              upsert=True
            )
            Accumulate status counts
                              ↓
            BatchStats {
              total_pids: N,
              pids_matched: M,
              pids_no_data: errors,
              pids_errored: failures,
              total_mappings_written: count,
              status_counts: {
                AUTO_CONFIRM: X,
                NEEDS_REVIEW: Y,
                ...
              }
            }
                              ↓
        MappingRunResponse {
          status: "ok",
          batch_id: "batch_abc123...",
          total_pids: 5000,
          pids_matched: 4800,
          pids_no_data: 150,
          pids_errored: 50,
          total_mappings_written: 12500,
          status_counts: {
            AUTO_CONFIRM: 7200,
            NEEDS_REVIEW: 3500,
            LLM_ASSISTED: 1200,
            ...
          },
          dry_run: false
        }
                              ↓
                        200 OK
```

---

## Algorithm Deep Dive

### The Three-Round Assignment Algorithm

**Problem:** Match N TCIN colors to M impression names with maximum total similarity score, respecting 1:1 constraint (each color gets one impression, each impression gets ≤ one color).

**Why not greedy alone?**
```
Example: 3 colors, 3 impressions

Score matrix:
         IMP1  IMP2  IMP3
Color1   0.90  0.10  0.10  ← Greedy picks IMP1 (0.90)
Color2   0.89  0.91  0.10  ← Greedy picks IMP2 (0.91)
Color3   0.05  0.05  0.95  ← Greedy picks IMP3 (0.95)

Greedy total: 0.90 + 0.91 + 0.95 = 2.76

But optimal 1:1 would be:
Color1 → IMP2 (0.10) [no match]
Color2 → IMP1 (0.89)
Color3 → IMP3 (0.95)

Greedy total: 2.76 ✓ (greedy happened to be optimal here)

Better example:
         IMP1  IMP2
Color1   0.99  0.50  ← Greedy picks IMP1 (0.99)
Color2   0.98  0.99  ← Greedy picks IMP2 (0.99)

Greedy total: 0.99 + 0.99 = 1.98

Optimal:
Color1 → IMP2 (0.50)
Color2 → IMP1 (0.98)

Optimal total: 0.50 + 0.98 = 1.48  ✗ WORSE

Actually optimal is greedy here too...

Real worst case:
         IMP1  IMP2
Color1   0.10  0.99  ← Greedy picks IMP2 (0.99)
Color2   0.99  0.10  ← Greedy picks IMP1 (0.99)

Greedy total: 0.99 + 0.99 = 1.98
Optimal: Same = 1.98 ✓

BUT: The Hungarian algorithm guarantees global optimality
regardless of threshold or greedy selection. That's the value.
```

**Three-Round Approach:**

1. **Round 1 (Greedy):** Lock in high-confidence pairs fast. Avoids slow Hungarian for most colors.
2. **Round 2 (Hungarian):** Solve remaining colors optimally. Handles edge cases.
3. **Round 3 (Fallback):** Catch any stragglers with any positive score.

**Why this order?**
- High-confidence colors are usually correct; greedy speeds up execution
- Hungarian is slower (O(n³) but small n after round 1)
- Fallback ensures all colors get *some* assignment

### Confidence Scoring Formula

Each color-impression pair gets a **composite score** (0.0 to 1.0):

```python
def color_score(color_name: str, impression_name: str, keyword_map: dict) -> (float, str):
    # Signal 1: Direct token overlap
    color_tokens = set(color_name.lower().split())
    imp_tokens = set(impression_name.lower().split())
    if color_tokens & imp_tokens:  # intersection
        overlap_pct = len(color_tokens & imp_tokens) / len(color_tokens | imp_tokens)
        score = 0.70 + (overlap_pct * 0.29)  # 0.70-0.99
        return score, "token_overlap"
    
    # Signal 2: Keyword base match
    color_base = keyword_map.get(color_name.lower())
    impression_base = keyword_map.get(impression_name.lower())
    if color_base and impression_base and color_base == impression_base:
        score = 0.88 + random(0.0, 0.04)  # 0.88-0.92 for consistency
        return score, f"keyword_match:{color_base}"
    
    # Signal 3: Fuzzy string similarity
    wRatio = rapidfuzz.distance.Levenshtein.normalized_similarity(
        color_name.lower(), impression_name.lower()
    )
    fuzzy_score = wRatio * 0.95  # penalty
    fuzzy_score = min(fuzzy_score, 0.82)  # cap at 0.82 (weaker than keyword)
    if fuzzy_score > 0.0:
        return fuzzy_score, "fuzzy"
    
    # No match
    return 0.0, "no_match"
```

**Scoring Properties:**
- **Token overlap > Keyword > Fuzzy** (signal priority by caps)
- **Keyword overlap never loses to fuzzy** (0.88 > 0.82)
- **All signals ≥ 0.0** (no negative scores)

### Size Matching

**Problem:** Map TCIN size (e.g., "1X") to closest variation size (e.g., "1x", "M", "XL").

**Algorithm:**
```python
def best_size_match(tcin_size: str, var_sizes: list[str]) -> (str, float):
    # Normalize: "1X" → "1x", "XL" → "xl"
    normalized_tcin = normalize_size(tcin_size)
    
    # Try exact match first
    for var_size in var_sizes:
        if normalize_size(var_size) == normalized_tcin:
            return var_size, 1.0
    
    # Levenshtein distance + ordinal awareness
    best_var = None
    best_distance = float('inf')
    for var_size in var_sizes:
        normalized_var = normalize_size(var_size)
        distance = levenshtein(normalized_tcin, normalized_var)
        
        # Penalize ordinal mismatch: "1x" vs "3x" is large jump
        if _is_ordinal(normalized_tcin) and _is_ordinal(normalized_var):
            ord_diff = abs(_ordinal_rank(normalized_tcin) - _ordinal_rank(normalized_var))
            distance += ord_diff * 2
        
        if distance < best_distance:
            best_distance = distance
            best_var = var_size
    
    # Confidence: 1.0 if exact, else 0.5 + decay
    confidence = 0.5 + (max(0, 5 - best_distance) / 10)
    return best_var, confidence
```

**Examples:**
| TCIN Size | Variation Sizes | Best Match | Confidence |
|-----------|-----------------|------------|-----------|
| "1X" | ["1x", "L"] | "1x" | 1.0 |
| "Large" | ["M", "L", "XL"] | "L" | 0.9 |
| "2X" | ["1x", "2x", "3x"] | "2x" | 1.0 |
| "M" | ["1x", "2x"] | "1x" | 0.6 |

---

## Request/Response Examples

### Request 1: Match Unmatched PIDs

```bash
POST /api/v1/mappings/run
Content-Type: application/json

{
  "use_llm": true,
  "batch_size": 500
}
```

**Response:**
```json
{
  "status": "ok",
  "batch_id": "batch_abc123def456",
  "total_pids": 5000,
  "pids_matched": 4800,
  "pids_no_data": 150,
  "pids_errored": 50,
  "total_mappings_written": 12543,
  "status_counts": {
    "AUTO_CONFIRM": 7234,
    "NEEDS_REVIEW": 3500,
    "LLM_ASSISTED": 1200,
    "NEEDS_SPOT_CHECK": 400,
    "NO_MATCH": 209
  },
  "dry_run": false
}
```

### Request 2: Match Single PID

```bash
POST /api/v1/mappings/run
Content-Type: application/json

{
  "pid": "009E83",
  "use_llm": true,
  "force": true
}
```

**Response:**
```json
{
  "status": "ok",
  "batch_id": "batch_xyz789...",
  "total_pids": 1,
  "pids_matched": 1,
  "pids_no_data": 0,
  "pids_errored": 0,
  "total_mappings_written": 18,
  "status_counts": {
    "AUTO_CONFIRM": 12,
    "NEEDS_REVIEW": 4,
    "LLM_ASSISTED": 2
  },
  "dry_run": false
}
```

### Request 3: Dry Run (No DB Write)

```bash
POST /api/v1/mappings/run
Content-Type: application/json

{
  "department": "Clothing",
  "use_llm": false,
  "dry_run": true
}
```

**Response:**
```json
{
  "status": "ok",
  "batch_id": "batch_dryrun_...",
  "total_pids": 1200,
  "pids_matched": 1150,
  "pids_no_data": 45,
  "pids_errored": 5,
  "total_mappings_written": 3445,
  "status_counts": {
    "AUTO_CONFIRM": 2100,
    "NEEDS_REVIEW": 1100,
    "NEEDS_SPOT_CHECK": 245
  },
  "dry_run": true
}
```

---

## Get Mappings (Query)

**Endpoint:** `GET /api/v1/mappings`

**Query Parameters:**
```
?pid=009E83                    # Filter by PID
&status=NEEDS_REVIEW           # Filter by status
&department=Clothing           # Filter by department_ids
&page=1                        # Page number (1-indexed)
&page_size=20                  # Items per page
```

**Response:**
```json
{
  "total": 18,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": "550e8400-...",
      "pid": "009E83",
      "tcin_id": "94447439",
      "tcin_color": "Red",
      "tcin_color_name": "Maroon",
      "tcin_size": "1X",
      "matched_impression_name": "ROMANTIC RUBY",
      "matched_impression_id": "dd948247-...",
      "color_confidence": 0.92,
      "confidence_tier": "HIGH",
      "status": "AUTO_CONFIRM",
      "match_round": "GREEDY",
      "batch_id": "batch_abc123..."
    },
    ...
  ]
}
```

---

## Configuration Parameters

**Matching configuration** (`config/base.yaml`):

```yaml
matching:
  # Threshold for automatic confirmation (no review needed)
  auto_confirm_threshold: 0.85
  
  # Threshold for LLM fallback (if score below this, ask LLM)
  llm_fallback_threshold: 0.60
  
  # Threshold for NO_MATCH status (clear impression)
  no_match_threshold: 0.75
  
  # High-confidence threshold for Round 1 greedy
  # (typically same as auto_confirm_threshold)
  # Not directly exposed; uses auto_confirm_threshold
```

**Tuning Guidance:**
- Lower `auto_confirm_threshold` → fewer NEEDS_REVIEW → risk more errors
- Raise `llm_fallback_threshold` → more LLM calls → slower, higher cost
- Adjust based on correction_rate from evaluator

---

## Performance Characteristics

**Throughput:**
- **Deterministic matching:** ~100-200 PIDs/sec (CPU-bound)
- **With LLM:** ~1-2 PIDs/sec (network latency)

**Example: 5,000 PIDs**
- Deterministic only: ~30 seconds
- With LLM (10% fallback): ~2-5 minutes
- Memory: < 200MB

**Optimization Tips:**
- Use `use_llm=false` for initial fast run
- Use `department` filter to split work across batches
- Use `shadow=true` for config testing (doesn't block production)

---

## Next Steps

After successful matching:
1. Query mappings: `/api/v1/mappings?status=NEEDS_REVIEW`
2. Review via Streamlit UI (see PROCESS_FEEDBACK.md)
3. Run evaluation (see PROCESS_EVALUATION.md)
