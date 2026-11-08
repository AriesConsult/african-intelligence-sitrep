#!/usr/bin/env python3
"""Assemble a reproducible historical BDBV series from pinned INRB candidates.

The long-form collection is useful for analysis preparation, NOT a fully
source-cell-verified incidence dataset. No date or geographic alias is guessed.
Both raw source records and an unambiguous provisional time series are kept.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

CUMULATIVE_METRICS={
 "cumulative_confirmed_cases","cumulative_confirmed_deaths",
 "cumulative_contacts_isolated","cumulative_contacts_traced",
 "cumulative_suspected_cases","cumulative_suspected_deaths",
 "national_cumulative_confirmed_cases","national_cumulative_confirmed_deaths",
 "national_cumulative_recovered_cases","national_cumulative_suspected_cases",
 "national_cumulative_suspected_deaths"
}
DIRECT_NATIONAL={"national_cumulative_confirmed_cases","national_cumulative_confirmed_deaths"}
UNALLOCATED={"NA","Sans Fiche",""}
def record_key(row):
    return (row["metric_id"],row["geography_raw"],row["date_raw"],
            json.dumps(row.get("extra_columns_raw") or {},sort_keys=True,ensure_ascii=False))

def assemble(staged: Path, output: Path):
    metadata=json.loads((staged/"inrb_staging_summary.json").read_text(encoding="utf-8"))
    if metadata.get("status")!="INRB_SERIES_STAGED_NOT_PDF_VERIFIED":raise ValueError("Unexpected INRB source status")
    sourcefile=staged/"inrb_observation_candidates.jsonl.gz"
    groups=defaultdict(list)
    source_count=Counter()
    with gzip.open(sourcefile,"rt",encoding="utf-8") as inp:
        for line in inp:
            item=json.loads(line)
            if item.get("inrb_commit")!=metadata["inrb_commit"]:
                raise ValueError("Staged observation from a different upstream revision")
            groups[record_key(item)].append(item)
            source_count["rows"]+=1
    expected=metadata["counts"].get("rows")
    if source_count["rows"]!=expected:
        raise ValueError(f"Source count mismatch: {source_count['rows']} != {expected}")
    output.mkdir(parents=True,exist_ok=True)
    statuses=Counter()
    observations=[]
    for key,versions in sorted(groups.items()):
        m,geo,day,extra=key
        distinct={(json.dumps(v.get("value_parsed"),sort_keys=True),v.get("value_status"),v.get("value_raw")) for v in versions}
        date_ok=all(v.get("date_valid") for v in versions)
        if len(versions)>1 and len(distinct)>1:state="CONFLICTING_DUPLICATE_SOURCE_ROWS"
        elif len(versions)>1:state="REPEATED_IDENTICAL_SOURCE_ROW"
        elif not date_ok:state="INVALID_SOURCE_DATE"
        elif versions[0]["value_status"]=="NOT_REPORTED":state="EXPLICIT_ND"
        elif versions[0]["value_status"]!="NUMERIC_UNVERIFIED":state="NONNUMERIC_OR_MISSING"
        elif geo in UNALLOCATED:state="UNALLOCATED_GEOGRAPHY"
        else:state="SINGLE_SOURCE_NUMERIC_CANDIDATE"
        row=versions[0]
        if m in DIRECT_NATIONAL:derivation="INRB_DOCUMENTED_DIRECT_NATIONAL_BANNER_TRANSCRIPTION"
        elif m in CUMULATIVE_METRICS:derivation="INRB_CURATED_CUMULATIVE_POTENTIALLY_CARRIED_FORWARD_OR_DERIVED"
        else:derivation="INRB_CURATED_SOURCE_METHOD_UNVERIFIED"
        item={"metric_id":m,"geography_raw":geo,"date":day,
              "extra_columns_raw":row.get("extra_columns_raw") or {},
              "source_value_raw":row.get("value_raw"),
              "value":row.get("value_parsed") if state=="SINGLE_SOURCE_NUMERIC_CANDIDATE" else None,
              "status":state,"derivation_class":derivation,
              "source_records":[{"inrb_csv_path":v["inrb_csv_path"],
                 "inrb_csv_sha256":v["inrb_csv_sha256"],
                 "inrb_csv_row_number":v["inrb_csv_row_number"],
                 "raw_value":v["value_raw"]} for v in versions],
              "report_matches":row.get("date_matched_registry_sources") or [],
              "historical_role":"PROVISIONAL_CURATED_AS_RECORDED_AT_INRB_REVISION",
              "pdf_cell_verified":False,"approved_for_analysis":False,
              "inrb_commit":metadata["inrb_commit"]}
        observations.append(item)
        statuses[state]+=1
    # Temporal anomalies are review flags, NOT automatic replacement with later reports.
    chronological=defaultdict(list)
    for row in observations:
        if row["status"]=="SINGLE_SOURCE_NUMERIC_CANDIDATE" and row["metric_id"] in CUMULATIVE_METRICS:
            chronological[(row["metric_id"],row["geography_raw"],
                           json.dumps(row["extra_columns_raw"],sort_keys=True))].append(row)
    revisions=[]
    for (metric,geo,_),rows in chronological.items():
        rows.sort(key=lambda r:r["date"])
        last=None
        for row in rows:
            if last is not None and row["value"]<last["value"]:
                revisions.append({"metric_id":metric,"geography_raw":geo,
                    "previous_date":last["date"],"previous_value":last["value"],
                    "current_date":row["date"],"current_value":row["value"],
                    "delta":row["value"]-last["value"],
                    "classification":"DECREASE_IN_CUMULATIVE_CURATED_SERIES_REQUIRES_SOURCE_CHECK",
                    "not_interpreted_as_negative_cases":True})
            last=row
    # Retain observations in source chronological order for columnar consumers.
    observations.sort(key=lambda r:(r["date"],r["metric_id"],r["geography_raw"],
                                   json.dumps(r["extra_columns_raw"],sort_keys=True)))
    with gzip.open(output/"historical_curated_candidates.jsonl.gz","wt",encoding="utf-8",compresslevel=6) as dest:
        for row in observations:dest.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
    with (output/"historical_coverage.csv").open("w",encoding="utf-8",newline="") as dest:
        writer=csv.DictWriter(dest,fieldnames=["metric_id","source_rows","unique_observation_keys",
                  "numeric_candidates","explicit_ND","conflicting_keys","first_date","last_date"])
        writer.writeheader()
        per_metric=defaultdict(list)
        for row in observations:per_metric[row["metric_id"]].append(row)
        for metric,rows in sorted(per_metric.items()):
            dates=sorted({row["date"] for row in rows if len(row["date"])==10 and row["date"][4]=="-"})
            writer.writerow({"metric_id":metric,
                "source_rows":sum(len(r["source_records"]) for r in rows),
                "unique_observation_keys":len(rows),
                "numeric_candidates":sum(r["status"]=="SINGLE_SOURCE_NUMERIC_CANDIDATE" for r in rows),
                "explicit_ND":sum(r["status"]=="EXPLICIT_ND" for r in rows),
                "conflicting_keys":sum(r["status"]=="CONFLICTING_DUPLICATE_SOURCE_ROWS" for r in rows),
                "first_date":dates[0] if dates else "", "last_date":dates[-1] if dates else ""})
    with (output/"historical_cumulative_revision_flags.csv").open("w",newline="",encoding="utf-8") as dest:
        fields=["metric_id","geography_raw","previous_date","previous_value",
                "current_date","current_value","delta","classification","not_interpreted_as_negative_cases"]
        writer=csv.DictWriter(dest,fieldnames=fields);writer.writeheader();writer.writerows(revisions)
    summary={"schema_version":"bdbv-historical-assembly-v1",
       "generated_at":datetime.now(timezone.utc).isoformat(),
       "inrb_commit":metadata["inrb_commit"],"source_rows":source_count["rows"],
       "unique_observation_keys":len(observations),"observations_by_status":dict(statuses),
       "cumulative_decrease_flags":len(revisions),
       "coverage_metrics":len({x["metric_id"] for x in observations}),
       "source_data_limitations":[
          "A single pinned INRB repo revision is NOT a true historical vintage archive: its rows may have been retrospectively revised.",
          "As-reported-by-SitRep values require independent original-PDF cell verification; INRB direct banner claims do not replace this.",
          "As-recorded-in-INRB-revision data must not be renamed as latest epidemiologically corrected incidence.",
          "Retrospective cumulative corrections cannot be allocated to earlier days without explicit source evidence.",
          "Unknown dates, duplicates, ND, NA and absent source cells are preserved without imputation.",
          "Geography uses exact source labels until validated canonical-zone/province mapping is completed."],
       "release_gate":"REVIEW_ONLY_NO_PUBLIC_FEED_IMPORT",
       "approved_for_analysis":0}
    (output/"historical_assembly_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--staged-dir",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    assemble(a.staged_dir,a.out)
