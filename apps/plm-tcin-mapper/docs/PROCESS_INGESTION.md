# Process: CSV Ingestion Pipeline

> **Purpose:** Load normalized CSV data (TCIN + Variation records) from disk into MongoDB  
> **Entry Point:** `POST /api/v1/ingest`  
> **Core Logic:** `plm_tcin_mapper/pipeline/ingestion.py`

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│ Client Request                                                    │
│ POST /api/v1/ingest                                              │
│ {                                                                │
│   "chunk": "chunk_01" | null,      # single chunk or all        │
│   "data_dir": "/data/normalized" | null,  # override config dir │
│   "batch_size": 500,               # MongoDB bulk write size     │
│   "skip_existing": false,          # upsert vs insert-only       │
│   "dry_run": false                 # parse & count, don't write  │
│ }                                                                │
└──────────────────────────────────────────────────────────────────┘
                              ↓
                    IngestionService
                (routes/ingest.py:14-16)
                              ↓
                  service.run(request)
                   [async wrapper]
                              ↓
        run_in_executor(None, _run_sync)
          [offload sync I/O from event loop]
                              ↓
            _run_sync(request)
            [sync function, CPU-bound]
            1. Resolve data_dir + batch_size from config
            2. List chunk directories (chunk_01, chunk_02, ...)
            3. Get MongoDB connection (or None if dry_run)
                              ↓
    ┌─────────────────────────────────────┐
    │ For each chunk_dir:                 │
    │ ingest_chunk(chunk_dir, db, ...)   │
    └─────────────────────────────────────┘
                ↓ ↓ ↓
        ┌──────────────────┐
        │ chunk_01/        │
        ├──────────────────┤
        │ tcin.csv         │
        │ variation.csv    │
        └──────────────────┘
                ↓
        ingest_chunk()
        [pipeline/ingestion.py:184]
                ↓
        Loop: for csv_file in chunk_dir/*.csv
                ↓
            _detect_kind(csv_file)
            [sniff header row]
                ↓
        ┌───────────────────────────────────┐
        │ Header Analysis                   │
        ├───────────────────────────────────┤
        │ TCIN_REQUIRED:                    │
        │   {PID, TcinId, colorName}        │
        │ → kind = "tcin"                   │
        ├───────────────────────────────────┤
        │ VARIATION_REQUIRED:               │
        │   {PID, ImpressionId, Name}       │
        │ → kind = "variation"              │
        ├───────────────────────────────────┤
        │ ERROR_REQUIRED:                   │
        │   {PID, ReportType, ErrorMsg}     │
        │ → kind = "error" [skipped]        │
        └───────────────────────────────────┘
                ↓
        ┌─────────────────────────────────────────┐
        │ ingest_tcin_file() OR                   │
        │ ingest_variation_file()                 │
        └─────────────────────────────────────────┘
                ↓
        _read_csv(path)
        [Parse rows with csv.DictReader]
                ↓
        For each row:
        ├─ parse_tcin_row(row) → TcinRecord | None
        │  or
        ├─ parse_variation_row(row) → VariationRecord | None
        │  [Validates PID, IDs, required fields]
                ↓
        Build bulk op:
        ├─ If skip_existing:
        │   UpdateOne(filter, {"$setOnInsert": doc}, upsert=True)
        │   [Insert only if new; skip if exists]
        │
        └─ Else (default):
            ReplaceOne(filter, doc, upsert=True)
            [Insert or replace; always latest]
                ↓
        Batch size = 500 rows
        ├─ When len(ops) >= 500:
        │   _bulk_write(collection, ops)
        │   [Send to MongoDB]
        │
        └─ On EOF:
            Send remaining ops
                ↓
        _bulk_write()
        [collection.bulk_write(ops, ordered=False)]
                ↓
        MongoDB Response
        ├─ upserted_count: new docs
        ├─ modified_count: updated docs
        └─ On BulkWriteError: extract partial counts
                ↓
        Return FileStats
        {
          path: str,
          kind: "tcin" | "variation",
          inserted: int,
          updated: int,
          skipped: int,
          errored: int
        }
                ↓
        Accumulate across all chunks:
        IngestStats {
          chunks_processed: int,
          file_stats: [FileStats, ...],
          totals: {inserted, updated, skipped, errored}
        }
                ↓
        Return IngestResponse
        {
          status: "ok",
          chunks_processed: int,
          totals: {...},
          dry_run: bool
        }
                ↓
                200 OK
```

---

## Schema Details

### Input: CSV File Formats

#### tcin.csv Header (required columns)
```
PID, TcinId, Color, colorName, Size, PartnerId, DepartmentIds, ClassIds
009E83, 94447439, Red, Maroon, 1X, Target-001, Clothing;Home, Fashion
```

**Field Mapping:**
| CSV Column | TcinRecord Field | Type | Required |
|------------|------------------|------|----------|
| `PID` | `pid` | str | ✅ Yes |
| `TcinId` | `tcin_id` | str | ✅ Yes (not "ERROR") |
| `Color` | `color` | str | ❌ Optional (broad family) |
| `colorName` | `color_name` | str | ✅ Yes (specific shade) |
| `Size` | `size` | str | ❌ Optional |
| `PartnerId` | `partner_id` | str | ❌ Optional |
| `DepartmentIds` | `department_ids` | list[str] (sep=`;`) | ❌ Optional |
| `ClassIds` | `class_ids` | list[str] (sep=`;`) | ❌ Optional |

**Auto-Generated:**
```python
id:           str = uuid4()
ingested_at:  datetime = now(UTC)
source_file:  str = "tcin.csv"  # or other filename
```

#### variation.csv Header (required columns)
```
PID, ImpressionId, ImpressionName, Size, SizeId, WorkspaceIds
009E83, dd948247-..., ROMANTIC RUBY, 1X, 1x-dd948247, workspace-001;workspace-002
```

**Field Mapping:**
| CSV Column | VariationRecord Field | Type | Required |
|------------|----------------------|------|----------|
| `PID` | `pid` | str | ✅ Yes |
| `ImpressionId` | `impression_id` | str | ✅ Yes |
| `ImpressionName` | `impression_name` | str | ✅ Yes |
| `Size` | `size` | str | ❌ Optional |
| `SizeId` | `size_id` | str | ❌ Optional |
| `WorkspaceIds` | `workspace_ids` | list[str] (sep=`;`) | ❌ Optional |

**Auto-Generated:**
```python
id:           str = uuid4()
ingested_at:  datetime = now(UTC)
source_file:  str = "variation.csv"  # or other filename
```

### Output: MongoDB Collections

#### tcin_records Collection

**Index (recommended):**
```javascript
db.tcin_records.createIndex({pid: 1, tcin_id: 1})  // Upsert key
db.tcin_records.createIndex({department_ids: 1})   // For querying by dept
db.tcin_records.createIndex({ingested_at: -1})     // For tracing
```

**Document Example:**
```javascript
{
  "_id": "550e8400-e29b-41d4-a716-446655440000",
  "pid": "009E83",
  "tcin_id": "94447439",
  "partner_id": "Target-001",
  "color": "Red",
  "color_name": "Maroon",
  "size": "1X",
  "department_ids": ["Clothing", "Home"],
  "class_ids": ["Fashion"],
  "ingested_at": ISODate("2026-06-11T14:30:00.000Z"),
  "source_file": "chunk_01/tcin.csv"
}
```

#### variation_records Collection

**Index (recommended):**
```javascript
db.variation_records.createIndex({pid: 1, impression_id: 1, size_id: 1})  // Upsert key
db.variation_records.createIndex({pid: 1, impression_name: 1})            // For matching
```

**Document Example:**
```javascript
{
  "_id": "660f9511-f40c-52e5-b827-557766551111",
  "pid": "009E83",
  "impression_id": "dd948247-7a8c-11ec-81d5-0242ac130003",
  "impression_name": "ROMANTIC RUBY",
  "size": "1X",
  "size_id": "1x-dd948247",
  "workspace_ids": ["workspace-001", "workspace-002"],
  "ingested_at": ISODate("2026-06-11T14:30:00.000Z"),
  "source_file": "chunk_01/variation.csv"
}
```

---

## Implementation Details

### CSV Parsing

**Header Normalization:**
```python
# CSV headers may have leading/trailing spaces
reader.fieldnames = [h.strip() for h in (reader.fieldnames or [])]

# Row values also stripped
row = {k.strip(): v for k, v in row.items()}
```

**Multi-valued Fields (List Splits):**
```python
def _split_ids(value: str, sep: str = ",") -> list[str]:
    """Split comma/semicolon-separated values, strip whitespace."""
    return [v.strip() for v in value.split(sep) if v.strip()]

# Usage:
department_ids = _split_ids(row.get("DepartmentIds", ""), sep=";")
# "Clothing;Home" → ["Clothing", "Home"]
# "  ;  " → []
```

### Validation Rules

**TcinRecord:**
- `pid`: required, non-empty ✅
- `tcin_id`: required, non-empty, ≠ "ERROR" ✅
  (Filters out error placeholders)
- `color_name`: required ✅
- Others: optional, defaulted to None or []

**VariationRecord:**
- `pid`: required ✅
- `impression_id`: required ✅
- `impression_name`: required ✅
- Others: optional

**On Parse Failure:**
- Skipped (stats.errored += 1)
- No exception raised
- Processing continues

### MongoDB Upsert Strategy

**Filter Key (Upsert On):**
```python
# TCIN records
filter = {"pid": record.pid, "tcin_id": record.tcin_id}

# Variation records
filter = {"pid": record.pid, "impression_id": record.impression_id, "size_id": record.size_id}
```

**Why?** Ensures 1:1 mapping per (PID, ID) pair. Multiple ingest runs are idempotent.

**Mode Options:**

1. **Default (replace):**
   ```python
   ReplaceOne(filter, doc, upsert=True)
   # If exists: replace entire doc with latest CSV data
   # If not exists: insert
   ```

2. **Skip Existing:**
   ```python
   UpdateOne(filter, {"$setOnInsert": doc}, upsert=True)
   # If exists: do nothing
   # If not exists: insert doc
   # ✅ Useful: re-ingest can't overwrite corrections
   ```

### Bulk Write Options

**Ordered vs Unordered:**
```python
# Current: ordered=False (default in _bulk_write)
collection.bulk_write(ops, ordered=False)
# ✅ Faster: continues on errors, doesn't stop at first failure
# ✅ Safe for upserts: order doesn't matter
```

**Batch Size:**
- Default: 500 rows
- Configurable: `batch_size` parameter
- Trade-off:
  - Larger batch → fewer round-trips → faster
  - Smaller batch → less memory → safer for huge datasets

---

## Request/Response Examples

### Request 1: Ingest Single Chunk (Full)

```bash
POST /api/v1/ingest
Content-Type: application/json

{
  "chunk": "chunk_01",
  "batch_size": 500,
  "skip_existing": false,
  "dry_run": false
}
```

**Response:**
```json
{
  "status": "ok",
  "chunks_processed": 1,
  "totals": {
    "inserted": 2847,
    "updated": 156,
    "skipped": 0,
    "errored": 12
  },
  "dry_run": false
}
```

### Request 2: Dry Run (Count Without Writing)

```bash
POST /api/v1/ingest
Content-Type: application/json

{
  "chunk": "chunk_02",
  "dry_run": true
}
```

**Response:**
```json
{
  "status": "ok",
  "chunks_processed": 1,
  "totals": {
    "inserted": 3101,
    "updated": 0,
    "skipped": 0,
    "errored": 8
  },
  "dry_run": true
}
```
*(Parsed 3,101 records, but nothing written to DB)*

### Request 3: Ingest All Chunks

```bash
POST /api/v1/ingest
Content-Type: application/json

{
  "batch_size": 1000
}
```

**Response:**
```json
{
  "status": "ok",
  "chunks_processed": 14,
  "totals": {
    "inserted": 45230,
    "updated": 3421,
    "skipped": 0,
    "errored": 156
  },
  "dry_run": false
}
```

---

## Error Scenarios

### Scenario 1: CSV Header Missing Required Column

**CSV File:**
```
PID, TcinId, Color, Size      ← Missing 'colorName'
```

**Result:**
- File skipped silently (returns `kind=None` from `_detect_kind()`)
- Not processed
- No error logged (silent skip)

**Fix:** Ensure CSV has correct headers before upload

### Scenario 2: Malformed CSV (UTF-8 Issue)

**Input:**
- File with broken encoding

**Result:**
- `_read_csv()` fails on line with encoding error
- Exception caught in `ingest_chunk()` loop
- File marked `kind=None`
- Other files continue

**Fix:** Pre-validate CSV encoding (UTF-8 recommended)

### Scenario 3: Partial Bulk Write Failure

**Scenario:**
- 500 ops queued
- MongoDB connection drops mid-write
- BulkWriteError raised

**Code:**
```python
try:
    result = collection.bulk_write(ops, ordered=False)
    return result.upserted_count, result.modified_count
except BulkWriteError as exc:
    return exc.details.get("nUpserted", 0), exc.details.get("nModified", 0)
    # ⚠️ Returns partial counts; some ops may have succeeded
```

**Fix:** Operator must retry or manually verify DB state

---

## Performance Characteristics

**Throughput (empirical estimates):**
- **Parsing:** ~10,000 rows/sec per CPU core
- **Bulk write:** ~5,000 rows/sec (MongoDB latency-dependent)
- **Overall:** ~3,000-5,000 rows/sec (limited by network)

**Memory:**
- 500-row batch: ~2MB (Pydantic models + ops list)
- Safe for 100K+ row files

**Example: Ingest chunk_01 (50K records)**
- Parse: 50,000 / 10,000 = 5s
- Bulk writes (100 batches): 100 * 200ms = 20s
- **Total:** ~25-30 seconds

---

## Operations

### Idempotency

✅ **Fully idempotent:**
- Upsert filter ensures (PID, ID) → latest doc
- Re-running ingest on same file = no change
- Safe for retries

### Rollback

❌ **No rollback mechanism:**
- Data is upserted directly
- To revert: manual MongoDB update or re-ingest old CSV

### Monitoring

**Metrics to track:**
- `chunks_processed` (should match expected # of chunks)
- `totals.errored` (should be <1% of total)
- `totals.inserted` vs `totals.updated` (ratio indicates fresh data or updates)

**Alerts:**
- `errored` count > 100 per chunk → investigate CSV quality
- `total_rows_ingested == 0` → likely misconfiguration (wrong data_dir)

---

## Next Steps

After successful ingestion:
1. Verify document counts: `db.tcin_records.countDocuments({})` + `db.variation_records.countDocuments({})`
2. Spot-check a PID: `db.tcin_records.findOne({pid: "009E83"})` + variations
3. Proceed to **Matching Pipeline** (see PROCESS_MATCHING.md)
