# TCIN Impression Mapper — User Flows & Workflows

**Document Purpose:** Guide users on how to use each page of the UI and describe typical workflows for different user types.

**Last Updated:** June 2026  
**Status:** Complete

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Page Descriptions](#page-descriptions)
3. [User Types & Roles](#user-types--roles)
4. [Workflow Scenarios](#workflow-scenarios)
5. [Decision Trees](#decision-trees)
6. [Daily Routines](#daily-routines)
7. [FAQ](#faq)

---

## System Overview

### What is TCIN Impression Mapper?

A human-in-the-loop system that maps **Guest-Facing TCIN Colors** (e.g., "Navy Blue") to **Design Impression Names** (e.g., "OCEAN NIGHT"). The system uses:

1. **Deterministic Matching** — Rule-based (Hungarian algorithm + fuzzy string matching)
2. **LLM Fallback** — When deterministic is ambiguous
3. **Human Review** — For low-confidence matches to train the system

### Core Data Flow

```
CSV Data (TCIN + Impressions)
        ↓
    [Ingest] ← Data Pipeline page
        ↓
  MongoDB (raw data)
        ↓
  [Matching Pipeline] ← Data Pipeline page
        ↓
  Mappings + Confidence Scores
        ↓
  [Human Review] ← Review Queue, Department View, PID Search pages
        ↓
  Feedback (Confirm/Reject/Correct)
        ↓
  [Train System] ← Aliases, thresholds, LLM examples updated
        ↓
  [Evaluate] ← Evaluation Metrics, Improvement Tracker pages
```

---

## Page Descriptions

### Group 1: Core Review & Browse (Main Workflow)

#### **1. Search by PID** ⭐ (Default landing page)

**Purpose:** Find and review mappings for a specific Product ID  
**Access:** Homepage or sidebar  
**Who uses it:** Anyone reviewing a known PID

**How it works:**
```
1. Enter PID (e.g., PID-0ABC12)
2. System loads all TCIN → Impression mappings for that PID
3. Mappings grouped by TCIN color (guest-facing)
4. Each color group shows:
   - Color name and family
   - Assigned impression (design name)
   - Confidence % (green/yellow/red)
   - Variation size (design size)
5. Click "✏️ Review PID" to edit:
   - Change assigned impression
   - Review & confirm corrections
   - Save (marked as CORRECTED in MongoDB)
```

**Example:**
- PID = `PID-0L20P5` (a men's shirt)
- Groups:
  - Blue / Navy → OCEAN NIGHT (87% confidence) ✅
  - White / Off-White → CREAM (64% confidence) ⚠️ [user corrects to IVORY]
  - Red / Crimson → no match (45% confidence) ❌ [user assigns CARDINAL RED]

**When to use:**
- "I know the product ID and want to fix it quickly"
- "A customer complained about a specific PID's color mapping"
- "Let me spot-check this random PID"

---

#### **2. Department View**

**Purpose:** Browse all products in a department + batch review  
**Access:** Sidebar under main group  
**Who uses it:** Department managers, batch workflows

**How it works:**
```
1. Select Department (e.g., 214 = Menswear)
2. Optional filters:
   - PID prefix (e.g., "PID-009E")
   - Status (All / Needs Review / Confirmed / Rejected / Corrected)
3. See list of PIDs sorted by worst confidence first
4. Each row shows:
   - PID name + avg confidence %
   - Status icon (⚠️ = Needs Review, ✅ = Good)
   - Glimpse: top 3 color → impression pairs
   - Note: "🔄 Overridden" if you edited this session
5. Click row to expand and review inline (same as PID Search)
6. Session state: "Expand all by default" toggle in Admin page
```

**Example workflow:**
```
Dept 214 (Menswear) has 47 products
↓
Filter by "Needs Review" → 12 products need attention
↓
Expand first 3 → quickly fix color assignments
↓
Remaining 9 are too complex → go to Review Queue instead
```

**When to use:**
- "I'm the Menswear owner — let me fix our worst products"
- "We need to verify all products in a department"
- "Show me only items that need review"

---

#### **3. Review Queue** ⭐⭐ (MOST IMPORTANT FOR SYSTEM TRAINING)

**Purpose:** Structured queue of low-confidence mappings; each card = one decision  
**Access:** Sidebar under main group  
**Who uses it:** Dedicated reviewers, quality specialists

**How it works:**

**Step 1: Load & Filter**
```
Select Queue Type:
├─ NO_MATCH: No impression assigned (confidence < 75%)
├─ NEEDS_REVIEW: Needs human decision (confidence 50-75%)
├─ NEEDS_SPOT_CHECK: LLM tried but uncertain (confidence 70-85%)
└─ All Pending: Everything needing review

Optional: Filter by Match Round
├─ GREEDY: High-confidence direct match
├─ HUNGARIAN: Optimal global assignment
├─ FALLBACK: Structural mismatch (more TCINs than impressions)
└─ LLM: LLM attempted disambiguation

Click "Load Queue" → Loads up to 100 items
```

**Step 2: Navigate & Review**
```
Progress Bar:
  Reviewed 12 of 100 loaded | 88 remaining
  [===========--------] 12%

Navigation:
  [← Prev] [Card 13 of 100] [Next →]
```

**Step 3A: NO_MATCH Card** (when mapping.status == "NO_MATCH")
```
Header:
  ⛔ No Match Found · PID: PID-0ABC12 / TCIN: 12345678
  Confidence: 42% (LOW tier)

Left Column (TCIN Details):
  - Color family: BLUE
  - Color name: NAVY
  - Size: MEDIUM
  - Departments: 214
  - Match round: ⚠️ FALLBACK (Structural mismatch)
  - Confidence bar: [=====----------] 42% LOW

Right Column (Assign Impression):
  Engine top candidates (ranked):
    🟢 OCEAN NIGHT (84%)
    🔵 DEEP BLUE (76%)
    🟡 SKY BLUE (68%)
    
  Dropdown: [Select impression ▼]
    - OCEAN NIGHT (top candidate)
    - DEEP BLUE
    - SKY BLUE
    - [All impressions for this PID...]
  
  Notes: [Why is this the right impression?]
  
  Buttons:
    [✓ Assign Impression] [Skip]
```

**Step 3B: Standard Review Card** (when status == "NEEDS_REVIEW" or "NEEDS_SPOT_CHECK")
```
Header:
  🟡 PID: PID-0ABC12 / TCIN: 12345678
  Confidence: 72% (GOOD tier)

Left Column (TCIN Details):
  - Color family: BLUE
  - Color name: NAVY
  - Size: MEDIUM
  - Departments: 214

Right Column (Matched Impression Details):
  - Impression: OCEAN NIGHT
  - Size: M
  - Match round: 🔢 HUNGARIAN
  - LLM note: "Chose OCEAN NIGHT over SKY BLUE due to color family"

Confidence bar: [===============------] 72% GOOD

Possible Impressions (engine candidates):
  🟢 OCEAN NIGHT — 72% (current match)
  🔵 DEEP BLUE — 69%
  🟡 SKY BLUE — 65%

Your Decision:
  [○ Confirm] [○ Reject] [● Correct]
  
  Impression (candidates first, then remaining):
    [OCEAN NIGHT ▼] (pre-populated with current)
  
  Notes: [Why are you making this decision?]

Outcome Banner (live preview):
  ┌─ Marking as WRONG — providing correction ─────────┐
  │ Original: OCEAN NIGHT → Correct: DEEP BLUE         │
  │ Both the rejection and the correction are recorded.│
  └───────────────────────────────────────────────────┘

Buttons:
  [✏ Submit Correction] (type="primary")
```

**Actions Explained:**

| Action | What You're Saying | Signal Sent to System |
|--------|---|---|
| **Confirm** | "Engine got this right" | ✓ Correct match (trains signal accuracy) |
| **Reject** | "Engine got this wrong" | ✗ Wrong match (lowers signal accuracy) |
| **Correct** | "Wrong match, here's the right one" | ✗ Wrong + ✓ Correction (trains both signals + aliases) |

**When to use:**
- "I'm doing a dedicated review session"
- "I want to systematically train the system"
- "I want to filter by match round or confidence tier"

**Expected Time per Card:**
- NO_MATCH: 30 seconds (pick from candidates)
- Standard: 45 seconds (read current, decide action, select correction)
- With notes: 60 seconds
- **Goal: 30-40 cards per hour**

---

### Group 2: Data Management

#### **4. Data Pipeline**

**Purpose:** Load CSV data and run matching algorithm  
**Access:** Sidebar under "Data" group  
**Who uses it:** Data engineers, ops team

**Tab 1: Ingest Data**

```
Inputs:
  Data directory path: [./apps/plm-tcin-mapper/data/normalized]
  ☐ Skip existing

Button: [▶ Run Ingestion]

Output (after success):
  TCIN Records: 15,234
  Variation Records: 8,976
  Skipped: 120
  Errors: 3

Success message: ✅ Ingestion complete!
```

**How ingestion works:**
- Scans directory for CSV files
- Identifies by headers (TCIN_REQUIRED, VARIATION_REQUIRED, ERROR_REQUIRED)
- Bulk upserts into MongoDB (replaces by PID+TCIN)
- Skips rows with missing required fields

---

**Tab 2: Run Mapping Pipeline**

```
Inputs:
  PID filter (optional): [PID-0ABC12]
  Department filter (optional): [214]
  ☐ Dry run (test without saving)

Button: [▶ Run Matching]

Output (after success):
  PIDs Processed: 450
  Mappings Created: 2,100
  AUTO_CONFIRM: 1,850 (88% confidence)
  NEEDS_REVIEW: 250 (50-88% confidence)

Success message: ✅ Matching complete!
```

**How matching works:**
- For each PID, loads TCIN records + variation impressions
- Runs deterministic engine (Hungarian + fuzzy match)
- Assigns confidence score + tier (HIGH/GOOD/FAIR/LOW)
- If score < LLM threshold, calls LLM for disambiguation
- Auto-confirms if confidence ≥ auto_confirm_threshold (typically 85%)
- Rest marked NEEDS_REVIEW

---

**When to use:**
- "We have new CSV files to load"
- "We changed alias config and need to re-run matching"
- "Let me test this change in dry-run mode first"

---

### Group 3: Analytics & Admin

#### **5. Evaluation Metrics**

**Purpose:** System quality snapshot + diagnostics  
**Access:** Sidebar under "Analytics" group  
**Who uses it:** Product managers, system owners

**Overview Tab:**
```
KPI Row (5 metrics):
  Total Mappings: 2,500,000
  Correction Rate: 24% ↓ Better (target <20%)
  Avg Confidence: 0.768
  HIGH Tier %: 62% ↑ Better (target >60%)
  Calibration Error: 0.087

Status Distribution (2 charts):
  [Bar chart: By Status] [Bar chart: By Confidence Tier]

Guardrail Alerts:
  ⚠️ Correction rate 24% is above target 20%
  ❌ LOW tier 3% is concerning

Confidence Analysis:
  HIGH confidence actual correction rate: 8% (good — should be <15%)
  LOW confidence actual correction rate: 62% (expected — should be 50-80%)
```

---

**Per-Signal Analysis Tab:**
```
Table of scoring signals:
  Signal Name | Occurrences | Corrections | Correction Rate | Avg Conf
  ────────────┼─────────────┼─────────────┼─────────────────┼──────────
  exact_token |      450,000 |      8,100  |        1.8%     │ 0.92
  keyword     |      680,000 |     51,000  |        7.5%     │ 0.79
  fuzzy_match |      950,000 |    380,000  |       40.0%     │ 0.52
  fallback    |      420,000 |    185,000  |       44.0%     │ 0.49

Signal Health Indicators (colored badges):
  exact_token: ✅ Strong
  keyword: ✓ Good
  fuzzy_match: ⚠️ Weak
  fallback: ❌ Very Weak

Recommendations:
  "fuzzy_match and fallback signals are weak — consider lowering thresholds"
```

---

**Per-Department Analysis Tab:**
```
Table:
  Department | Total | HIGH % | Correction Rate | Avg Confidence
  ──────────┼───────┼────────┼─────────────────┼────────────────
  214        |  45k  | 68%    | 18%             | 0.79
  215        |  38k  | 52%    | 32%             | 0.71
  220        |  32k  | 45%    | 42%             | 0.64
  221        |  28k  | 71%    | 12%             | 0.82

Department Health:
  214: ✅ Excellent
  215: ⚠️ Needs Work
  220: ❌ Critical
  221: ✅ Excellent

Recommendations:
  "220 has high error rate — consider focused alias mining for that category"
```

---

**LLM Impact Tab:**
```
KPIs:
  LLM Calls: 180,000
  LLM Correction Rate: 22%
  Deterministic Correction Rate: 31%
  LLM Improvement: -9% (hurting performance)

Detailed Comparison Table:
  Metric | LLM | Deterministic
  ──────┼─────┼──────────────
  Calls | 180k | 2,320k
  Corrections | 39,600 | 719,200
  Corr Rate | 22% | 31%
  Avg Conf | 0.68 | 0.79

Recommendation:
  "❌ LLM is hurting performance (22% vs 31%). Review LLM prompts or consider disabling."
```

---

**Trend Tab** (New!):
```
Line chart (last 30 evals):
  Y-axis: Percentage
  X-axis: Date
  Lines:
    — Avg Confidence (trending up 0.745 → 0.768)
    — HIGH % (trending up 58% → 62%)

Full Trend Table (with expander):
  Date | Avg Confidence | HIGH % | LOW %
  ─────┼────────────────┼────────┼──────
  6/1  | 0.745          | 58%    | 3%
  6/2  | 0.748          | 59%    | 3%
  6/3  | 0.751          | 59%    | 3%
  ...
  6/10 | 0.768          | 62%    | 3%

Interpretation:
  ✅ Upward trend — improvements are working
```

---

**When to use:**
- "I want to see overall system health"
- "Did our recent changes help?"
- "Which departments need the most work?"
- "Is the LLM helping or hurting?"

---

#### **6. Threshold Optimizer**

**Purpose:** Propose & test threshold changes  
**Access:** Sidebar under "Analytics"  
**Who uses it:** Advanced users, system tuners  
**Status:** Stubbed (buttons say "Coming soon")

---

#### **7. Alias Mining Dashboard**

**Purpose:** Review & approve keyword alias proposals  
**Access:** Sidebar under "Analytics"  
**Status:** Implemented (no changes to workflow)

**Example workflow:**
```
System detected: Reviewers keep correcting "TEAL" to "AQUA"
↓
Proposal: Add "TEAL" as alias to AQUA color family
↓
You review: 5 human corrections support this (evidence)
↓
Approve → Alias written to config/alias_overrides.yaml
↓
Next matching run: "TEAL" now recognized as AQUA ✓
```

---

#### **8. LLM Quality**

**Purpose:** Monitor LLM cost, latency, accuracy, hallucinations  
**Access:** Sidebar under "Analytics"  
**Status:** Implemented (no changes to workflow)

---

#### **9. Improvement Tracker** (New!)

**Purpose:** Track impact of each improvement (before/after metrics)  
**Access:** Sidebar under "Analytics"  
**Who uses it:** Engineering team validating changes

**How it works:**
```
Recent Improvements (expandable cards):

1. alias_added (6/8, 2:14 PM)
   Confidence Δ: +0.045 ✅
   HIGH Tier Δ: +3% ✅
   Needs Review Δ: -47 ✅
   PIDs Affected: 127
   Note: "Added TEAL → AQUA alias"

2. threshold_changed (6/7, 4:22 PM)
   Confidence Δ: -0.012 ⚠️
   HIGH Tier Δ: -1%
   Needs Review Δ: +82
   PIDs Affected: 312
   Note: "Lowered fuzzy_match threshold from 0.65 → 0.60"

3. model_updated (6/6, 9:00 AM)
   Confidence Δ: +0.008
   HIGH Tier Δ: +1%
   Needs Review Δ: -25
   PIDs Affected: 156
   Note: "Updated LLM prompt with new few-shot examples"
```

**Manual Logging Form:**
```
Change Type: [alias_added / threshold_changed / model_updated / manual_review]
Color Family (optional): [BLUE]
Description: [What changed?]
[Log Improvement]
```

**When to use:**
- "What changed last week?"
- "Did this improvement actually help?"
- "Show the team the before/after metrics"

---

#### **10. System Admin**

**Purpose:** App settings + database health  
**Access:** Sidebar under "Analytics"  
**Who uses it:** Admin, DevOps, system owners

**Features:**
```
Department View Settings:
  ☑️ Expand all PID rows by default
  (Toggle controls st.session_state.expand_default)

Confidence Color Scale (informational):
  [HIGH ≥85%] [GOOD 70-85%] [FAIR 50-70%] [LOW <50%]

MongoDB Status:
  ✅ Connected
  
  Metrics:
    Total Mappings: 2,500,000
    Total Feedback: 18,432
  
  Full Counts (expandable):
    Mappings: 2,500,000
    TCIN Records: 2,100,000
    Variation Records: 1,850,000
    Feedback: 18,432
```

**When to use:**
- "Is MongoDB up?"
- "How much data do we have?"
- "Let me toggle the default expand behavior"

---

## User Types & Roles

### 1. Color Expert / Reviewer (Primary User)
**Time commitment:** 1-2 hours/day  
**Primary pages:** Review Queue, Department View  
**Goal:** Confirm/reject/correct mappings; train the system

**Typical session:**
- Start Review Queue
- Work through 30-40 cards in 45 min
- Each action: Confirm (2 sec) / Reject (5 sec) / Correct (15 sec)
- Impact: ~200 feedback records per week

**Responsibilities:**
- Make accurate decisions (your corrections train the system)
- Add notes explaining ambiguous decisions
- Report systematic patterns to engineering

---

### 2. Department Manager (Team Lead)
**Time commitment:** 2-3 hours/week  
**Primary pages:** Department View, Evaluation Metrics  
**Goal:** Ensure their department's products are mapped correctly

**Typical session:**
- Check Evaluation Metrics for their department status
- Go to Department View, filter by department
- Review worst products inline
- Use Review Queue as fallback for complex items

**Responsibilities:**
- QA their department's mappings
- Escalate patterns to color expert
- Report quality metrics to stakeholders

---

### 3. Data Engineer / DevOps
**Time commitment:** 30 min - 2 hours/week  
**Primary pages:** Data Pipeline, Admin, Evaluation Metrics  
**Goal:** Load data, run pipelines, monitor health

**Typical workflow (weekly):**
- Monday: Load new CSV files (Data Pipeline → Ingest)
- Monday: Run matching pipeline (Data Pipeline → Mapping)
- Friday: Run fresh eval (Evaluation Metrics → Run Fresh Eval)
- Anytime: Check Admin for MongoDB status

---

### 4. Product Manager
**Time commitment:** 30 min/week  
**Primary pages:** Evaluation Metrics, Improvement Tracker  
**Goal:** Understand system quality trends, report to stakeholders

**Typical weekly meeting:**
1. Open Evaluation Metrics
2. Check current KPIs (correction rate, avg confidence, HIGH %)
3. View Trend tab (last 5 days)
4. Review Improvement Tracker (what changed this week?)
5. Present to team: "We went from 28% → 24% correction rate"

---

### 5. System/Research Analyst
**Time commitment:** Ad hoc  
**Primary pages:** All pages  
**Goal:** Deep investigation of system behavior, root cause analysis

**Example investigation:**
- "Why are department 50 mappings so bad?"
- Evaluation Metrics → Per-Department → Dept 50 = 42% correction rate
- Review Queue → Filter by Dept 50 → manually review 20 items
- Notice pattern: "SAGE color always gets mapped wrong"
- Alias Mining → Check if "SAGE" proposal exists
- If not, go to Alias Mining and check why not
- Department View → Search for PIDs with SAGE
- Manually correct 10 SAGE mappings
- Wait for system to mine the pattern

---

## Workflow Scenarios

### Scenario A: Morning Review Session (30 min)

**User:** Color Expert  
**Goal:** Quick review before meetings  
**Steps:**

```
9:00 AM
├─ Open app (lands on Search by PID)
├─ Check Admin page quickly
│  └─ "MongoDB: Connected, 2.5M mappings"
├─ Sidebar → Department View
│  ├─ Select Department 214 (Menswear)
│  ├─ Filter by "Needs Review" (shows 12 of 47)
│  └─ Expand first 3 rows
│     └─ Each: 2 min to review colors + save corrections
│
├─ Still 9 items needing review (too complex for inline)
├─ Sidebar → Review Queue
│  ├─ Queue type: "All Pending"
│  ├─ Click "Load Queue" (loads 100 items)
│  └─ Work through 10 cards (5 min)
│     └─ Each card: ~30 sec (read, decide, confirm/reject)
│
└─ 9:30 AM: Done! Feedback saved to MongoDB
   └─ Toast: "Reviewed 10 items — great work!"
```

**Outcome:** 13 corrections made, system trained

---

### Scenario B: New Data Arrives (1 hour)

**User:** Data Engineer  
**Goal:** Ingest new data and run matching  
**Steps:**

```
10:00 AM: New CSV files available
├─ Sidebar → Data Pipeline
├─ Tab: Ingest Data
│  ├─ Data directory: "./apps/plm-tcin-mapper/data/normalized"
│  ├─ Skip existing: ☑️
│  └─ Click "Run Ingestion"
│     └─ Output:
│        TCIN Records: 5,000 new
│        Variation Records: 2,400 new
│        Skipped: 120
│        Errors: 3 (investigate later)
│
├─ Tab: Run Mapping Pipeline
│  ├─ PID filter: (blank — process all)
│  ├─ Dept filter: (blank)
│  ├─ Dry run: ☐
│  └─ Click "Run Matching"
│     └─ Output:
│        PIDs Processed: 8,320
│        Mappings Created: 8,320
│        AUTO_CONFIRM: 7,100 (85% confidence)
│        NEEDS_REVIEW: 1,220 (50-85%)
│
├─ 10:45 AM: Run fresh eval
│  ├─ Sidebar → Evaluation Metrics
│  ├─ Click "Run Fresh Eval" button
│  └─ Wait 2 min for computation
│
├─ Check Trend tab
│  └─ "HIGH % went from 62% → 64% ✓"
│
└─ 11:00 AM: Slack message
   └─ "New data loaded: 1,220 mappings need review. Let's tackle these this week."
```

**Outcome:** 8K new mappings ingested & matched; 1.2K flagged for human review

---

### Scenario C: Quality Investigation (2 hours)

**User:** Product Manager + Color Expert  
**Goal:** Root cause analysis of low quality in a department  
**Steps:**

```
Weekly standup: "Department 50 has 42% correction rate. Why?"

Step 1: Quantify the problem
├─ Open Evaluation Metrics
├─ Per-Department Analysis tab
├─ See: Dept 50 = 42% correction rate (target: <20%)
└─ That's 4,200 corrections out of 10,000 mappings

Step 2: Identify patterns
├─ Review Queue
├─ Filter by Dept 50, Queue type "NEEDS_REVIEW"
├─ Manually review 20 items (10 min)
├─ Notice: "SAGE" color appears 8 times
│  └─ All mapped wrong (chosen reds/oranges instead of greens)
└─ Hypothesis: "SAGE" alias missing from GREEN color family

Step 3: Check existing proposals
├─ Sidebar → Alias Mining Dashboard
├─ Search: "SAGE"
├─ If NOT proposed: Go back to Review Queue
│  └─ Manually correct 5 SAGE mappings in Dept 50
│  └─ Log notes: "SAGE should be green, not warm"
│
├─ System will mine pattern (5+ confirmations)
│  └─ Tomorrow: "SAGE → GREEN" proposal appears
│
└─ Or IF already proposed: Approve it

Step 4: Apply and verify
├─ Data Pipeline → Run Mapping (forces re-scoring with new aliases)
│  └─ Mappings updated instantly for new scores
│
├─ Wait 10 min
├─ Evaluation Metrics → Run Fresh Eval
├─ Check Trend: Correction rate Dept 50: 42% → 35% ✓
│
└─ Email team: "SAGE alias improvement saved 700 corrections"
```

**Outcome:** Root cause identified (SAGE alias), 700+ corrections prevented

---

### Scenario D: Weekly Review Meeting

**Participants:** Color Expert, Manager, Data Engineer, PM  
**Duration:** 30 min  
**Steps:**

```
1. Overall Health Check (5 min)
   ├─ Open Evaluation Metrics
   ├─ Overview tab
   ├─ Read aloud:
   │  "Correction rate: 24% (was 26% Monday)"
   │  "Avg confidence: 0.768 (↑ from 0.765)"
   │  "HIGH tier: 62% (↑ from 60%)"
   └─ Conclusion: "Trends are positive"

2. What Changed This Week (5 min)
   ├─ Open Improvement Tracker
   ├─ Review 5 improvements logged:
   │  ├─ Alias: SAGE → GREEN (+0.045 confidence)
   │  ├─ Alias: TEAL → AQUA (+0.032 confidence)
   │  └─ 3 other minor aliases
   └─ Show bar chart trend: Confidence up 0.018 this week

3. Weak Signals (5 min)
   ├─ Evaluation Metrics → Per-Signal Analysis
   ├─ fuzzy_match signal: 40% correction rate (weak!)
   ├─ Discussion: "Should we lower fuzzy_match threshold?"
   ├─ Assign: Data Engineer will test in Threshold Optimizer
   └─ Follow-up meeting: Friday to review shadow test results

4. Department Spotlight (5 min)
   ├─ Evaluation Metrics → Per-Department
   ├─ Best: Dept 221 (12% correction rate) ✅
   ├─ Worst: Dept 220 (42% correction rate) ❌
   ├─ Assign: Color expert to focus on Dept 220 next week
   └─ Task: "Review 50 Dept 220 items in Review Queue"

5. LLM Status (5 min)
   ├─ Open LLM Quality page
   ├─ "LLM accuracy: 82%, cost: $34 this week"
   ├─ "LLM helping? YES — +8% improvement over deterministic"
   └─ Conclusion: "Keep LLM enabled"

6. Next Week (5 min)
   ├─ Color expert: Focus on Dept 220
   ├─ Data engineer: Test fuzzy_match threshold change
   ├─ PM: Monitor trend, report to execs
   └─ Manager: Review Dept 214 daily (15 min)
```

**Outcome:** Team aligned on priorities and progress

---

## Decision Trees

### "Which page should I use?"

```
┌─ START
│
├─ "I know the specific PID"
│  └─> SEARCH BY PID
│
├─ "I know the department"
│  └─> DEPARTMENT VIEW
│
├─ "I want to systematically review low-confidence items"
│  └─> REVIEW QUEUE ⭐ (RECOMMENDED FOR QUALITY)
│
├─ "I need to load new CSV files"
│  └─> DATA PIPELINE → Ingest Data
│
├─ "I need to run the matching algorithm"
│  └─> DATA PIPELINE → Run Mapping
│
├─ "I want to see overall system health"
│  └─> EVALUATION METRICS
│      (also: Improvement Tracker, Trend tab)
│
├─ "I want to review keyword alias proposals"
│  └─> ALIAS MINING DASHBOARD
│
├─ "I want to monitor LLM cost/accuracy"
│  └─> LLM QUALITY
│
├─ "I want to propose & test threshold changes"
│  └─> THRESHOLD OPTIMIZER
│
├─ "I want to track what improved this week"
│  └─> IMPROVEMENT TRACKER
│
└─ "I need to change app settings"
   └─> SYSTEM ADMIN
```

---

### "How do I fix a low-quality department?"

```
START: Department X has high correction rate (>30%)

Step 1: MEASURE
├─ Evaluation Metrics → Per-Department tab
├─ See: Dept X correction rate = 42%
└─ That's 4,200 errors out of 10,000 mappings

Step 2: SAMPLE
├─ Review Queue → Filter by Dept X
├─ Manually review 30 random items
├─ Take notes on patterns you see
└─ Examples: "SAGE maps wrong 8/30 times", "Color X always confused with Y"

Step 3: HYPOTHESIS
├─ Hypothesis: "Missing or weak aliases"
├─ Example: "SAGE should be in GREEN family but isn't recognized"
└─ Next: Check if system has this alias

Step 4: CHECK & FIX
├─ Alias Mining Dashboard
├─ Search for pattern (e.g., "SAGE")
│
├─ IF NOT proposed yet:
│  ├─ Go back to Review Queue
│  └─ Manually correct 5+ SAGE items
│     └─ Triggers system mining (5+ = proposal threshold)
│
└─ IF already proposed:
   └─ Click "✅ Approve" (done!)

Step 5: VERIFY
├─ Data Pipeline → Run Mapping (forces re-score with new aliases)
├─ Wait 10 min
├─ Evaluation Metrics → Run Fresh Eval
├─ Trend tab: Check Dept X correction rate
│  └─ Did it improve? ✓ Yes → Success! ✗ No → Dig deeper
│
└─ Repeat if needed with other patterns

END: Dept X correction rate reduced
```

---

## Daily Routines

### For a Team (2 Color Experts + 1 Data Engineer)

#### **Daily (9:00-10:30 AM)**
- **9:00:** Check System Admin → MongoDB status ✓
- **9:05:** Open Review Queue → work 30 min (review 30-40 cards)
- **9:35:** Check Evaluation Metrics → any guardrail alerts?
- **9:40:** Department View → review worst department (5 min inline edits)
- **9:45:** Done for morning!

#### **Afternoon (2:00-3:00 PM)**
- Review Queue again (same 30-40 cards) OR
- Department View (different department)
- Goal: 60-80 reviews per day across team

#### **Weekly (Friday 3:00-4:00 PM)**
- Run Evaluation Metrics → "Run Fresh Eval"
- Check Trend tab (last 5 days)
- View Improvement Tracker (what changed this week?)
- Meeting: Present findings to stakeholders
- Assign: Next week's priorities

#### **As-Needed (Data Drops)**
- Data Engineer: Data Pipeline → Ingest → Run Mapping
- Notify team: "X new mappings, Y need review"
- Color Experts: Adjust focus to new items

---

## FAQ

### Q: How do I know if I'm making good decisions in Review Queue?

**A:** You're making good decisions if:
- You're consistent (same color/impression pair always gets the same answer)
- You understand the difference (guest-facing TCIN color vs design impression name)
- You add notes for ambiguous decisions (helps future reviewers)
- Your feedback is used in system proposals (Alias Mining, Threshold Optimizer)

**Tip:** If you're unsure, Skip the card and come back to it later. Quality > speed.

---

### Q: What's the difference between "Correct" and "Reject"?

**A:**
- **Reject:** "Engine got it wrong" (confidence score was too high)
- **Correct:** "Engine got it wrong AND here's the right answer"

Both say "wrong match," but:
- Reject: Trains the system to lower confidence for that signal type
- Correct: Trains the system to lower confidence AND add/improve aliases/LLM examples

**Tip:** Always use "Correct" when you know the right answer. It's more valuable.

---

### Q: How often should I run "Run Fresh Eval"?

**A:**
- **Daily:** No (takes 2-5 min depending on data size; unnecessary)
- **Weekly:** Yes (every Friday, to see if changes helped)
- **After major changes:** Yes (after approving batch of aliases or thresholds)
- **During investigation:** Yes (to validate a hypothesis)

---

### Q: What does "Dry run" do in Data Pipeline?

**A:** Runs the matching algorithm without saving results to MongoDB. Use it to:
- Test a threshold change before applying
- See how many mappings would be affected
- Validate new data without committing

**Example:** "If I lower fuzzy_match threshold from 0.65 → 0.60, how many extra AUTO_CONFIRMs would I get?"

---

### Q: Can I undo a feedback decision?

**A:** No — once you submit Confirm/Reject/Correct, it's saved to MongoDB. 

**If you made a mistake:**
- Go back to Department View or Search by PID
- Click "Review PID"
- Change the impression again (creates a new feedback record)
- The old feedback stays, but the newer one overrides the mapping

---

### Q: What's the difference between "NEEDS_REVIEW" and "NEEDS_SPOT_CHECK" in Review Queue?

**A:**
- **NEEDS_REVIEW:** Low confidence (< 70%), deterministic or LLM failed
- **NEEDS_SPOT_CHECK:** Medium confidence (70-85%), LLM helped but not confident

**In practice:** Both need human review. NEEDS_SPOT_CHECK is slightly better (LLM had a reason).

---

### Q: How do I know if a department is "good" quality?

**A:** Look at Evaluation Metrics → Per-Department Analysis:

| Correction Rate | Status | Interpretation |
|---|---|---|
| < 15% | ✅ Excellent | Very few errors |
| 15-25% | ✓ Good | Acceptable |
| 25-35% | ⚠️ Fair | Needs improvement |
| 35-50% | ❌ Poor | Focus area |
| > 50% | 🔴 Critical | Major issues |

**Action:** If > 30%, investigate patterns (see Decision Tree above).

---

### Q: What should I put in the "Notes" field?

**A:** Explain your reasoning, especially for "Correct" actions:
- ✅ Good: "SAGE is a neutral green-gray, not a warm tone"
- ✅ Good: "Customer feedback: This color is always called NAVY in marketing"
- ❌ Bad: "Wrong" or "No comment"

Notes help:
- Future reviewers understand your decision
- System learn why corrections were made
- Analysts investigate patterns

---

### Q: How long does Evaluation Metrics "Run Fresh Eval" take?

**A:**
- Small dataset (< 500K mappings): 30 seconds
- Medium dataset (500K - 2.5M): 1-2 minutes
- Large dataset (> 2.5M): 3-5 minutes

During eval: Page shows spinner "Computing evaluation metrics…"

---

### Q: Can I run multiple Review Queue sessions in parallel?

**A:** No — Review Queue stores state in `st.session_state`, which is per-browser-session. If you open 2 browser windows:
- Window 1: Queue loaded, reviewing cards
- Window 2: You open Review Queue → loads different queue
- Closing Window 1: Queue state lost

**Best practice:** One Review Queue window at a time.

---

### Q: What's the fastest way to review a department?

**A:**
1. **Best:** Review Queue (30 sec/card, structured queue)
2. **Good:** Department View + inline review (2 min/PID)
3. **Quick check:** Search by PID (if you know the problem PID)

**Time estimates (per 10 items):**
- Review Queue: ~5 min
- Department View inline: ~20 min
- Search by PID: ~10 min

---

## Summary: User Journey Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    TCIN Impression Mapper                        │
│                    Typical User Journey                          │
└─────────────────────────────────────────────────────────────────┘

NEW DATA ARRIVES
    ↓
[Data Pipeline] ← Ingest CSVs
    ↓
[Data Pipeline] ← Run Matching (7,100 AUTO_CONFIRM + 1,220 NEEDS_REVIEW)
    ↓
[Review Queue] ⭐ ← Systematic review of low-confidence items
    ↓
[Feedback Records] ← Confirm/Reject/Correct decisions
    ↓
[Alias Mining] ← System proposes new keywords (5+ confirmations)
    ↓
[Review & Approve] ← Reviewer approves proposals
    ↓
[Data Pipeline] ← Re-run matching with new aliases
    ↓
[Evaluation Metrics] ← Measure impact (confidence ↑, corrections ↓)
    ↓
[Improvement Tracker] ← Log the improvement for stakeholders
    ↓
[Weekly Review] ← Team meets, celebrates wins, plans next focus
    ↓
REPEAT (virtuous cycle of continuous improvement)
```

---

**Document end.**

For questions or updates, contact: engineering@example.com
