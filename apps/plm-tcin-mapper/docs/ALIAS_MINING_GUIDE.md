# Alias Mining Implementation Guide — Gap #2

**Date:** 2026-06-11  
**Status:** ✅ IMPLEMENTED  
**Effort:** ~12 hours  
**Impact:** Data-driven keyword refinement from feedback patterns

---

## Overview

**Alias Mining** is a feature that analyzes corrected feedback to identify keyword mapping problems and propose improvements to the color scoring system. Instead of manually tuning keywords in `color_keywords.py` and `alias_overrides.yaml`, the system now extracts patterns from human corrections and generates evidence-based proposals.

### The Problem

When reviewers correct a mapping, they signal that the deterministic algorithm made a wrong choice. For example:

```
Human correction:
  Original: "RUBY RED" (matched)
  Corrected: "PURPLE VIOLET" (suggested)
  
Signal: The keyword "ruby" in red's mapping led to a wrong match.
        Maybe "ruby" should be in purple's keywords instead.
```

Before this feature:
- These patterns were invisible
- Developers had to manually review feedback and guess at keyword fixes
- Same mistakes repeated across multiple PIDs

After this feature:
- Patterns are automatically extracted
- Proposals are generated with frequency/confidence metrics
- Human reviewers can approve/reject proposals
- Changes are automatically applied to `alias_overrides.yaml`

---

## Architecture

### Data Flow

```
feedback records (CORRECT actions)
    ↓
AliasMiningService._extract_keyword_patterns()
    • Extract tokens from original_impression and suggested_impression
    • Map tokens to base colors
    • Track which keywords appear in corrections
    • Tally: "How often does keyword X cause corrections from color A to color B?"
    ↓
KeywordCorrection objects
    • frequency: how many times keyword appeared in corrections
    • correction_count: how many of those were actual mismatches
    • target_colors: which colors did reviewers prefer?
    • supporting_feedback_ids: link back to original feedback
    ↓
AliasMiningService._generate_proposals()
    • Filter by min_frequency (default 3 corrections)
    • Filter by min_confidence (default 60% of occurrences were corrections)
    • Generate ProposalType.ALIAS_MOVE for high-confidence patterns
    • Store in alias_mining_proposals collection
    ↓
API endpoints
    • POST /api/v1/alias-mining/analyze — trigger new analysis
    • GET /api/v1/alias-mining/proposals — view pending proposals
    • POST /api/v1/alias-mining/proposals/{id}/apply — apply a proposal
    ↓
alias_overrides.yaml
    • Update keyword mappings
    • No code changes needed; merged at runtime by color_keywords.py
```

### Models

#### `AliasMiningProposal`

```python
class AliasMiningProposal(BaseModel):
    id: str                                  # UUID
    proposal_type: ProposalType             # ALIAS_MOVE, ALIAS_ADD, THRESHOLD_ADJUST
    status: ProposalStatus                  # PENDING, APPROVED, REJECTED, APPLIED
    
    base_color: str                         # Current color (e.g., "red")
    keyword: str                            # Keyword to move (e.g., "ruby")
    suggested_base_color: str | None        # Target color (e.g., "purple")
    
    frequency: int                          # How many corrections involved this keyword
    confidence: float                       # What % of occurrences were corrections
    supporting_feedback_ids: list[str]      # Link to original feedback records
    
    rationale: str                          # Human-readable explanation
    estimated_impact: str                   # Impact assessment (HIGH/MEDIUM/LOW)
    
    created_at: datetime
    applied_at: datetime | None
```

#### Enums

```python
class ProposalType(StrEnum):
    ALIAS_ADD = "ALIAS_ADD"                 # Add new keyword (future)
    ALIAS_MOVE = "ALIAS_MOVE"               # Move keyword to different color
    THRESHOLD_ADJUST = "THRESHOLD_ADJUST"   # Adjust scoring thresholds (future)

class ProposalStatus(StrEnum):
    PENDING = "PENDING"                     # Awaiting human review
    APPROVED = "APPROVED"                   # Approved, not yet applied
    REJECTED = "REJECTED"                   # Rejected by human
    APPLIED = "APPLIED"                     # Successfully applied
```

---

## API Endpoints

### POST `/api/v1/alias-mining/analyze`

Analyze feedback records to generate improvement proposals.

**Request:**
```json
{
  "min_frequency": 3,
  "min_confidence": 0.60,
  "limit": 10
}
```

