"""Source-verified SitRep 169 values can resolve transcription, not a whole epidemic series."""
import csv,json
from adjudicate_historical_exceptions import resolve,SITREP169_HASH

def test_documented_169_original_cells_preserved_without_upstream_overwrite(tmp_path):
    revisions=tmp_path/"revisions.csv"
    with revisions.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["metric_id","geography_raw","previous_date","previous_value","current_date","current_value","delta"])
        w.writeheader();w.writerow({"metric_id":"cumulative_confirmed_cases","geography_raw":"Bunia",
        "previous_date":"2026-10-29","previous_value":120,"current_date":"2026-10-30","current_value":119,"delta":-1})
    zone=tmp_path/"zone.jsonl"
    zone.write_text(json.dumps({"date":"2026-10-30","metric_id":"cumulative_confirmed_cases",
        "geography":"Nyankunde","status":"DIFFERENCE_REQUIRES_SOURCE_PAGE_REVIEW",
        "pdf_value":154,"inrb_value_raw":"139","pdf_report":169,"pdf_sha256":SITREP169_HASH,"pdf_page":3})+"\n")
    national=tmp_path/"national.csv"
    with national.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["report_number","report_date","source_pdf_sha256","pdf_page",
            "metric_id","pdf_value_candidate","inrb_value","outcome"])
        w.writeheader();w.writerow({"report_number":169,"report_date":"2026-10-30",
            "source_pdf_sha256":SITREP169_HASH,"pdf_page":1,
            "metric_id":"national_cumulative_confirmed_deaths","pdf_value_candidate":32,
            "inrb_value":5058,"outcome":"DIFFERENCE_REVIEW_REQUIRED"})
    triage=tmp_path/"triage.csv"
    with triage.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["diagnosis"]);w.writeheader()
    result=resolve(revisions,zone,national,triage,tmp_path/"out")
    assert result["resolved_original_pdf_169_cells"]==1
    assert result["resolved_169_national_revision"]==1
    assert result["approved_for_research_grade"]==0
    with (tmp_path/"out/historical_exception_decision_register.csv").open() as f:
        rows=list(csv.DictReader(f))
    assert any(r["curated_INRB_value"]=="139" and r["original_pdf_candidate"]=="154" for r in rows)
    assert any(r["disposition"].startswith("CUMULATIVE_DROP_") for r in rows)
    assert any(r["metric"]=="national_cumulative_confirmed_deaths" and r["original_pdf_candidate"]=="32" and r["verified_pdf_value"]=="5372" and r["machine_pdf_reading_agrees_with_verified_value"]=="False" for r in rows)
