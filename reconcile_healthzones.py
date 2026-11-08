#!/usr/bin/env python3
"""Review-only INRB / PDF Table II health-zone and province reconciliation.

Matches explicit PDF Table II row candidates with pinned INRB CSV candidates.
Never imports upstream values into the approved feed or imputes absent cells.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

PDF_METRICS={"cumulative_confirmed_cases":"cumulative_cases",
             "cumulative_confirmed_deaths":"cumulative_deaths"}
IGNORE_NAMES={"", "na", "sans fiche", "drc", "total", "total general"}

def normalize(name):
    text="".join(x for x in unicodedata.normalize("NFKD",str(name or "").lower())
                 if not unicodedata.combining(x))
    return re.sub(r"\s+"," ",text.replace("’","'").replace("‐","-").replace("–","-")).strip()

def load_pdf_candidates(registry_path, published):
    registry=json.loads(Path(registry_path).read_text(encoding="utf-8"))
    out=defaultdict(list)
    counters=Counter()
    for record in registry["documents"].values():
        no,sha=record["report_number"],record["sha256"]
        path=Path(published)/"tables"/f"{no:03d}_{sha[:12]}.json"
        if not path.exists():
            counters["missing_pdf_table_snapshot"]+=1
            continue
        document=json.loads(path.read_text(encoding="utf-8"))
        if document.get("source_sha256")!=sha or document.get("report_number")!=no:
            raise ValueError(f"PDF table snapshot identity mismatch for SitRep {no}")
        table=document.get("tables",{}).get("table_2")
        if not table:
            counters["no_parsed_table2"]+=1
            continue
        table_status=table.get("status","REVIEW_REQUIRED")
        if table_status!="MACHINE_VALIDATED":
            counters["table2_unvalidated_documents"]+=1
        for geographic_grain,items in (("health_zone",table.get("rows",[])),
                                       ("province",table.get("province_totals",[]))):
            for row in items:
                name=row.get("health_zone") if geographic_grain=="health_zone" else row.get("province")
                if not name or normalize(name) in IGNORE_NAMES:continue
                for upstream_metric,pdf_metric in PDF_METRICS.items():
                    value=row.get(pdf_metric)
                    if type(value) is not int:continue
                    result={"report_number":no,"report_date":record.get("report_date"),
                        "pdf_sha256":sha,"pdf_source_url":record.get("source_url"),
                        "metric_id":upstream_metric,"geographic_grain":geographic_grain,
                        "geography_pdf_raw":name,"province_pdf_raw":row.get("province"),
                        "pdf_value":value,"pdf_table_status":table_status,
                        "pdf_page":row.get("source",{}).get("page"),
                        "pdf_table_id":row.get("source",{}).get("table_id"),
                        "pdf_source_row":row.get("source",{}).get("source_row"),
                        "pdf_extraction_role":"POTENTIAL_DIRECT_PDF_TABLE_CELL_NOT_HUMAN_VERIFIED"}
                    key=(result["report_date"],upstream_metric,normalize(name),geographic_grain)
                    out[key].append(result)
                    counters["pdf_candidate_values"]+=1
    return out,counters

def reconcile(registry_path,published,staged_dir,output):
    stage=Path(staged_dir)
    summary=json.loads((stage/"inrb_staging_summary.json").read_text(encoding="utf-8"))
    commit=summary["inrb_commit"]
    pdf_by_key,pdf_count=load_pdf_candidates(registry_path,published)
    results=[]
    counts=Counter()
    seen_pdf_keys=set()
    with gzip.open(stage/"inrb_observation_candidates.jsonl.gz","rt",encoding="utf-8") as fp:
        for line in fp:
            upstream=json.loads(line)
            metric=upstream["metric_id"]
            if metric not in PDF_METRICS:continue
            name=upstream.get("geography_raw","")
            normalized=normalize(name)
            if normalized in IGNORE_NAMES:continue
            day=upstream.get("date_raw")
            if not upstream.get("date_valid"):
                counts["INRB_INVALID_DATE"]+=1
                results.append({"date":day,"metric_id":metric,"geography":name,
                    "status":"INRB_INVALID_DATE","pdf_value":None,
                    "inrb_value_raw":upstream.get("value_raw"),"inrb_row":upstream.get("inrb_csv_row_number"),
                    "inrb_commit":commit,"review_required":True})
                continue
            key=(day,metric,normalized,"health_zone")
            candidates=pdf_by_key.get(key,[])
            # Province-wide INRB files are not among the health-zone metric CSVs.
            # Do not match a namesake province or a province total to a health zone.
            seen_pdf_keys.add(key)
            pdf=None
            if len(candidates)==1:pdf=candidates[0]
            if len(candidates)>1:status="AMBIGUOUS_MULTIPLE_PDF_ROWS"
            elif not candidates:status="NO_DIRECT_PDF_TABLE2_CELL_FOR_DATE_AND_ZONE"
            elif upstream["value_status"]!="NUMERIC_UNVERIFIED":status="INRB_ND_OR_NONNUMERIC"
            elif pdf["pdf_value"]!=upstream["value_parsed"]:status="DIFFERENCE_REQUIRES_SOURCE_PAGE_REVIEW"
            elif pdf["pdf_table_status"]!="MACHINE_VALIDATED":status="MATCH_BUT_PDF_TABLE_NOT_VALIDATED"
            else:status="MATCH_WITH_MACHINE_VALIDATED_TABLE_REQUIRES_VISUAL_QA"
            counts[status]+=1
            result={"date":day,"metric_id":metric,"geography":name,"inrb_value_raw":upstream.get("value_raw"),
                "inrb_value_parsed":upstream.get("value_parsed"),"inrb_csv_path":upstream.get("inrb_csv_path"),
                "inrb_csv_row":upstream.get("inrb_csv_row_number"),"inrb_csv_sha256":upstream.get("inrb_csv_sha256"),
                "inrb_commit":commit,"pdf_value":pdf["pdf_value"] if pdf else None,
                "pdf_report":pdf["report_number"] if pdf else None,
                "pdf_sha256":pdf["pdf_sha256"] if pdf else None,
                "pdf_page":pdf["pdf_page"] if pdf else None,
                "pdf_table_id":pdf["pdf_table_id"] if pdf else None,
                "pdf_source_row":pdf["pdf_source_row"] if pdf else None,
                "pdf_table_status":pdf["pdf_table_status"] if pdf else None,
                "status":status,"review_required":True,"approved_for_analysis":False}
            results.append(result)
    # All PDF data without a corresponding INRB record remain visible.
    unmatched_pdf=[]
    for key,candidates in pdf_by_key.items():
        if key in seen_pdf_keys and key[-1]=="health_zone":continue
        for p in candidates:
            unmatched_pdf.append({"report_number":p["report_number"],"date":p["report_date"],
                "metric_id":p["metric_id"],"geography":p["geography_pdf_raw"],
                "grain":p["geographic_grain"],"value":p["pdf_value"],
                "pdf_sha256":p["pdf_sha256"],"pdf_page":p["pdf_page"],
                "pdf_table_id":p["pdf_table_id"],"pdf_source_row":p["pdf_source_row"],
                "status":"PDF_ONLY_OR_PROVINCE_GRAIN_NOT_IN_INRB_ZONE_CSV"})
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with (output/"healthzone_concordance.jsonl").open("w",encoding="utf-8") as stream:
        for record in results:stream.write(json.dumps(record,ensure_ascii=False)+"\n")
    with (output/"pdf_unmatched_candidates.jsonl").open("w",encoding="utf-8") as stream:
        for record in unmatched_pdf:stream.write(json.dumps(record,ensure_ascii=False)+"\n")
    review=[x for x in results if x["status"] in
           ("DIFFERENCE_REQUIRES_SOURCE_PAGE_REVIEW","AMBIGUOUS_MULTIPLE_PDF_ROWS","INRB_INVALID_DATE")]
    with (output/"review_priority.csv").open("w",newline="",encoding="utf-8") as fp:
        fields=["date","metric_id","geography","status","inrb_value_raw","pdf_value",
                "pdf_report","pdf_sha256","pdf_page","pdf_table_id","pdf_source_row","inrb_csv_path","inrb_csv_row"]
        writer=csv.DictWriter(fp,fieldnames=fields,extrasaction="ignore")
        writer.writeheader();writer.writerows(review)
    report={"schema_version":"bdbv-inrb-zone-concordance-v1",
        "status":"REVIEW_ONLY_NO_AUTOMATIC_APPROVAL",
        "inrb_commit":commit,"comparison_counts":dict(counts),
        "pdf_candidate_summary":dict(pdf_count),"pdf_unmatched_candidates":len(unmatched_pdf),
        "matched_same_value_unapproved":counts["MATCH_BUT_PDF_TABLE_NOT_VALIDATED"]+
           counts["MATCH_WITH_MACHINE_VALIDATED_TABLE_REQUIRES_VISUAL_QA"],
        "explicit_source_disagreements":counts["DIFFERENCE_REQUIRES_SOURCE_PAGE_REVIEW"],
        "review_priority_rows":len(review),"records_evaluated":len(results),
        "limitations":[
            "Exact accent-insensitive geographic-name matching only; no unreviewed aliases.",
            "INRB source values may be carried forward or derived; equality does not prove identical provenance.",
            "Only direct PDF table_2 cumulative cases/deaths candidates compared; other metrics are not certified.",
            "No automatic approval or modification of public analytics feeds."]}
    (output/"healthzone_reconciliation_summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--registry",type=Path,default=Path("state/registry.json"))
    parser.add_argument("--published",type=Path,default=Path("published"))
    parser.add_argument("--staged-dir",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    reconcile(args.registry,args.published,args.staged_dir,args.out)