**Response:**
```json
{
  "status": "ok",
  "proposals_generated": 5,
  "total_feedback_analyzed": 150,
  "proposals": [
    {
      "id": "uuid",
      "proposal_type": "ALIAS_MOVE",
      "status": "PENDING",
      "base_color": "red",
      "keyword": "ruby",
      "suggested_base_color": "purple",
      "frequency": 7,
      "confidence": 0.86,
      "rationale": "Keyword 'ruby' appears in 7 corrections where reviewers prefer 'purple'...",
      "estimated_impact": "Moving 'ruby' from 'red' to 'purple' may improve accuracy for ~7 mappings (MEDIUM impact).",
      "created_at": "2026-06-11T14:32:00Z"
    }
  ]
}
```

**Parameters:**
- `min_frequency` (default: 3) — Only consider keywords appearing in 3+ corrections
- `min_confidence` (default: 0.60) — Only propose if 60%+ of occurrences were corrections
- `limit` (default: null) — Max number of proposals to generate (sorted by frequency/confidence)

**Behavior:**
1. Queries all feedback records with `action: "CORRECT"`
2. Extracts keyword tokens from original and suggested impressions
3. Maps tokens to base colors
4. Identifies patterns: "keyword X always appears when humans reject color A for color B"
5. Generates proposals above thresholds
6. Persists proposals to `alias_mining_proposals` collection

---

### GET `/api/v1/alias-mining/proposals`

List all alias mining proposals, optionally filtered by status.

**Query Parameters:**
- `status` (optional) — Filter by: PENDING, APPROVED, REJECTED, APPLIED

**Response:**
```json
{
  "total": 5,
  "proposals": [
    {
      "id": "uuid",
      "proposal_type": "ALIAS_MOVE",
      "status": "PENDING",
      "base_color": "red",
      "keyword": "ruby",
      "suggested_base_color": "purple",
      "frequency": 7,
      "confidence": 0.86,
      "rationale": "...",
      "estimated_impact": "...",
      "created_at": "2026-06-11T14:32:00Z"
    }
  ]
}
```

---

### POST `/api/v1/alias-mining/proposals/{proposal_id}/apply`

Apply a proposal by updating `alias_overrides.yaml` with the new keyword mapping.

**Request:**
```json
{
  "reviewer": "analyst@target.com",
  "notes": "Approved based on feedback review"
}
```

**Response:**
```json
{
  "status": "ok",
  "proposal_id": "uuid",
  "message": "Proposal applied: 'ruby' moved to 'purple' in alias_overrides.yaml"
}
```

**Behavior:**
1. Load the target proposal from DB
2. Check status is not already APPLIED
3. Read current `alias_overrides.yaml`
4. Add keyword to target color's list
5. Write updated file
6. Mark proposal as APPLIED with timestamp

**Files Modified:**
- `config/alias_overrides.yaml` — New entry or updated color list

**Effect:**
- Next matching run will use updated keywords
- `get_merged_keyword_map()` merges this at runtime
- No restart needed

---

## Usage Workflow

### Phase 1: Collect Feedback (2 weeks)

Reviewers use the Streamlit UI to review and correct mappings.

```
POST /feedback {action: "CORRECT", original: "MAROON", suggested: "PURPLE"}
POST /feedback {action: "CORRECT", original: "RUBY RED", suggested: "PURPLE VIOLET"}
...
```

Each correction is stored with full context in the `feedback` collection.

### Phase 2: Analyze & Propose (1 hour)

```bash
POST /api/v1/alias-mining/analyze \
  {min_frequency: 3, min_confidence: 0.60}
```

Output:
```
Analyzing 450 feedback records...
Found 12 keyword patterns above threshold
Generated 8 proposals:
  1. ruby (red→purple): frequency=7, confidence=86%
  2. maroon (red→purple): frequency=6, confidence=83%
  3. crimson (red→purple): frequency=5, confidence=80%
  ...
```

### Phase 3: Review & Approve (15 min)

Analyst reviews proposals:

```bash
GET /api/v1/alias-mining/proposals?status=PENDING
```

Reviews rationale, estimated impact, and supporting feedback IDs.

If confident:
```bash
POST /api/v1/alias-mining/proposals/{id1}/apply
POST /api/v1/alias-mining/proposals/{id2}/apply
POST /api/v1/alias-mining/proposals/{id3}/apply
```

### Phase 4: Test & Deploy (1 hour)

