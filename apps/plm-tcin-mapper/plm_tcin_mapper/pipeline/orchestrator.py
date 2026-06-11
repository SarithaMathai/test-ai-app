"""Matching pipeline orchestrator — coordinates deterministic engine + LLM disambiguation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ai_core.llm.base import LLMClient

from plm_tcin_mapper.database.models import (
    ConfidenceTier,
    Mapping,
    MappingStatus,
    MatchRound,
    TcinRecord,
    VariationRecord,
)

logger = logging.getLogger(__name__)

_TCIN_COL = "tcin_records"
_VAR_COL = "variation_records"
_MAPPING_COL = "mappings"


def _get_pids_to_match(db: Any, cfg: Any, force: bool, department: str | None) -> list[str]:
    tcin_col = db[_TCIN_COL]
    mapping_col = db[_MAPPING_COL]

    filt: dict = {}
    if department:
        filt["department_ids"] = department

    all_pids = tcin_col.distinct("pid", filt)
    if force:
        return sorted(all_pids)

    already_matched = set(mapping_col.distinct("pid"))
    return sorted(p for p in all_pids if p not in already_matched)


def _load_tcin_records(db: Any, pid: str) -> list[TcinRecord]:
    return [TcinRecord(**{**doc, "_id": str(doc["_id"])}) for doc in db[_TCIN_COL].find({"pid": pid})]


def _load_variation_records(db: Any, pid: str) -> list[VariationRecord]:
    return [VariationRecord(**{**doc, "_id": str(doc["_id"])}) for doc in db[_VAR_COL].find({"pid": pid})]


def _upsert_mapping(db: Any, mapping: Mapping) -> None:
    doc = mapping.model_dump(by_alias=True)
    doc.pop("_id", None)
    db[_MAPPING_COL].update_one(
        {"pid": mapping.pid, "tcin_id": mapping.tcin_id},
        {"$set": doc},
        upsert=True,
    )


def match_pid(
    pid: str,
    tcin_records: list[TcinRecord],
    variation_records: list[VariationRecord],
    cfg: Any,
    llm: LLMClient,
    use_llm: bool,
    dry_run: bool,
    batch_id: str | None = None,
) -> list[Mapping]:
    if not tcin_records or not variation_records:
        return []

    from plm_tcin_mapper.matching.deterministic import match_pid_records

    raw_results = match_pid_records(tcin_records, variation_records, cfg)

    if use_llm and raw_results:
        try:
            from plm_tcin_mapper.llm.disambiguator import disambiguate_low_confidence

            raw_results = disambiguate_low_confidence(raw_results, cfg, llm=llm)
        except Exception as exc:
            logger.warning("LLM disambiguation failed for pid=%s: %s", pid, exc)

    _no_match_threshold = getattr(cfg.matching, "no_match_threshold", 0.75)

    mappings: list[Mapping] = []
    for raw in raw_results:
        if raw.get("used_llm"):
            color_conf = raw.get("color_confidence", 0.0)
            raw["status"] = (
                MappingStatus.LLM_ASSISTED
                if color_conf >= cfg.matching.auto_confirm_threshold
                else MappingStatus.NEEDS_SPOT_CHECK
            )
            raw["match_round"] = MatchRound.LLM

        if raw.get("color_confidence", 0.0) < _no_match_threshold and raw.get("status") not in (
            MappingStatus.AUTO_CONFIRM,
            MappingStatus.LLM_ASSISTED,
        ):
            raw["status"] = MappingStatus.NO_MATCH
            raw["matched_impression_name"] = None
            raw["matched_impression_id"] = None

        mapping_fields = {k: v for k, v in raw.items() if k not in ("candidates", "used_llm")}
        mapping_fields["batch_id"] = batch_id
        try:
            mappings.append(Mapping(**mapping_fields))
        except Exception:
            mappings.append(
                Mapping(
                    pid=raw["pid"],
                    tcin_id=raw["tcin_id"],
                    tcin_color=raw.get("tcin_color", ""),
                    tcin_color_name=raw.get("tcin_color_name", ""),
                    tcin_size=raw.get("tcin_size", ""),
                    color_confidence=raw.get("color_confidence", 0.0),
                    confidence_tier=ConfidenceTier.LOW,
                    status=MappingStatus.NEEDS_REVIEW,
                    batch_id=batch_id,
                )
            )

    return mappings


@dataclass
class BatchStats:
    total_pids: int = 0
    pids_matched: int = 0
    pids_no_data: int = 0
    pids_errored: int = 0
    total_mappings_written: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)


def run_batch(
    pids: list[str],
    db: Any,
    cfg: Any,
    llm: LLMClient,
    use_llm: bool,
    dry_run: bool,
    batch_id: str | None = None,
    shadow_mode: bool = False,
) -> BatchStats:
    stats = BatchStats(total_pids=len(pids))

    for pid in pids:
        try:
            tcin_records = _load_tcin_records(db, pid)
            variation_records = _load_variation_records(db, pid)

            if not tcin_records or not variation_records:
                stats.pids_no_data += 1
                continue

            mappings = match_pid(
                pid, tcin_records, variation_records,
                cfg, llm, use_llm, dry_run,
                batch_id=batch_id,
            )

            if not dry_run:
                for m in mappings:
                    _upsert_mapping(db, m)
                    stats.status_counts[str(m.status)] = stats.status_counts.get(str(m.status), 0) + 1

            stats.pids_matched += 1
            stats.total_mappings_written += len(mappings)

        except Exception as exc:
            stats.pids_errored += 1
            logger.error("Match failed pid=%s: %s", pid, exc)

    return stats
