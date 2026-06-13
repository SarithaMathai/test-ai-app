"""CSV → MongoDB ingestion pipeline."""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from pymongo import ReplaceOne, UpdateOne
from pymongo.errors import BulkWriteError

from plm_tcin_mapper.database.models import TcinRecord, VariationRecord

logger = logging.getLogger(__name__)
PROGRESS_LOG_EVERY = 1000

TCIN_REQUIRED = {"PID", "TcinId", "colorName"}
VARIATION_REQUIRED = {"PID", "ImpressionId", "ImpressionName"}
ERROR_REQUIRED = {"PID", "ReportType", "ErrorMessage"}


@dataclass
class FileStats:
    path: str
    kind: str
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errored: int = 0

    @property
    def total_processed(self) -> int:
        return self.inserted + self.updated + self.skipped + self.errored


@dataclass
class IngestStats:
    chunks_processed: int = 0
    file_stats: list[FileStats] = field(default_factory=list)

    @property
    def totals(self) -> dict[str, int]:
        return {
            "inserted": sum(f.inserted for f in self.file_stats),
            "updated": sum(f.updated for f in self.file_stats),
            "skipped": sum(f.skipped for f in self.file_stats),
            "errored": sum(f.errored for f in self.file_stats),
        }


def _split_ids(value: str, sep: str = ",") -> list[str]:
    return [v.strip() for v in value.split(sep) if v.strip()]


def parse_tcin_row(row: dict, source_file: str) -> TcinRecord | None:
    pid = row.get("PID", "").strip()
    tcin_id = row.get("TcinId", "").strip()
    if not pid or not tcin_id or tcin_id.upper() == "ERROR":
        return None
    return TcinRecord(
        pid=pid,
        partner_id=row.get("PartnerId", "").strip() or None,
        tcin_id=tcin_id,
        color=row.get("Color", "").strip(),
        color_name=row.get("colorName", "").strip(),
        size=row.get("Size", "").strip(),
        department_ids=_split_ids(row.get("DepartmentIds", ""), sep=";"),
        class_ids=_split_ids(row.get("ClassIds", ""), sep=";"),
        source_file=source_file,
    )


def parse_variation_row(row: dict, source_file: str) -> VariationRecord | None:
    pid = row.get("PID", "").strip()
    impression_id = row.get("ImpressionId", "").strip()
    impression_name = row.get("ImpressionName", "").strip()
    if not pid or not impression_id or not impression_name:
        return None
    return VariationRecord(
        pid=pid,
        impression_id=impression_id,
        impression_name=impression_name,
        size_id=row.get("SizeId", "").strip() or None,
        size=row.get("Size", "").strip(),
        workspace_ids=_split_ids(row.get("WorkspaceIds", ""), sep=";"),
        source_file=source_file,
    )


