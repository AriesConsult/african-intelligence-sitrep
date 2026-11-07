"""Regression check against GitHub's actual, archived SitRep 175 extraction.

Skipping only while the five-table extension has not been uploaded.
"""
import json
from pathlib import Path
import pytest

mod=pytest.importorskip("sitrep_tables")
ROOT=Path(__file__).resolve().parents[1]

def test_real_sitrep_175_five_tables_and_arithmetic():
    path=next((ROOT/"review_queue").glob("report_175_*.json"))
    doc=json.loads(path.read_text(encoding="utf8"))
    s=mod.extract_five_tables(doc)
    assert s["tables_machine_validated"]==5, s["quality_flags"]
    t=s["tables"]
    assert t["table_1"]["national"]["cumulative_cases"]==10803
    assert t["table_1"]["national"]["cumulative_deaths"]==5267
    assert len(t["table_2"]["rows"])==67
    assert t["table_2"]["unallocated_deaths"][0]["unallocated_deaths"]==493
    assert t["table_3"]["national"]["alerts_received"]==3885
    assert t["table_3"]["national"]["suspected_alerts"]==559
    assert t["table_4"]["national"]["contacts_to_follow"]==38054
    assert t["table_4"]["national"]["contacts_seen"]==31419
    assert t["table_4"]["national"]["contact_follow_up_rate"]==82.6
    national=next(r for r in t["table_5"]["rows"] if r["scope"]=="DRC")
    assert national["travellers_passed"]==276403
    assert national["reports_received"]==111
    assert national["reports_expected"]==132
    assert national["poe_suspects_investigated_24h_denominator"]==4
