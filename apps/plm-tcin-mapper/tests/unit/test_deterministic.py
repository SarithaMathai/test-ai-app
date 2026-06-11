"""Unit tests for the deterministic matching engine."""

import pytest
from plm_tcin_mapper.database.models import TcinRecord, VariationRecord
from plm_tcin_mapper.matching.deterministic import match_pid_records


def _make_tcin(pid: str, tcin_id: str, color: str, color_name: str, size: str = "Medium") -> TcinRecord:
    return TcinRecord(pid=pid, tcin_id=tcin_id, color=color, color_name=color_name, size=size)


def _make_var(pid: str, impression_id: str, name: str, size: str = "Medium") -> VariationRecord:
    return VariationRecord(pid=pid, impression_id=impression_id, impression_name=name, size=size)


class _FakeCfg:
    class matching:
        auto_confirm_threshold = 0.85
        no_match_threshold = 0.75
        llm_fallback_threshold = 0.60
        low_confidence_threshold = 0.50


@pytest.mark.unit
class TestMatchPidRecords:
    def test_basic_match(self):
        tcins = [_make_tcin("PID1", "T001", "Blue", "Navy Blue")]
        variations = [_make_var("PID1", "IMP001", "NAVY BLUE")]
        results = match_pid_records(tcins, variations, _FakeCfg)
        assert len(results) == 1
        assert results[0]["pid"] == "PID1"
        assert results[0]["color_confidence"] > 0.70

    def test_empty_inputs(self):
        assert match_pid_records([], [], _FakeCfg) == []
        assert match_pid_records([_make_tcin("P1", "T1", "Red", "Red")], [], _FakeCfg) == []

    def test_multi_color_assignment(self):
        tcins = [
            _make_tcin("PID2", "T001", "Red", "Ruby Red"),
            _make_tcin("PID2", "T002", "Blue", "Navy Blue"),
        ]
        variations = [
            _make_var("PID2", "IMP001", "RUBY RED"),
            _make_var("PID2", "IMP002", "DEEP NAVY"),
        ]
        results = match_pid_records(tcins, variations, _FakeCfg)
        assert len(results) == 2

    def test_single_impression_maps_all(self):
        tcins = [
            _make_tcin("PID3", "T001", "Red", "Ruby Red"),
            _make_tcin("PID3", "T002", "Blue", "Navy Blue"),
        ]
        variations = [_make_var("PID3", "IMP001", "MULTICOLOR")]
        results = match_pid_records(tcins, variations, _FakeCfg)
        assert len(results) == 2
        assert all(r["matched_impression_name"] == "MULTICOLOR" for r in results)