def _read_csv(path: Path) -> Iterator[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [h.strip() for h in (reader.fieldnames or [])]
        for row in reader:
            yield {k.strip(): v for k, v in row.items()}


def _detect_kind(path: Path) -> str | None:
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = {h.strip() for h in next(reader, [])}
    except Exception:
        return None
    if headers >= TCIN_REQUIRED:
        return "tcin"
    if headers >= VARIATION_REQUIRED:
        return "variation"
    if headers >= ERROR_REQUIRED:
        return "error"
    return None


def _bulk_write(collection, ops: list, ordered: bool = False) -> tuple[int, int]:
    if not ops:
        return 0, 0
    try:
        result = collection.bulk_write(ops, ordered=ordered)
        return result.upserted_count, result.modified_count
    except BulkWriteError as exc:
        return exc.details.get("nUpserted", 0), exc.details.get("nModified", 0)


def ingest_tcin_file(path: Path, collection, batch_size: int, skip_existing: bool, dry_run: bool) -> FileStats:
    stats = FileStats(path=str(path), kind="tcin")
    ops: list = []
    processed = 0
    for row in _read_csv(path):
        processed += 1
        record = parse_tcin_row(row, path.name)
        if record is None:
            stats.errored += 1
            if processed % PROGRESS_LOG_EVERY == 0:
                logger.info(
                    "TCIN progress: file=%s processed=%s inserted=%s updated=%s skipped=%s errored=%s",
                    path.name,
                    processed,
                    stats.inserted,
                    stats.updated,
                    stats.skipped,
                    stats.errored,
                )
            continue
        doc = record.model_dump(by_alias=False, exclude={"id"})
        # One canonical TCIN record per tcin_id across the dataset.
        filt = {"tcin_id": record.tcin_id}
        ops.append(
            UpdateOne(filt, {"$setOnInsert": doc}, upsert=True)
            if skip_existing
            else ReplaceOne(filt, doc, upsert=True)
        )
        if len(ops) >= batch_size:
            if not dry_run:
                ins, upd = _bulk_write(collection, ops)
                stats.inserted += ins
                stats.updated += upd
                stats.skipped += len(ops) - ins - upd
            else:
                stats.inserted += len(ops)
            ops = []
        if processed % PROGRESS_LOG_EVERY == 0:
            logger.info(
                "TCIN progress: file=%s processed=%s inserted=%s updated=%s skipped=%s errored=%s",
                path.name,
                processed,
                stats.inserted,
                stats.updated,
                stats.skipped,
                stats.errored,
            )
    if ops:
        if not dry_run:
            ins, upd = _bulk_write(collection, ops)
            stats.inserted += ins
            stats.updated += upd
            stats.skipped += len(ops) - ins - upd
        else:
            stats.inserted += len(ops)

    logger.info(
        "Ingested TCIN file: path=%s inserted=%s updated=%s skipped=%s errored=%s",
        path,
        stats.inserted,
        stats.updated,
        stats.skipped,
        stats.errored,
    )
    return stats


def ingest_variation_file(path: Path, collection, batch_size: int, skip_existing: bool, dry_run: bool) -> FileStats:
    stats = FileStats(path=str(path), kind="variation")
    ops: list = []
    processed = 0
    for row in _read_csv(path):
        processed += 1
        record = parse_variation_row(row, path.name)
        if record is None:
            stats.errored += 1
            if processed % PROGRESS_LOG_EVERY == 0:
                logger.info(
                    "Variation progress: file=%s processed=%s inserted=%s updated=%s skipped=%s errored=%s",
                    path.name,
                    processed,
                    stats.inserted,
                    stats.updated,
                    stats.skipped,
                    stats.errored,
                )
            continue
        doc = record.model_dump(by_alias=False, exclude={"id"})
        filt = {"pid": record.pid, "impression_id": record.impression_id, "size_id": record.size_id}
        ops.append(
            UpdateOne(filt, {"$setOnInsert": doc}, upsert=True)
            if skip_existing
            else ReplaceOne(filt, doc, upsert=True)
        )
        if len(ops) >= batch_size:
            if not dry_run:
                ins, upd = _bulk_write(collection, ops)
                stats.inserted += ins
                stats.updated += upd
                stats.skipped += len(ops) - ins - upd
            else:
                stats.inserted += len(ops)
            ops = []
        if processed % PROGRESS_LOG_EVERY == 0:
            logger.info(
                "Variation progress: file=%s processed=%s inserted=%s updated=%s skipped=%s errored=%s",
                path.name,
                processed,
                stats.inserted,
                stats.updated,
                stats.skipped,
                stats.errored,
            )
    if ops:
        if not dry_run:
            ins, upd = _bulk_write(collection, ops)
            stats.inserted += ins
            stats.updated += upd
            stats.skipped += len(ops) - ins - upd
        else:
            stats.inserted += len(ops)

    logger.info(
        "Ingested variation file: path=%s inserted=%s updated=%s skipped=%s errored=%s",
        path,
        stats.inserted,
        stats.updated,
        stats.skipped,
        stats.errored,
    )
    return stats


def ingest_chunk(chunk_dir: Path, db, batch_size: int, skip_existing: bool, dry_run: bool) -> list[FileStats]:
    file_stats = []
    tcin_col = db["tcin_records"] if db is not None else None
    variation_col = db["variation_records"] if db is not None else None

    csv_files = sorted(chunk_dir.glob("*.csv"))
    total_files = len(csv_files)
    logger.info("Chunk start: chunk_dir=%s files=%s", chunk_dir, total_files)

    for file_index, csv_file in enumerate(csv_files, start=1):
        kind = _detect_kind(csv_file)
        logger.info(
            "Processing file %s/%s in %s: name=%s kind=%s",
            file_index,
            total_files,
            chunk_dir.name,
            csv_file.name,
            kind,
        )
        if kind == "tcin":
            stats = ingest_tcin_file(csv_file, tcin_col, batch_size, skip_existing, dry_run)
        elif kind == "variation":
            stats = ingest_variation_file(csv_file, variation_col, batch_size, skip_existing, dry_run)
        elif kind == "error":
            stats = FileStats(path=str(csv_file), kind="error")
        else:
            continue
        file_stats.append(stats)

    logger.info("Chunk processed: chunk_dir=%s files=%s", chunk_dir, len(file_stats))

    return file_stats


def ingest_directory(
    data_dir: str | Path, db, batch_size: int = 500, skip_existing: bool = False, dry_run: bool = False
) -> dict[str, int]:
    """Ingest one directory of chunk folders and return UI-friendly aggregate stats.

    This helper is kept for Streamlit UI compatibility.
    """
    root = Path(data_dir)
    logger.info(
        "Directory ingestion started: root=%s batch_size=%s skip_existing=%s dry_run=%s",
        root,
        batch_size,
        skip_existing,
        dry_run,
    )
    if not root.exists():
        raise FileNotFoundError(f"Data directory does not exist: {root}")

    # Support both a root folder containing chunk_* dirs and a direct chunk dir.
    if any(root.glob("*.csv")):
        chunk_dirs = [root]
    else:
        chunk_dirs = sorted(d for d in root.iterdir() if d.is_dir() and d.name.startswith("chunk_"))

    if not chunk_dirs:
        raise FileNotFoundError(f"No chunk directories found under: {root}")

    totals = {
        "tcin_inserted": 0,
        "tcin_updated": 0,
        "variation_inserted": 0,
        "variation_updated": 0,
        "skipped": 0,
        "errored": 0,
        "chunks_processed": 0,
    }

    for chunk_dir in chunk_dirs:
        logger.info("Directory ingestion chunk start: %s", chunk_dir)
        per_file = ingest_chunk(
            chunk_dir=chunk_dir,
            db=db,
            batch_size=batch_size,
            skip_existing=skip_existing,
            dry_run=dry_run,
        )
        totals["chunks_processed"] += 1

        for stats in per_file:
            totals["skipped"] += stats.skipped
            totals["errored"] += stats.errored

            if stats.kind == "tcin":
                totals["tcin_inserted"] += stats.inserted
                totals["tcin_updated"] += stats.updated
            elif stats.kind == "variation":
                totals["variation_inserted"] += stats.inserted
                totals["variation_updated"] += stats.updated

        logger.info("Directory ingestion chunk done: %s totals=%s", chunk_dir.name, totals)

    logger.info("Directory ingestion finished: totals=%s", totals)

    return totals