```bash
# Test with shadow batch
POST /api/v1/mappings/run {shadow: true, batch_id: "test_new_keywords"}

# Compare shadow vs previous prod batch
POST /api/v1/shadow-compare \
  {shadow_batch: "test_new_keywords", prod_batch: "batch_xyz"}
```

If metrics improve:
```bash
# Deploy to prod
POST /api/v1/mappings/run {use_llm: true}
```

---

## Implementation Details

### Service Methods

#### `analyze(request: AliasMiningAnalyzeRequest) → AliasMiningAnalyzeResponse`

Async wrapper that delegates to `_analyze_sync()`.

#### `_analyze_sync(request) → AliasMiningAnalyzeResponse`

Main analysis pipeline:
1. Load all CORRECT feedback from DB
2. Call `_extract_keyword_patterns()` to build correction stats
3. Call `_generate_proposals()` to create proposals
4. Persist proposals to DB
5. Return response with proposal list

#### `_extract_keyword_patterns(feedback_records) → dict[str, KeywordCorrection]`

For each feedback record:
1. Tokenize original and suggested impression names
2. Map tokens to base colors using `self._keyword_map`
3. Detect if original color was wrong (not in suggested colors)
4. Record: keyword, frequency, which color was preferred instead

Returns: `{keyword: KeywordCorrection}` tracking patterns

#### `_generate_proposals(keyword_corrections, min_frequency, min_confidence, limit) → list[AliasMiningProposal]`

For each keyword with sufficient signal:
1. Filter by frequency threshold
2. Filter by correction_rate (% of occurrences that were corrections)
3. Identify most common target color
4. Skip if target == current (no change needed)
5. Create proposal with rationale and impact estimate
6. Sort by frequency/confidence, apply limit
7. Return proposals

#### `_apply_proposal(proposal_id) → dict`

Synchronously updates `alias_overrides.yaml`:
1. Load proposal from DB
2. Check not already applied
3. Read current `alias_overrides.yaml`
4. Add keyword to target color's list
5. Write file back
6. Mark proposal as APPLIED
7. Return status

#### `_estimate_impact(keyword, current_color, target_color, frequency) → str`

Classification:
- frequency ≥ 10 → HIGH impact
- frequency ≥ 5 → MEDIUM impact
- frequency < 5 → LOW impact

---

## Keyword Extraction Logic

### Tokenization

The service uses `plm_tcin_mapper.matching.color_keywords.tokenize()` to break impression names into tokens:

```python
tokenize("ROMANTIC MAROON HEATHER")
# → ["romantic", "maroon", "heather"]

tokenize("LIGHT-PURPLE-OMBRE")
# → ["light", "purple", "ombre"]
```

Removes:
- Stop words (a, the, of, etc.)
- Numbers and units
- Size/pattern indicators

### Color Mapping

Tokens are matched against `KEYWORD_TO_BASE` dictionary:

```python
KEYWORD_TO_BASE = {
    "maroon": "red",
    "ruby": "red",
    "purple": "purple",
    "violet": "purple",
    ...
}
```

This dictionary is built from `BASE_COLOR_MAP` and merged with `alias_overrides.yaml` at runtime.

### Correction Detection

A keyword is "problematic" if:
- It appears in the original impression
- Its current base color is in `original_colors`
- That base color is NOT in `suggested_colors`

Example:
```
Original: "RUBY RED" → tokens=[ruby, red] → colors={red}
Suggested: "PURPLE VIOLET" → tokens=[purple, violet] → colors={purple}

ruby: original_color=red, suggested_colors={purple}
      is_correction = (red in {red}) AND (red NOT in {purple})
                    = TRUE
      → Record: ruby caused a correction from red to purple
```

---

## Configuration

### Environment

- `APP_CONFIG_DIR` (default: `config`) — Directory for `alias_overrides.yaml`

### Thresholds

Adjust in API request or create new proposals with different parameters:

```json
POST /alias-mining/analyze
{
  "min_frequency": 5,        # Require 5+ corrections
  "min_confidence": 0.75,    # Require 75%+ correction rate
  "limit": 20                # Top 20 proposals
}
```

---

## Example: End-to-End Scenario

### Situation

Users keep correcting "MAROON" matches from red to purple:

```
Feedback 1: matched=DARK RED, corrected=MAROON PURPLE
Feedback 2: matched=BURGUNDY WINE, corrected=MAROON PURPLE
Feedback 3: matched=SCARLET CRIMSON, corrected=MAROON PURPLE
```

