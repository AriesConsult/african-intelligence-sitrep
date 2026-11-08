"""Tidy CSV preserves an unresolved discrepancy without numeric autoapproval."""
import gzip,json,csv
from export_historical_review_csv import export

def test_tidy_export_preserves_source_and_not_approved(tmp_path):
    data={"date":"2026-10-30","metric_id":"national_cumulative_confirmed_deaths",
      "geography_raw":"DRC","decision_value":5058,"source_value_raw":"5058",
      "status":"SINGLE_SOURCE_NUMERIC_CANDIDATE",
      "evidence_class":"PDF_INRB_DIFFERENCE_PENDING_ADJUDICATION",
      "derivation_class":"INRB_DOCUMENTED_DIRECT_NATIONAL_BANNER_TRANSCRIPTION",
      "inrb_commit":"a"*40,"source_records":[{"inrb_csv_path":"x.csv",
        "inrb_csv_sha256":"b"*64,"inrb_csv_row_number":23}],
      "report_matches":[{"source_pdf_sha256":"c"*64}],
      "pdf_comparison_evidence":[{"report_number":169,"pdf_sha256":"c"*64,
        "pdf_page":1,"pdf_candidate_value":5372,
        "comparison_status":"DIFFERENCE_REVIEW_REQUIRED"}]}
    input=tmp_path/"aligned.jsonl.gz"
    with gzip.open(input,"wt") as f:f.write(json.dumps(data)+"\n")
    summary=tmp_path/"summary.json";summary.write_text(json.dumps({
      "records":1,"schema_version":"bdbv-historical-evidence-alignment-v1",
      "source_inrb_commit":"a"*40}))
    result=export(input,summary,tmp_path/"out")
    with (tmp_path/"out/historical_long_review_only.csv").open() as f:row=next(csv.DictReader(f))
    assert row["value"]=="5058"
    assert row["approved_for_analysis"]=="FALSE"
    assert row["pdf_comparison_statuses"]=="DIFFERENCE_REVIEW_REQUIRED"
    assert result["total_rows"]==1
