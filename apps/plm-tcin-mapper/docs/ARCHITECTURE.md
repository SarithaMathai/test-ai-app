# System Architecture — plm-tcin-mapper

> **Render tip:** All diagrams use [Mermaid](https://mermaid.js.org/). They render natively on GitHub and in VS Code with the *Markdown Preview Mermaid Support* extension.

This document describes `plm-tcin-mapper` as it lives in the `plm-ai-apps` monorepo: a FastAPI microservice backed by MongoDB, sharing infrastructure libraries (`ai-core`, `ai-mongo`, `ai-thinktank`) with the other apps. For the request/response data-flow walkthrough, see [DATA_FLOW_DESIGN.md](DATA_FLOW_DESIGN.md).

---

## Table of Contents
1. [The Problem](#1-the-problem)
2. [Solution Approach](#2-solution-approach)
3. [System Context](#3-system-context)
4. [Component Architecture](#4-component-architecture)
5. [Request Flow](#5-request-flow)
6. [Matching Pipeline — Decision Logic](#6-matching-pipeline--decision-logic)
7. [Data Model](#7-data-model)
8. [Configuration System](#8-configuration-system)
9. [LLM Abstraction Layer](#9-llm-abstraction-layer)
10. [Key Design Decisions](#10-key-design-decisions)

---

## 1. The Problem

Two separate systems describe the same physical product using completely different vocabularies:

```
┌─────────────────────────────────────────────────────────┐
│  System 1 — Guest-Facing (TCIN)                          │
│  PID-009E83  →  TcinId 94447439                          │
│    Color:     Red          (broad family)                │
│    colorName: Maroon       (specific shade)              │
│    Size:      1X                                         │
└─────────────────────────────────────────────────────────┘

                  ??? How do these connect? ???

┌─────────────────────────────────────────────────────────┐
│  System 2 — Design / Manufacturing                       │
│  PID-009E83  →  ImpressionId dd948247-...                │
│    ImpressionName: ROMANTIC RUBY  (creative brand name)  │
│    Size:           1X                                    │
└─────────────────────────────────────────────────────────┘
```

**Why this is hard:**
- Impression names are creative and non-literal (`GOALSETTING GRAY` could map to a gray _or_ a muted blue).
- The same PID can have 15–25 TCIN color/size combinations and 18–30 impression variations.
- A 1:1 assignment is required — one impression per TCIN color, no sharing.
- Some PIDs span baby sizing, plus sizing, and standard sizing in the same dataset.

---

## 2. Solution Approach

```
Deterministic first  →  LLM as fallback  →  Human as safety net
```

1. **Deterministic matching** — color-keyword dictionary + fuzzy string matching + the Hungarian algorithm for a globally-optimal 1:1 assignment. Handles ~70–80% of cases at high confidence, with zero latency and zero cost.
2. **LLM disambiguation** — only for genuinely ambiguous low-confidence cases. Stateless and provider-swappable through `ai-core`'s `LLMClient`; backed by Target's **ThinkTank** gateway.
3. **Human-in-the-loop** — low-confidence mappings surface in the Streamlit operator UI. Reviewer feedback is stored and can promote known-good corrections over time.

---

## 3. System Context

```mermaid
C4Context
    title plm-tcin-mapper — System Context

    Person(reviewer, "Merchandising Reviewer", "Reviews low-confidence mappings, confirms or corrects them via the Streamlit UI")
    Person(engineer, "Engineer / Data Analyst", "Calls the REST API to ingest data, run matching, and read eval snapshots")
    System_Ext(plm_ui, "PLM UI / callers", "Internal services that call the mapping REST API")

    System_Boundary(repo, "plm-ai-apps monorepo") {
        System(mapper, "plm-tcin-mapper", "FastAPI service: deterministic + LLM matching pipeline, REST API on :8001")
        System(ui, "Operator UI", "Optional Streamlit review tool (:8501) — reads Mongo directly")
        System_Ext(aimongo, "ai-mongo (lib)", "Shared Motor + PyMongo client manager")
        System_Ext(aicore, "ai-core (lib)", "Settings, LLMClient interface, logging, exceptions")
        System_Ext(aitt, "ai-thinktank (lib)", "ThinkTank LLM client implementation")
    }

    System_Ext(thinktank, "ThinkTank Gateway", "Target LLM gateway (gemini-1.5-pro) for ambiguous color disambiguation")
    System_Ext(mongo, "MongoDB", "Persistent store: tcin_records, variation_records, mappings, feedback, eval_runs")

    Rel(engineer, mapper, "REST: /ingest, /mappings/run, /eval/run")
    Rel(plm_ui, mapper, "REST: /mappings query")
    Rel(mapper, aicore, "config + LLMClient interface")
    Rel(mapper, aimongo, "read/write collections")
    Rel(mapper, aitt, "disambiguation via LLMClient")
    Rel(aitt, thinktank, "chat/completions (low-confidence only)")
    Rel(aimongo, mongo, "Motor (async) + PyMongo (sync)")
    Rel(reviewer, ui, "review + submit feedback")
    Rel(ui, mongo, "sync reads/writes via ai-mongo")
```

---

## 4. Component Architecture

```mermaid
flowchart TD
    subgraph DATA["📁 Data Layer"]
        NORM["data/normalized/\nchunk_01…chunk_14\ntcin.csv / variation.csv"]
        DB[("MongoDB\ntcin_records\nvariation_records\nmappings\nfeedback\neval_runs")]
    end

    subgraph API["🌐 API Layer  (plm_tcin_mapper/routes + services)"]
        HEALTH["health.py\nGET /health"]
        RINGEST["ingest.py + ingest_service.py\nPOST /api/v1/ingest"]
        RMAP["mappings.py + mapping_service.py\nPOST /api/v1/mappings/run\nGET /api/v1/mappings"]
        REVAL["eval.py + eval_service.py\nPOST /api/v1/eval/run\nGET /api/v1/eval/latest"]
        RFB["feedback.py + feedback_service.py\nPOST /api/v1/feedback"]
    end

    subgraph PIPELINE["⚙️ Pipeline  (plm_tcin_mapper/pipeline/)"]
        INGEST["ingestion.py\nCSV → Mongo bulk upsert\n(header sniffing)"]
        ORCH["orchestrator.py\nrun_batch / match_pid"]
        EVAL["evaluator.py\nmetrics snapshot + guardrails"]
    end

    subgraph MATCHING["🔍 Matching Engine  (plm_tcin_mapper/matching/)"]
        KEYWORDS["color_keywords.py\ncanonical base-color dict\n+ alias overrides"]
        SCORER["scorer.py\ncolor_score(): token / keyword / fuzzy"]
        SIZENORM["size_normalizer.py\nX Large → xl, 2X → 2xl"]
        DET["deterministic.py\nR1 Greedy → R2 Hungarian → R3 Fallback"]
    end

    subgraph LLM["🤖 LLM  (plm_tcin_mapper/llm + ai-core/ai-thinktank)"]
        DISAMB["disambiguator.py\nwhen to call + prompt build"]
        IFACE["ai-core LLMClient.chat(ChatRequest)"]
        TT["ai-thinktank ThinkTankClient"]
        NOOP["NoOpLLMClient (provider=none)"]
    end

    subgraph SHARED["📦 Shared libs"]
        MONGO["ai-mongo\nMongoClientManager\n(Motor + PyMongo)"]
        CONFIG["ai-core Settings\nbase.yaml + env overrides"]
    end

    subgraph UI["🖥️ Operator UI  (plm_tcin_mapper/ui/) — optional"]
        APPUI["streamlit_app.py"]
        PID["pid_lookup.py"]
        DEPT["department_view.py"]
        LLMQ["llm_quality.py"]
    end

    NORM -->|"POST /ingest"| RINGEST --> INGEST -->|"bulk upsert"| DB
    RMAP --> ORCH
    ORCH -->|"load tcin + variation per PID"| DB
    ORCH --> DET
    DET --> KEYWORDS & SCORER & SIZENORM
    DET -->|"low confidence"| DISAMB --> IFACE
    IFACE -->|"provider=thinktank"| TT
    IFACE -->|"provider=none"| NOOP
    ORCH -->|"upsert mappings"| DB
    REVAL --> EVAL -->|"write eval_runs"| DB
    RFB -->|"write feedback + update mapping"| DB
    DB --> UI
    UI -->|"write feedback"| DB

    MONGO -. used by .- API
    MONGO -. used by .- UI
    CONFIG -. used by .- API

    style DATA fill:#e8f4f8,stroke:#2196F3
    style API fill:#e8eef8,stroke:#3F51B5
    style PIPELINE fill:#e8f8e8,stroke:#4CAF50
    style MATCHING fill:#fff8e8,stroke:#FF9800
    style LLM fill:#f8e8f8,stroke:#9C27B0
    style SHARED fill:#f0f0f0,stroke:#607D8B
    style UI fill:#f8e8e8,stroke:#F44336
```

The **API layer** is thin: each route validates a request and delegates to a service. Each service runs the (synchronous, PyMongo-based) pipeline inside `run_in_executor` so the FastAPI event loop is never blocked. The **matching engine** is pure Python with no I/O — which is why its logic is unit-tested in isolation.

---

## 5. Request Flow

```mermaid
sequenceDiagram
    participant C as Caller (PLM / Engineer)
    participant API as FastAPI route
    participant S as Service (thread pool)
    participant O as orchestrator.py
    participant M as matching engine
    participant L as LLMClient (ThinkTank, optional)
    participant DB as MongoDB

    Note over C,DB: Ingestion
    C->>API: POST /api/v1/ingest {chunk}
    API->>S: IngestionService.run()
    S->>DB: bulk upsert tcin_records + variation_records
    S-->>C: {chunks_processed, totals}

    Note over C,DB: Matching
    C->>API: POST /api/v1/mappings/run {pid, use_llm}
    API->>S: MappingService.run()
    S->>O: run_batch(pids)
    loop For each PID
        O->>DB: load tcin_records + variation_records
        O->>M: match_pid_records()
        M->>M: normalize sizes
        M->>M: score color pairs
        M->>M: R1 greedy → R2 Hungarian → R3 fallback
        alt confidence < llm_fallback_threshold AND use_llm
            O->>L: disambiguate_low_confidence()
            L-->>O: chosen impression + rationale
        end
        O->>DB: upsert mappings
    end
    S-->>C: {batch_id, status_counts, ...}

    Note over C,DB: Human review (Streamlit UI)
    C->>DB: load NEEDS_REVIEW mappings
    C->>API: POST /api/v1/feedback {action}
    API->>DB: write feedback + update mapping status

    Note over C,DB: Evaluation
    C->>API: POST /api/v1/eval/run
    API->>DB: aggregate by status + tier → write eval_runs
    API-->>C: metrics + guardrail alerts
```

---

## 6. Matching Pipeline — Decision Logic

The core algorithm for each PID's color↔impression matrix:

```mermaid
flowchart TD
    START([Load PID's TCIN + Variation records]) --> NORM[Normalize all sizes\nX Large → xl, 1X → 1x]

    NORM --> SCORE["Score every colorName × ImpressionName pair
    ① Token overlap:  'maroon' in 'ROBUST MAROON'
    ② Keyword match:  ruby→red, maroon→red
    ③ Fuzzy string:   rapidfuzz WRatio / token_set"]

    SCORE --> R1{"Round 1 — Greedy\nany pair ≥ HIGH_CONF_THRESHOLD?"}
    R1 -->|Yes| LOCK["Lock high-confidence pairs\n(first-come, no sharing)"]
    LOCK --> R2
    R1 -->|No| R2["Round 2 — Hungarian\nglobally-optimal 1:1 assignment\n(scipy linear_sum_assignment)"]

    R2 --> R3["Round 3 — Fallback\nremaining colors get best\navailable impression"]

    R3 --> AMBIG{"confidence < llm_fallback_threshold\nAND use_llm enabled?"}
    AMBIG -->|Yes| LLM["LLM Disambiguation\nsend colorName + candidate list\nto ThinkTank via LLMClient.chat()"]
    LLM --> STATUS
    AMBIG -->|No| STATUS

    STATUS{"Assign MappingStatus\nfrom final confidence"}
    STATUS -->|"≥ auto_confirm, no LLM"| A["AUTO_CONFIRM ✅"]
    STATUS -->|"≥ auto_confirm, LLM ran"| B["LLM_ASSISTED 🤖"]
    STATUS -->|"≥ llm_fallback"| C["NEEDS_SPOT_CHECK 🟡"]
    STATUS -->|"< no_match"| D["NO_MATCH 🔴"]
    STATUS -->|"otherwise"| E["NEEDS_REVIEW 🟠"]

    A --> WRITE[(mappings collection)]
    B --> WRITE
    C --> WRITE
    D --> WRITE
    E --> WRITE

    WRITE --> FEEDBACK{Reviewer acts?}
    FEEDBACK -->|Confirm| CONFIRMED["CONFIRMED ✅"]
    FEEDBACK -->|Reject| REJECTED["REJECTED ❌"]
    FEEDBACK -->|Correct| CORRECTED["CORRECTED ✏️\n+ new impression stored"]
```

Thresholds (`auto_confirm_threshold`, `no_match_threshold`, `llm_fallback_threshold`) are all configurable via `matching.*` in `config/base.yaml` or `APP__MATCHING__*` env vars.

---

## 7. Data Model

```mermaid
erDiagram
    tcin_records {
        string _id PK
        string pid
        string partner_id
        string tcin_id
        string color "broad family: Red, Blue"
        string color_name "specific: Maroon, Light Blue"
        string size "1X, Medium, XX Large"
        string[] department_ids
        string[] class_ids
        datetime ingested_at
        string source_file
    }
    variation_records {
        string _id PK
        string pid
        string impression_id
        string impression_name "ROMANTIC RUBY, GOALSETTING GRAY"
        string size_id
        string size
        string[] workspace_ids
        datetime ingested_at
        string source_file
    }
    mappings {
        string _id PK
        string pid
        string tcin_id
        string[] department_ids
        string tcin_color
        string tcin_color_name
        string tcin_size
        string matched_impression_id
        string matched_impression_name
        string variation_size
        float color_confidence "0.0 – 1.0"
        float size_confidence "0.0 – 1.0"
        string confidence_tier "HIGH GOOD FAIR LOW"
        string color_match_reason
        string match_round "GREEDY HUNGARIAN FALLBACK LLM"
        string llm_rationale
        string batch_id
        string status "AUTO_CONFIRM LLM_ASSISTED NEEDS_SPOT_CHECK NO_MATCH NEEDS_REVIEW CONFIRMED REJECTED CORRECTED"
        datetime created_at
        datetime updated_at
    }
    feedback {
        string _id PK
        string mapping_id FK
        string pid
        string tcin_id
        string action "CONFIRM REJECT CORRECT"
        string reviewer
        string suggested_impression_name
        string original_impression_name
        float original_color_confidence
        datetime created_at
    }
    eval_runs {
        string _id PK
        int total_mappings
        map by_status
        map by_tier
        float pct_high
        float pct_low
        float correction_rate
        float avg_color_confidence
        string[] guardrail_alerts
        datetime created_at
    }

    tcin_records      ||--o{ mappings  : "pid + tcin_id"
    variation_records ||--o{ mappings  : "pid + impression_id"
    mappings          ||--o{ feedback  : "mapping_id"
    mappings          }o--|| eval_runs : "aggregated into"
```

Document models are defined as Pydantic models in [`plm_tcin_mapper/database/models.py`](../plm_tcin_mapper/database/models.py); enums subclass `StrEnum` so they serialize transparently to MongoDB.

---

## 8. Configuration System

Configuration is owned by **`ai-core`** (`ai_core.config.Settings`) and shared by every app in the monorepo. `plm-tcin-mapper` uses the `mongo`, `matching`, `ingestion`, and `eval` sections in addition to the common `app` / `llm` / `thinktank` / `spark` sections.

```mermaid
flowchart LR
    subgraph FILES["Files"]
        BASE["config/base.yaml\n✅ committed\nthresholds, model, mongo db,\ningestion data_dir"]
        LOCAL["config/local.yaml\n🚫 gitignored\ndev overrides"]
        DOTENV[".env (root + app)\n🚫 gitignored\nThinkTank secrets, Mongo URL"]
    end
    subgraph CLOUD["TAP / Cloud"]
        ENVVARS["APP__* env vars\n+ /tap/secret/* files"]
    end

    BASE -->|lowest| MERGE
    LOCAL -->|overrides base| MERGE
    DOTENV --> MERGE
    ENVVARS -->|highest| MERGE
    MERGE["ai_core.config.load_settings()\nlru_cache — loaded once"]
    MERGE --> CFG

    subgraph CFG["Settings (Pydantic)"]
        MC["MongoConfig\nurl, database"]
        LC["LLMConfig\nprovider, model"]
        MATCHC["MatchingConfig\nauto_confirm 0.85\nllm_fallback 0.60"]
        IC["IngestionConfig\ndata_dir, batch_size"]
        EC["EvalConfig\nguardrail thresholds"]
    end

    style FILES fill:#e8f4f8,stroke:#2196F3
    style CLOUD fill:#f8e8f8,stroke:#9C27B0
    style CFG fill:#e8f8e8,stroke:#4CAF50
```

**Override pattern (no YAML edits):**
```bash
APP__MONGO__URL=mongodb://user:pass@cluster.mongodb.net
APP__LLM__MODEL=gemini-1.5-flash               # cheaper model for staging
APP__MATCHING__AUTO_CONFIRM_THRESHOLD=0.90
```

Secrets are **never** read from YAML — they come from env vars locally, or TAP-mounted `/tap/secret/*` files in clusters (see `ai_core.config._read_secret`).

---

## 9. LLM Abstraction Layer

Unlike the original standalone app (which defined its own `LLMClient.disambiguate()` method and an OpenAI client), this service uses the monorepo's shared **`ai-core` `LLMClient`** interface — a single `chat(ChatRequest) -> ChatResponse` contract. The disambiguator builds a chat prompt and parses the JSON reply, so the matching pipeline is fully decoupled from any specific provider.

```mermaid
classDiagram
    class LLMClient {
        <<abstract, ai-core>>
        +chat(request: ChatRequest) ChatResponse
    }
    class ChatRequest {
        +messages: list[ChatMessage]
        +model: str
        +temperature: float
    }
    class ChatResponse {
        +content: str
        +model: str
        +usage: dict
    }
    class ThinkTankClient {
        <<ai-thinktank>>
        +chat(request) ChatResponse
    }
    class NoOpLLMClient {
        <<ai-core>>
        +chat(request) ChatResponse
    }
    class disambiguator {
        <<plm_tcin_mapper.llm>>
        +disambiguate_low_confidence(mappings, cfg, llm)
        -builds prompt, parses JSON pick
    }

    LLMClient <|-- ThinkTankClient : implements
    LLMClient <|-- NoOpLLMClient : implements
    disambiguator --> LLMClient : uses
    disambiguator ..> ChatRequest : builds

    note for NoOpLLMClient "Used when llm.provider = none\nor in tests — no network"
    note for disambiguator "Called only for pairs below\nllm_fallback_threshold when use_llm=true"
```

**Switching providers** is a one-line config change — `build_llm_client(settings)` in `ai-core` selects the implementation from `llm.provider` (`thinktank` / `openai` / `none`); no pipeline code changes.

---

## 10. Key Design Decisions

### Why deterministic first, LLM second?
LLMs are non-deterministic, slower, and cost money. The deterministic engine (Hungarian + fuzzy) handles ~75–80% of cases correctly with zero latency and zero cost. The LLM is reserved for genuinely ambiguous cases where the color vocabulary overlaps and no clear winner exists.

### Why the Hungarian algorithm?
Naive greedy matching produces locally-optimal but globally-suboptimal assignments. If `ROMANTIC RUBY` is the best match for both `Maroon` and `Red/Coral`, greedy assigns it to whichever it sees first, leaving the other with a poor fallback. Hungarian (`scipy.optimize.linear_sum_assignment`) finds the globally-optimal 1:1 assignment across all pairs at once.

### Why is MongoDB in a shared library, not the app?
MongoDB access lives in [`libs/ai-mongo`](../../../libs/ai-mongo/) so it can be reused by any app that needs it — and **only** by those apps. `plm-think-tank-ai` doesn't touch Mongo, so it never pulls in Motor/PyMongo and its `.env` needs no Mongo URL. This is the low-coupling / high-cohesion goal made concrete: shared infrastructure is available but never imposed.

### Why a FastAPI service instead of CLI scripts?
The original tool ran as `uv run ingest` / `uv run run-mapping` CLI commands. Re-homing it as a FastAPI service makes it deployable on TAP exactly like `plm-think-tank-ai` (same Dockerfile, Vela pipeline, gunicorn entrypoint, health checks) and callable by other PLM services over HTTP. The heavy synchronous pipeline runs in a thread pool so it never blocks the async event loop.

### Why keep the Streamlit UI separate from the service?
The operator UI is an internal review tool, not part of the public API surface, and it brings heavy front-end dependencies. It lives in the optional `ui` dependency group and is excluded from the deployed image. It reads MongoDB directly (sync PyMongo via `ai-mongo`), so reviewers can run it independently of the API.

### Why human-in-the-loop?
No automated system reaches 100% accuracy on creative impression names. The review UI turns reviewer expertise into signal — confirmed mappings become known-good, corrections are recorded in `feedback`. Over time this builds the labeled set needed to tune thresholds or, eventually, train a classifier.