### Analysis Run

```bash
POST /api/v1/alias-mining/analyze {min_frequency: 3, min_confidence: 0.6}

Analysis:
  - Found 3 feedback records mentioning "maroon"
  - All 3 involved corrections from red → purple
  - Confidence: 100% (3/3 were corrections)
  - Frequency: 3
  - Passes: min_frequency=3, min_confidence=0.6
  
Generated proposal:
  - keyword: "maroon"
  - base_color: "red"
  - suggested_base_color: "purple"
  - confidence: 1.0
  - rationale: "Keyword 'maroon' appears in 3 corrections where reviewers prefer 'purple'. Correction rate: 100%"
  - estimated_impact: "Moving 'maroon' from 'red' to 'purple' may improve matching accuracy for ~3 mappings (LOW impact)."
```

### Approval & Application

```bash
POST /api/v1/alias-mining/proposals/{proposal_id}/apply

Updates alias_overrides.yaml:
  purple:
    - violet
    - lavender
    - ... existing keywords ...
    - maroon    # ← NEW

File written to config/alias_overrides.yaml
```

### Test & Deploy

```bash
POST /api/v1/mappings/run {shadow: true, batch_id: "with_maroon_fix"}

Shadow run with updated keywords...
Results: correction_rate dropped 0.35 → 0.28 ✓

Deploy to production with confidence.
```

---

## Testing

Unit tests cover:
- `KeywordCorrection` class behavior
- Pattern extraction from feedback
- Proposal generation with thresholds
- Impact estimation
- Service integration with mocked DB

Run tests:
```bash
make test-unit  # All unit tests
uv run pytest tests/unit/test_alias_mining.py -v  # Just alias mining tests
```

---

## Future Enhancements

### Gap #2b: Threshold Tuning (v2.1)

Analyze `correction_rate` trends to propose threshold adjustments:
- If correction_rate > 0.30, lower `auto_confirm_threshold` to catch more edge cases
- If pct_high < 0.40, raise `llm_fallback_threshold` to disambiguate earlier

### Gap #2c: A/B Testing Framework (v2.2)

Integrate with Shadow Mode (Gap #7) for automated proposal validation:
1. Generate proposal
2. Apply to shadow batch
3. Compare metrics vs baseline
4. Auto-approve if p-value < 0.05
5. Auto-reject with analysis if degradation detected

### Gap #2d: Keyword Addition (v2.3)

Extend proposal types to suggest NEW keywords (currently only ALIAS_MOVE):
- Extract tokens from suggested impressions
- Find new tokens never seen in training data
- Propose adding them to target color's keyword list

---

## Troubleshooting

### No Proposals Generated

Check:
1. Do you have CORRECT feedback records? Query:
   ```
   db.feedback.count({action: "CORRECT"})
   ```

2. Are thresholds too strict?
   ```bash
   POST /alias-mining/analyze {min_frequency: 1, min_confidence: 0.3}
   ```

3. Do corrected impressions share common tokens?
   - If suggestions are completely different, no pattern to extract

### Proposal Not Applying

Check:
1. Config directory exists: `ls -la config/`
2. `APP_CONFIG_DIR` env var set correctly
3. File permissions allow write: `touch config/alias_overrides.yaml`
4. YAML syntax valid after update

### Changes Not Taking Effect

Remember:
- Keyword mappings are loaded at startup
- Changes apply to next matching run automatically
- No server restart needed (merged at query time)

---

## Deployment Checklist

- [ ] Unit tests pass: `make test-unit`
- [ ] Integration tests pass: `make test-int`
- [ ] Example workflow tested end-to-end
- [ ] `APP_CONFIG_DIR` set in deployment
- [ ] `config/` directory writable by service
- [ ] Monitoring for proposal creation rate
- [ ] Alert if no proposals generated > 2 weeks
- [ ] Document alias override changes in runbook

---

## Success Metrics for v2

- Proposals generated within 1 hour of analysis request
- ≥80% of applied proposals improve correction_rate
- ≥50% of reviewers approve generated proposals
- Correction rate trending downward after each cycle
- Mean time to deploy keyword improvements < 4 hours

---

**Document authored:** 2026-06-11  
**Implementation status:** ✅ COMPLETE  
**Ready for:** Production deployment  
**Depends on:** Feedback loop (Gap #5, #6 — COMPLETE)  
**Unblocks:** Threshold tuning (Gap #3), Shadow comparison (Gap #7)
