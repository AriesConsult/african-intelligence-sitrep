"""Health-zone reconciliation must never merge province rows, impute ND, or approve matches."""
import gzip
import json
from pathlib import Path
from reconcile_healthzones import normalize, reconcile

def test_normalize_accents_without_guessing_aliases():
    assert normalize("  Miti  Murhésa ")=="miti murhesa"
    assert normalize("Beni")!=normalize("Biena")

def test_unvalidated_pdf_match_and_nd_stay_review_only(tmp_path):
    published=tmp_path/"published"; table_dir=published/"tables";table_dir.mkdir(parents=True)
    sha="a"*64
    registry={"documents":{f"175:{sha}":{"report_number":175,"report_date":"2026-11-05",
                                     "sha256":sha,"source_url":"https://example.org/175.pdf"}}}
    regpath=tmp_path/"registry.json";regpath.write_text(json.dumps(registry),encoding="utf-8")
    doc={"report_number":175,"source_sha256":sha,"tables":{"table_2":{
        "status":"REVIEW_REQUIRED",
        "rows":[{"health_zone":"Aru","province":"Ituri","scope":"health_zone",
                 "cumulative_cases":25,"cumulative_deaths":7,
                 "source":{"page":2,"table_id":"p2-t4","source_row":6}}],
        "province_totals":[{"province":"Ituri","cumulative_cases":7543,"cumulative_deaths":3565,
                            "source":{"page":2,"table_id":"p2-t4","source_row":4}}]}}}
    (table_dir/f"175_{sha[:12]}.json").write_text(json.dumps(doc),encoding="utf-8")
    staged=tmp_path/"staged";staged.mkdir()
    (staged/"inrb_staging_summary.json").write_text(json.dumps({"inrb_commit":"b"*40}),encoding="utf-8")
    records=[
       {"metric_id":"cumulative_confirmed_cases","geography_raw":"Aru","date_raw":"2026-11-05",
        "date_valid":True,"value_status":"NUMERIC_UNVERIFIED","value_parsed":25,"value_raw":"25",
        "inrb_csv_path":"cases.csv","inrb_csv_sha256":"1","inrb_csv_row_number":2},
       {"metric_id":"cumulative_confirmed_deaths","geography_raw":"Aru","date_raw":"2026-11-05",
        "date_valid":True,"value_status":"NOT_REPORTED","value_parsed":None,"value_raw":"ND",
        "inrb_csv_path":"deaths.csv","inrb_csv_sha256":"2","inrb_csv_row_number":2}]
    with gzip.open(staged/"inrb_observation_candidates.jsonl.gz","wt",encoding="utf-8") as fp:
        for item in records:fp.write(json.dumps(item)+"\n")
    result=reconcile(regpath,published,staged,tmp_path/"out")
    assert result["comparison_counts"]["MATCH_BUT_PDF_TABLE_NOT_VALIDATED"]==1
    assert result["comparison_counts"]["INRB_ND_OR_NONNUMERIC"]==1
    assert result["pdf_unmatched_candidates"]==2
    assert result["matched_same_value_unapproved"]==1
    ledger=[json.loads(s) for s in (tmp_path/"out/healthzone_concordance.jsonl").read_text().splitlines()]
    assert all(not row["approved_for_analysis"] for row in ledger)
