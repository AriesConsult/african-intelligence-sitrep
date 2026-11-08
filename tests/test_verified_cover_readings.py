"""Visually inspected SitRep cover readings must stay tied to exact source identity."""
import json
from pathlib import Path

def test_cover_review_original_registry_hashes_and_key_inconsistencies():
    fixture=json.loads(Path("state/verified_original_cover_readings_20261108.json").read_text(encoding="utf-8"))
    reg=json.loads(Path("state/registry.json").read_text(encoding="utf-8"))
    originals={(v["report_number"],v["sha256"]) for v in reg["documents"].values()}
    for entry in fixture["evidence"]:
        assert (entry["report_number"],entry["registry_sha256"]) in originals
        assert entry["source_url"].startswith("https://")
    by_num={d["report_number"]:d for d in fixture["evidence"]}
    cases="national_cumulative_confirmed_cases"
    deaths="national_cumulative_confirmed_deaths"
    assert by_num[4]["metrics"][cases]["preferred_verbatim_pdf"]==33
    assert by_num[86]["metrics"][cases]["preferred_verbatim_pdf"]==4294
    assert by_num[86]["metrics"][deaths]["preferred_verbatim_pdf"]==1960
    assert by_num[103]["metrics"][deaths]["preferred_verbatim_pdf"]==2744
    assert by_num[150]["metrics"][cases]["preferred_verbatim_pdf"]==9065
    assert any(x["value"]==9066 for x in by_num[150]["metrics"][cases]["other_printed_values"])
    assert by_num[169]["metrics"][deaths]["preferred_verbatim_pdf"]==5372
    assert fixture["status"].startswith("SOURCE_READINGS_VISUALLY_CHECKED")
