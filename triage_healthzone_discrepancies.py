#!/usr/bin/env python3
"""Diagnose health-zone concordance disagreements without changing values or dates.

An adjacent-day match is a clue, never a verified date correction. Compare
only the same metric and raw health-zone name, preserving all original inputs.
"""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

METRICS={"cumulative_confirmed_cases","cumulative_confirmed_deaths"}

def classify(review_csv, upstream_csv_dir, out):
    with Path(review_csv).open(encoding="utf-8-sig",newline="") as f:
        review=list(csv.DictReader(f))
    values={}
    for metric in sorted(METRICS):
        path=Path(upstream_csv_dir)/f"insp_sitrep__{metric}__daily.csv"
        with path.open(encoding="utf-8-sig",newline="") as fp:
            rows=csv.DictReader(fp)
            index=defaultdict(list)
            for row in rows:
                index[(row["nom"],row["date"])].append(row[metric])
        values[metric]=index
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    classified=[]
    report_counts=defaultdict(Counter)
    for r in review:
        entry=dict(r)
        status=r.get("status","")
        offsets=[]
        if status=="DIFFERENCE_REQUIRES_SOURCE_PAGE_REVIEW":
            metric=r["metric_id"]
            try:reported=date.fromisoformat(r["date"])
            except ValueError:reported=None
            if reported is not None and metric in values:
                for offset in (-1,1):
                    alternative=(reported+timedelta(days=offset)).isoformat()
                    options=values[metric].get((r["geography"],alternative),[])
                    if len(options)==1 and options[0]==r["pdf_value"]:
                        offsets.append(offset)
            if len(offsets)==1:
                classification="POSSIBLE_ADJACENT_DATE_ALIGNMENT_REVIEW_REQUIRED"
            elif offsets:
                classification="MULTIPLE_ADJACENT_DATE_CANDIDATES_REVIEW_REQUIRED"
            else:
                classification="PERSISTENT_VALUE_DISAGREEMENT_REVIEW_REQUIRED"
        else:
            classification=status
        entry["possible_date_offsets_days"]=";".join(str(o) for o in offsets)
        entry["diagnosis"]=classification
        entry["approved_for_analysis"]=False
        classified.append(entry)
        report_counts[r.get("pdf_report") or "UPSTREAM_ONLY"][classification]+=1
    with (out/"healthzone_adjudication_triage.csv").open("w",newline="",encoding="utf-8") as f:
        fields=list(classified[0]) if classified else ["diagnosis"]
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(classified)
    summary={
      "schema_version":"bdbv-historical-discrepancy-triage-v1",
      "status":"CANDIDATE_DIAGNOSES_NOT_ADJUDICATED",
      "items_checked":len(classified),
      "classifications":dict(Counter(x["diagnosis"] for x in classified)),
      "by_report":{k:dict(v) for k,v in sorted(report_counts.items())},
      "policy":"No value or reporting date may be corrected by matching an adjacent day's curated CSV. Compare against PDF cover and relevant Table II row first.",
      "approved_for_analysis":0}
    (out/"healthzone_adjudication_triage.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))
    return summary

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--review-csv",type=Path,required=True)
    parser.add_argument("--upstream-csv-dir",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    a=parser.parse_args()
    classify(a.review_csv,a.upstream_csv_dir,a.out)
