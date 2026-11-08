"""Page-name occurrence is only a source locator, not a validated cell."""
import gzip
import json
from pathlib import Path
from locate_historical_zone_pages import locate

def test_locs_dont_promote_upstream_values(tmp_path):
    root=tmp_path/"full";(root/"full_pages").mkdir(parents=True)
    doc={"report_number":10,"report_date":"2026-05-24","source_sha256":"a"*64,
         "pages":[{"page":1,"text_sorted":"Mongbwalu cas suspects 5"}]}
    with gzip.open(root/"full_pages/010.json.gz","wt",encoding="utf-8") as f:json.dump(doc,f)
    audit={"status":"ALL_ARCHIVED_PDFS_EXTRACTED_FIDELITY_REVIEW_PENDING",
           "records":[{"report_number":10,"source_sha256":"a"*64,"extraction_file":"full_pages/010.json.gz"}]}
    (root/"page_extraction_audit.json").write_text(json.dumps(audit))
    ledger=tmp_path/"ledger.jsonl"
    row={"status":"NO_DIRECT_PDF_TABLE2_CELL_FOR_DATE_AND_ZONE",
        "date":"2026-05-24","metric_id":"cumulative_confirmed_cases",
        "geography":"Mongbwalu","inrb_value_raw":"5","inrb_csv_path":"a.csv","inrb_csv_row":4}
    ledger.write_text(json.dumps(row)+"\n")
    result=locate(ledger,root,tmp_path/"out")
    assert result["counts"]["ZONE_MENTIONED_ON_PDF_PAGE_SOURCE_CELL_UNVERIFIED"]==1
    parsed=json.loads((tmp_path/"out/unmatched_zone_page_leads.jsonl").read_text())
    assert parsed["source_candidates"][0]["page"]==1
    assert parsed["approved_for_analysis"] is False
    assert parsed["source_candidates"][0]["matching_text"]=="ZONE_NAME_ONLY_NOT_A_CELL"
