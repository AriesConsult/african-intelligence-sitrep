import csv,gzip,json
from accept_historical_qualified import acceptance

def test_excludes_unverified_scan_and_retains_conflicting_pdf(tmp_path):
    data=tmp_path/"in";data.mkdir()
    keys=[
        {"date":"2026-10-30","metric_id":"national_cumulative_confirmed_deaths","geography_raw":"DRC",
         "decision_value":5058,"status":"SINGLE_SOURCE_NUMERIC_CANDIDATE",
         "evidence_class":"PDF_INRB_DIFFERENCE_PENDING_ADJUDICATION",
         "source_records":[{"inrb_csv_path":"national.csv","inrb_csv_sha256":"c"*64,"inrb_csv_row_number":2}]},
        {"date":"2026-05-21","metric_id":"cumulative_confirmed_cases","geography_raw":"Bunia",
         "decision_value":22,"status":"SINGLE_SOURCE_NUMERIC_CANDIDATE",
         "evidence_class":"INRB_VINTAGE_ONLY_NO_CELL_LINK",
         "source_records":[{"inrb_csv_path":"zone.csv","inrb_csv_sha256":"d"*64,"inrb_csv_row_number":3}]}
    ]
    aligned=data/"aligned.gz"
    with gzip.open(aligned,"wt") as f:
        for r in keys:f.write(json.dumps({**r,"inrb_commit":"c00b8843e6ebae8f0cd846bc43cb564a3893bfd9"})+"\n")
    views=[
        {"date":"2026-10-30","metric_id":"national_cumulative_confirmed_deaths",
         "geography_raw":"DRC","curated_source_rows":keys[0]["source_records"],
         "curated_inrb_commit":"c00b8843e6ebae8f0cd846bc43cb564a3893bfd9",
         "two_view_consistency":"CURATED_AND_VERBATIM_PDF_DIFFERENT_RETAIN_BOTH",
         "verbatim_pdf_value_verified":True,"direct_pdf_as_reported":5372,
         "direct_pdf_report_number":169,"direct_pdf_sha256":"a"*64,"direct_pdf_page":1},
        {"date":"2026-05-21","metric_id":"cumulative_confirmed_cases","geography_raw":"Bunia",
         "curated_source_rows":keys[1]["source_records"],
         "curated_inrb_commit":"c00b8843e6ebae8f0cd846bc43cb564a3893bfd9",
         "two_view_consistency":"CURATED_ONLY_SOURCE_PDF_REVIEW_PENDING",
         "verbatim_pdf_value_verified":False}
    ]
    two=data/"two.gz"
    with gzip.open(two,"wt") as f:
        for r in views:f.write(json.dumps(r)+"\n")
    summary=data/"summary.json";summary.write_text(json.dumps({
       "source_inrb_commit":"c00b8843e6ebae8f0cd846bc43cb564a3893bfd9",
       "records":2}))
    verified=data/"verified.csv"
    with verified.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["report_date","metric_id","geography",
           "verbatim_source_value","verbatim_transcription_verified"])
        w.writeheader()
        w.writerow({"report_date":"2026-10-30","metric_id":"national_cumulative_confirmed_deaths",
           "geography":"DRC","verbatim_source_value":5372,"verbatim_transcription_verified":True})
        for i in range(16):
            w.writerow({"report_date":"2026-01-"+str(i+1).zfill(2),
               "metric_id":"placeholder"+str(i),"geography":"X","verbatim_source_value":1,
               "verbatim_transcription_verified":True})
    revision=data/"rev.csv"
    with revision.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["current_date","metric_id","geography_raw"])
        w.writeheader()
        for i in range(114):
            w.writerow({"current_date":"2026-08-"+str(i%28+1).zfill(2),
              "metric_id":"metric"+str(i),"geography_raw":"Zone"+str(i)})
    scans=data/"scans.json";scans.write_text(json.dumps({"source_records":[
       {"report_number":7,"report_date":"2026-05-21"},
       {"report_number":8,"report_date":"2026-05-22"},
       {"report_number":9,"report_date":"2026-05-23"}]}))
    # Tiny synthetic fixture deliberately fails the real production cardinality gate.
    try:
        acceptance(two,aligned,summary,verified,revision,scans,tmp_path/"out")
    except ValueError as exc:
        assert "cardinality changed" in str(exc)
    else:
        raise AssertionError("Must fail closed on incomplete historical source set")
    # Even before cardinality rejection, values must not silently become approved.
    rows=list(csv.DictReader((tmp_path/"out/historical_qualified_release.csv").open()))
    assert rows[0]["original_pdf_verified_value"]=="5372"
    assert rows[0]["curated_value"]=="5058"
    assert rows[0]["curated_value_eligible_for_qualified_descriptive_use"]=="FALSE"
    assert rows[1]["scanned_report_exclusion_applies"]=="TRUE"
    assert rows[1]["curated_value_eligible_for_qualified_descriptive_use"]=="FALSE"
