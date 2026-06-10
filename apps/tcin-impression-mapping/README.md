# tcin-impression-mapping

Streamlit application for mapping TCIN color descriptions to impression names.

Uses a two-stage pipeline:
1. **Deterministic** — rapidfuzz fuzzy matching + colour synonym expansion
2. **LLM fallback** — escalates ambiguous cases (score 60–85%) to the configured LLM

## Quick start

```bash
# set OPENAI_API_KEY (or THINKTANK_API_KEY) in .env, then:
make run-tcin
# → http://localhost:8501
```

## Pipeline logic

```
MappingRequest
    │
    ▼
Deterministic fuzzy match (rapidfuzz)
    │
    ├─ score ≥ 0.85 ──► ACCEPTED  (strategy: deterministic)
    │
    ├─ 0.60 ≤ score < 0.85 ──► LLM disambiguation
    │                              │
    │                              ├─ LLM picks from candidates ──► ACCEPTED  (strategy: llm)
    │                              └─ LLM fails ──► fallback to deterministic top match
    │
    └─ score < 0.60 ──► NO MATCH  (strategy: no_match, queued for human review)
```

## UI features

- **Single mapping tab**: enter one TCIN color + candidate list, see result instantly
- **Batch CSV tab**: upload CSV → download results with confidence badges

### CSV format

```
pid,tcin_id,color_family,color_name,size,candidates
P001,T001,Blue,Navy Blue,M,NAVY|DARK BLUE|COBALT DREAM
P002,T002,Red,Scarlet,S,RED|RUBY|CRIMSON
```

## Switching LLM providers

```yaml
# config/base.yaml
llm:
  provider: openai       # or: thinktank
  model: gpt-4o
```

Thresholds are tuneable:
```python
MapperService(llm, auto_threshold=0.85, llm_threshold=0.60)
```
