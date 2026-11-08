"""Cross-vintage and numerical disagreement must never silently overwrite curated values."""
import csv,gzip,json
from align_historical_evidence import build

def test_pdf_difference_keeps_curated_vintage_and_review_flag(tmp_path):
    h=tmp_path/"history";h.mkdir()
    (h/"historical_assembly_summary.json").write_text(json.dumps({"inrb_commit":"a"*40}))
    item={"metric_id":"cumulative_confirmed_cases","geography_raw":"Bunia","date":"2026-07-01",
      "inrb_commit":"a"*40,"status":"SINGLE_SOURCE_NUMERIC_CANDIDATE","value":15,
      "source_records":[{"inrb_csv_path":"cases.csv","inrb_csv_row_number":3}]}
    with gzip.open(h/"historical_curated_candidates.jsonl.gz","wt") as fp:fp.write(json.dumps(item)+"\n")
    z=tmp_path/"zone.jsonl"
    z.write_text(json.dumps({"date":"2026-07-01","metric_id":"cumulative_confirmed_cases",
        "geography":"Bunia","inrb_commit":"a"*40,"inrb_csv_path":"cases.csv",
        "inrb_csv_row":3,"status":"DIFFERENCE_REQUIRES_SOURCE_PAGE_REVIEW",
        "pdf_value":16,"pdf_report":49,"pdf_page":2})+"\n")
    n=tmp_path/"national.csv"
    with n.open("w",newline="") as fp:
        w=csv.DictWriter(fp,fieldnames=["inrb_commit","report_date","metric_id"]);w.writeheader()
    result=build(h,z,n,tmp_path/"out")
    assert result["statuses"]["PDF_INRB_DIFFERENCE_PENDING_ADJUDICATION"]==1
    with gzip.open(tmp_path/"out/historical_evidence_aligned.jsonl.gz","rt") as fp:row=json.loads(fp.readline())
    assert row["decision_value"]==15 and row["pdf_comparison_evidence"][0]["pdf_candidate_value"]==16
    assert row["research_grade_approved"] is False
