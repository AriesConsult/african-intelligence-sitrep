#!/usr/bin/env python3
"""Conservative provincial SitRep table evidence and coverage audit.

Cross-check Table I reported provincial totals with Table II province rows and
health-zone sums. Missing extraction never becomes a reported zero or approved
observation; reconstructed province sums are diagnostic only.
"""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

FIELDS=("cumulative_cases","cumulative_deaths")

def audit(registry_path,published,output):
    registry=json.loads(Path(registry_path).read_text(encoding="utf-8"))
    reports=[]
    details=[]
    counts=Counter()
    for d in sorted(registry["documents"].values(),key=lambda x:x["report_number"]):
        number=d["report_number"];sha=d["sha256"];date=d["report_date"]
        snapshot=Path(published)/"tables"/f"{number:03d}_{sha[:12]}.json"
        if not snapshot.is_file():
            report_status="NO_TABLE_SNAPSHOT"
            counts[report_status]+=1
            reports.append({"report_number":number,"report_date":date,"source_sha256":sha,
                            "table1_status":"ABSENT","table2_status":"ABSENT",
                            "provinces_examined":0,"status":report_status})
            continue
        j=json.loads(snapshot.read_text(encoding="utf-8"))
        if j.get("source_sha256")!=sha:raise ValueError(f"Snapshot source mismatch {number}")
        t1=j.get("tables",{}).get("table_1") or {}
        t2=j.get("tables",{}).get("table_2") or {}
        by_t1={r["scope"]:r for r in t1.get("rows",[]) if r.get("scope") and r.get("scope")!="DRC"}
        by_t2={r["province"]:r for r in t2.get("province_totals",[]) if r.get("province")}
        by_zone=defaultdict(list)
        for zone in t2.get("rows",[]):
            if zone.get("province") and zone.get("scope")=="health_zone":
                by_zone[zone["province"]].append(zone)
        provinces=sorted(set(by_t1)|set(by_t2)|set(by_zone))
        statuses=set()
        for province in provinces:
            p1=by_t1.get(province);p2=by_t2.get(province)
            zones=by_zone.get(province,[])
            for metric in FIELDS:
                v1=p1.get(metric) if p1 else None
                v2=p2.get(metric) if p2 else None
                complete=all(type(z.get(metric)) is int for z in zones)
                sum_z=sum(z[metric] for z in zones) if zones and complete else None
                if type(v1) is int and type(v2) is int:
                    status="REPORTED_PROVINCE_TOTALS_MATCH" if v1==v2 else "REPORTED_PROVINCE_TOTALS_DIFFER"
                elif v1 is None and v2 is None:
                    status="NO_REPORTED_PROVINCE_TOTAL_EXTRACTED"
                else:status="ONLY_ONE_PROVINCIAL_SOURCE_EXTRACTED"
                statuses.add(status)
                counts[status]+=1
                details.append({"report_number":number,"date":date,"source_sha256":sha,
                  "province":province,"metric_id":metric,
                  "table1_reported_value":v1,"table2_reported_value":v2,
                  "sum_of_extracted_zones_NOT_PROVINCE_TOTAL":sum_z,
                  "extracted_zone_row_count":len(zones),
                  "table1_page":(p1 or {}).get("source",{}).get("page"),
                  "table2_page":(p2 or {}).get("source",{}).get("page"),
                  "table1_status":t1.get("status","ABSENT"),
                  "table2_status":t2.get("status","ABSENT"),
                  "status":status,"approved_for_analysis":False})
        if not provinces:report_status="NO_EXTRACTABLE_PROVINCIAL_ROWS"
        elif "REPORTED_PROVINCE_TOTALS_DIFFER" in statuses:report_status="PROVINCIAL_TOTAL_DISAGREEMENT"
        elif "NO_REPORTED_PROVINCE_TOTAL_EXTRACTED" in statuses or "ONLY_ONE_PROVINCIAL_SOURCE_EXTRACTED" in statuses:
            report_status="INCOMPLETE_PROVINCIAL_CROSSCHECK"
        else:report_status="PROVINCE_TOTALS_MATCH_REVIEW_REQUIRED"
        counts["reports_"+report_status]+=1
        reports.append({"report_number":number,"report_date":date,"source_sha256":sha,
            "table1_status":t1.get("status","ABSENT"),"table2_status":t2.get("status","ABSENT"),
            "provinces_examined":len(provinces),"status":report_status})
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    for filename,rows in (("provincial_cells_review.csv",details),("provincial_report_coverage.csv",reports)):
        with (output/filename).open("w",newline="",encoding="utf-8") as f:
            if rows:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]))
                writer.writeheader();writer.writerows(rows)
    summary={"schema_version":"bdbv-historical-provincial-audit-v1",
       "status":"SOURCE_LINKED_PROVINCIAL_REVIEW_ONLY",
       "reports_evaluated":len(reports),"provincial_metric_candidates_evaluated":len(details),
       "counts":dict(counts),
       "warning":"Matching PDF-derived table totals alone is not a human-fidelity certificate. Incomplete province/zone coverage and ND must never be converted to zero."}
    (output/"provincial_audit_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--registry",type=Path,default=Path("state/registry.json"))
    p.add_argument("--published",type=Path,default=Path("published"))
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    audit(a.registry,a.published,a.out)
