#!/usr/bin/env python3
"""Export full source-linked provisional BDBV historical layer as tidy CSV.

No implicit approval, carry-forward filling, geographic mapping or
retrospective reallocation is performed. This is an analyst review dataset.
"""
import argparse,csv,gzip,json
from collections import Counter,defaultdict
from pathlib import Path

FIELDS=("date","metric_id","geography_source_label","geography_grain_unverified",
        "value","raw_value","source_value_status","evidence_class",
        "source_derivation_class","curated_data_revision","inrb_csv_path",
        "inrb_csv_sha256","inrb_csv_row_number","inrb_source_report_hashes",
        "pdf_comparison_report_numbers","pdf_comparison_sha256","pdf_comparison_pages",
        "pdf_comparison_statuses","extra_dimensions_json","approved_for_analysis")

def export(infile,summaryfile,output):
    source=json.loads(Path(summaryfile).read_text(encoding="utf-8"))
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    n=0;status=Counter();per_metric=defaultdict(Counter)
    with gzip.open(infile,"rt",encoding="utf-8") as inp,(output/"historical_long_review_only.csv").open("w",newline="",encoding="utf-8") as out:
        w=csv.DictWriter(out,fieldnames=FIELDS);w.writeheader()
        for line in inp:
            item=json.loads(line)
            val=item.get("decision_value")
            refs=item.get("pdf_comparison_evidence") or []
            records=item.get("source_records") or []
            registered=item.get("report_matches") or []
            rating=item["evidence_class"]
            result={
              "date":item["date"],"metric_id":item["metric_id"],
              "geography_source_label":item["geography_raw"],
              "geography_grain_unverified":"NATIONAL" if item["metric_id"].startswith("national_") and item["geography_raw"]=="DRC" else "GRAIN_REQUIRES_GEO_REFERENCE",
              "value":val if val is not None else "",
              "raw_value":item.get("source_value_raw") or "",
              "source_value_status":item["status"],
              "evidence_class":rating,
              "source_derivation_class":item.get("derivation_class"),
              "curated_data_revision":item["inrb_commit"],
              "inrb_csv_path":";".join(sorted({x["inrb_csv_path"] for x in records})),
              "inrb_csv_sha256":";".join(sorted({x["inrb_csv_sha256"] for x in records})),
              "inrb_csv_row_number":";".join(str(x["inrb_csv_row_number"]) for x in records),
              "inrb_source_report_hashes":";".join(sorted({x["source_pdf_sha256"] for x in registered if x.get("source_pdf_sha256")})),
              "pdf_comparison_report_numbers":";".join(sorted({str(x["report_number"]) for x in refs if x.get("report_number")})),
              "pdf_comparison_sha256":";".join(sorted({str(x["pdf_sha256"]) for x in refs if x.get("pdf_sha256")})),
              "pdf_comparison_pages":";".join(sorted({str(x["pdf_page"]) for x in refs if x.get("pdf_page")})),
              "pdf_comparison_statuses":";".join(sorted({str(x["comparison_status"]) for x in refs if x.get("comparison_status")})),
              "extra_dimensions_json":json.dumps(item.get("extra_columns_raw") or {},ensure_ascii=False,sort_keys=True),
              "approved_for_analysis":"FALSE"}
            w.writerow(result)
            status[rating]+=1;per_metric[item["metric_id"]][rating]+=1;n+=1
    if n!=source["records"]:raise ValueError("Historic alignment row count mismatch")
    with (output/"historical_evidence_coverage_by_metric.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["metric_id","evidence_class","observation_rows"])
        w.writeheader()
        for metric,distribution in sorted(per_metric.items()):
            for klass,count in sorted(distribution.items()):
                w.writerow({"metric_id":metric,"evidence_class":klass,"observation_rows":count})
    readme={"schema_version":"bdbv-tidy-analyst-review-export-v1",
        "source_historical_alignment_schema":source["schema_version"],
        "total_rows":n,"status":"REPRODUCIBLE_ANALYST_REVIEW_ONLY",
        "inrb_commit":source["source_inrb_commit"],
        "evidence_classes":dict(status),
        "variable_notes":{
          "date":"Original unadjusted INRB row date; not necessarily the SitRep publication or true event date",
          "geography_source_label":"Literal INRB geography name, not necessarily health zone; do not assume all rows share geographic grain",
          "value":"Curated source value as at frozen revision; empty when ND/missing/conflicted",
          "source_derivation_class":"Possible carried forward, calculated or source-provided modes; not independently proven",
          "evidence_class":"PDF concordance and extraction review status; no claim of independent epidemiological confirmation",
          "approved_for_analysis":"Always FALSE until cell-level verification and the historical acceptance procedure are completed"},
        "prohibition":"Do not interpret this CSV as finalized incidence, fully reconstructed historical snapshots, or the public African Intelligence accepted feed."}
    (output/"HISTORICAL_DATA_DICTIONARY.json").write_text(json.dumps(readme,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"rows":n,"metrics":len(per_metric),"status":readme["status"]},indent=2))
    return readme

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--aligned",type=Path,required=True)
    p.add_argument("--summary",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();export(a.aligned,a.summary,a.out)
