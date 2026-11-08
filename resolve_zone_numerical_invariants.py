#!/usr/bin/env python3
"""Disentangle numeric value ambiguity from unresolved physical row provenance.

For 113 same-value/same-province matches, the numerical candidate is invariant
among PDF-row choices, but physical source-row identity remains uncertain.
Never upgrade these to verified source cells or accepted incidence.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from pathlib import Path

def reconcile(source,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    count=Counter();seen=set();rows=[]
    with Path(source).open(encoding="utf-8") as fp:
        for line in fp:
            if not line.strip():continue
            r=json.loads(line)
            key=(r["date"],r["metric_id"],r["geography"])
            if key in seen:raise ValueError("Duplicate ambiguity key")
            seen.add(key)
            entries=r["candidate_rows"]
            vals={x["value"] for x in entries}
            provinces={x.get("province") for x in entries}
            source_keys={(x["pdf_sha256"],x["page"],x["table_id"],x["source_row"],x.get("province"))
                         for x in entries}
            if len(source_keys)<2:raise ValueError("Expected distinct physical rows")
            if len(provinces)==1 and len(vals)==1:
                status="NUMERIC_VALUE_INVARIANT_BUT_PHYSICAL_PDF_ROW_UNRESOLVED"
                numeric_value=next(iter(vals))
            elif len(provinces)>1:
                status="GEOGRAPHIC_CROSS_PROVINCE_AMBIGUITY_REQUIRES_REVIEW"
                numeric_value=None
            elif len(vals)>1:
                status="CONFLICTING_NUMERIC_PDF_ROW_VALUES_REQUIRE_REVIEW"
                numeric_value=None
            else:
                status="UNRESOLVED_NONUNIQUE_SOURCE_ROWS"
                numeric_value=None
            count[status]+=1
            rows.append({"date":r["date"],"metric_id":r["metric_id"],"geography":r["geography"],
               "candidate_numeric_value":numeric_value,"inrb_value_raw":r.get("inrb_value_raw"),
               "source_candidates":entries,"number_distinct_physical_cells":len(source_keys),
               "status":status,"source_transcription_verified":False,
               "approved_for_analysis":False})
    if sum(count.values())!=174:raise ValueError("Expected all 174 original ambiguous source matches")
    with (out/"healthzone_ambiguity_numeric_disposition.jsonl").open("w",encoding="utf-8") as fp:
        for row in rows:fp.write(json.dumps(row,ensure_ascii=False)+"\n")
    report={"schema_version":"bdbv-ambiguous-rows-numeric-disposition-v1",
        "status":"NUMERIC_INVARIANTS_IDENTIFIED_ORIGINAL_ROW_IDENTITY_REVIEW_PENDING",
        "original_ambiguous_row_count":174,
        "numeric_consensus_candidates":count["NUMERIC_VALUE_INVARIANT_BUT_PHYSICAL_PDF_ROW_UNRESOLVED"],
        "numerical_or_geographic_ambiguities_remaining":sum(v for k,v in count.items() if k!="NUMERIC_VALUE_INVARIANT_BUT_PHYSICAL_PDF_ROW_UNRESOLVED"),
        "source_row_identity_still_unverified":174,
        "classification_counts":dict(count),"approved_for_analysis":0,
        "warning":"Same numeric value on different extracted PDF rows reduces numerical uncertainty only; it does not identify the original cell or prove absence of duplicated or misassigned health zones."}
    (out/"healthzone_ambiguity_numeric_summary.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();reconcile(a.source,a.out)
