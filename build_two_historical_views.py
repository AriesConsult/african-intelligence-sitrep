#!/usr/bin/env python3
"""Build two NON-CONFLATED historical evidential views, not a fabricated corrected series.

1) INRB curated at pinned commit, 15726 rows and uncertain derivation.
2) Only PDF values with explicit visual transcription evidence and source hash.

Pair observations by exact source date, metric and geography label; preserve
different versions side by side. No retrospective case redistribution.
"""
from __future__ import annotations
import argparse,csv,gzip,json,unicodedata,re
from collections import Counter,defaultdict
from pathlib import Path

def canonical(s):
    s="".join(ch for ch in unicodedata.normalize("NFKD",str(s or "").lower())
          if not unicodedata.combining(ch))
    return re.sub(r"\s+"," ",s).strip()

def make(accepted_pdf,curated,curated_summary,out):
    summary=json.loads(Path(curated_summary).read_text(encoding="utf-8"))
    ref={}
    with Path(accepted_pdf).open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f):
            if row["verbatim_transcription_verified"]!="True":
                raise ValueError("Unverified PDF value included in accepted transcription ledger")
            key=(row["report_date"],row["metric_id"],canonical(row["geography"]))
            if key in ref:raise ValueError("Multiple reviewed PDF values per date/metric/geography require version disambiguation")
            ref[key]=row
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    matched=set();counts=Counter()
    with gzip.open(curated,"rt",encoding="utf-8") as src,gzip.open(out/"two_evidence_vintages.jsonl.gz","wt",encoding="utf-8") as dest:
        for line in src:
            row=json.loads(line)
            key=(row["date"],row["metric_id"],canonical(row["geography_raw"]))
            original=ref.get(key)
            if original:matched.add(key)
            curated_value=row.get("decision_value")
            original_value=int(original["verbatim_source_value"]) if original else None
            if original is None:klass="CURATED_ONLY_SOURCE_PDF_REVIEW_PENDING"
            elif curated_value is None:klass="DIRECT_PDF_VERIFIED_CURATED_NONNUMERIC"
            elif curated_value==original_value:klass="CURATED_AND_VERBATIM_PDF_CONCORDANT"
            else:klass="CURATED_AND_VERBATIM_PDF_DIFFERENT_RETAIN_BOTH"
            counts[klass]+=1
            dest.write(json.dumps({
                "date":row["date"],"metric_id":row["metric_id"],
                "geography_raw":row["geography_raw"],"geography_grain_unverified":row.get("extra_columns_raw"),
                "curated_inrb_commit":row["inrb_commit"],
                "curated_value":curated_value,
                "curated_original_raw_value":row.get("source_value_raw"),
                "curated_source_rows":row.get("source_records"),
                "curated_evidence_class":row.get("evidence_class"),
                "direct_pdf_as_reported":original_value,
                "direct_pdf_sha256":original["source_pdf_sha256"] if original else None,
                "direct_pdf_report_number":int(original["report_number"]) if original else None,
                "direct_pdf_page":int(original["source_page"]) if original else None,
                "direct_pdf_review_document":original["adjudication_basis"] if original else None,
                "direct_pdf_source_conflicts_json":original["source_conflicts_json"] if original else None,
                "two_view_consistency":klass,
                "verbatim_pdf_value_verified":bool(original),
                "full_retroactive_epidemiological_series_approved":False},ensure_ascii=False)+"\n")
    # The as-reported view must not disappear because the curated data has no
    # aligned record at an original report date (e.g. historical gaps).
    for key,pdf in sorted(ref.items()):
        if key in matched:continue
        counts["VERIFIED_PDF_ONLY_NO_SAME_DATE_CURATED_ROW"]+=1
        with gzip.open(out/"direct_pdf_only_unmatched.jsonl.gz","at",encoding="utf-8") as f:
            f.write(json.dumps({"date":key[0],"metric_id":key[1],"geography":pdf["geography"],
               "value":int(pdf["verbatim_source_value"]),"report":int(pdf["report_number"]),
               "source_sha256":pdf["source_pdf_sha256"],"source_page":int(pdf["source_page"]),
               "status":"VERIFIED_VERBATIM_PDF_ONLY_NO_CURATED_MATCH",
               "epidemiological_incidence_certified":False})+"\n")
    if sum(counts.values())-counts["VERIFIED_PDF_ONLY_NO_SAME_DATE_CURATED_ROW"]!=summary["records"]:
        raise ValueError("Historical curated observation count changed")
    result={"schema_version":"bdbv-two-historical-evidence-views-v1",
        "status":"TWO_VERSION_VIEWS_PRESERVED_FINAL_RETROSPECTIVE_ADJUDICATION_PENDING",
        "curated_rows":summary["records"],
        "verified_pdf_as_reported_rows":len(ref),
        "verified_pdf_curated_row_matches":len(matched),
        "cross_view_comparison_counts":dict(counts),
        "inrb_commit":summary["source_inrb_commit"],
        "scientific_cautions":[
            "The as-reported PDF view is sparse but only contains explicitly visually checked cells.",
            "The INRB curated view is more complete, but its retrospective source transformations are not all verified.",
            "Different reported and curated values are retained together; no formula silently picks a winner.",
            "An accepted national or health-zone cumulative total is not a back-corrected daily incident series.",
            "The two views cannot be merged into one research-grade historical time series without documented per-indicator revision rules."]}
    (out/"two_historical_views_summary.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--pdf-verified",type=Path,required=True)
    p.add_argument("--curated",type=Path,required=True)
    p.add_argument("--curated-summary",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();make(a.pdf_verified,a.curated,a.curated_summary,a.out)
