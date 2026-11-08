import csv,gzip,json
from build_two_historical_views import make

def test_distinct_historical_views_never_overwrite_source(tmp_path):
    pdf=tmp_path/"pdf.csv"
    with pdf.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["report_date","metric_id","geography","verbatim_transcription_verified",
           "verbatim_source_value","source_pdf_sha256","report_number","source_page","adjudication_basis","source_conflicts_json"])
        w.writeheader()
        w.writerow({"report_date":"2026-10-30","metric_id":"national_cumulative_confirmed_deaths","geography":"DRC",
           "verbatim_transcription_verified":True,"verbatim_source_value":5372,
           "source_pdf_sha256":"a"*64,"report_number":169,"source_page":1,"adjudication_basis":"source-review",
           "source_conflicts_json":"[]"})
    curated=tmp_path/"curated.gz"
    item={"date":"2026-10-30","metric_id":"national_cumulative_confirmed_deaths",
          "geography_raw":"DRC","decision_value":5058,"source_value_raw":"5058",
          "source_records":[{"inrb_csv_path":"x.csv"}],"inrb_commit":"b"*40}
    with gzip.open(curated,"wt") as f:f.write(json.dumps(item)+"\n")
    summary=tmp_path/"summary.json";summary.write_text(json.dumps({"records":1,"source_inrb_commit":"b"*40}))
    result=make(pdf,curated,summary,tmp_path/"out")
    assert result["cross_view_comparison_counts"]["CURATED_AND_VERBATIM_PDF_DIFFERENT_RETAIN_BOTH"]==1
    with gzip.open(tmp_path/"out/two_evidence_vintages.jsonl.gz","rt") as f:row=json.loads(f.readline())
    assert row["direct_pdf_as_reported"]==5372 and row["curated_value"]==5058
    assert row["full_retroactive_epidemiological_series_approved"] is False
