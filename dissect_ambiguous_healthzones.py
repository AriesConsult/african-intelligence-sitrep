#!/usr/bin/env python3
"""Dissect ambiguous health-zone matches into their original PDF source rows.

Allows deterministic deduplication only where all original row identities are
identical. Distinct source rows or provinces remain ambiguous even when their
values coincide. Nothing is auto-published.
"""
import argparse,csv,json
from pathlib import Path
from collections import Counter,defaultdict
from reconcile_healthzones import load_pdf_candidates,normalize

def inspect(registry_path,published,zone_ledger,out):
    candidates,source_stats=load_pdf_candidates(registry_path,published)
    rows=[];counter=Counter()
    with Path(zone_ledger).open(encoding="utf-8") as f:
        for line in f:
            row=json.loads(line)
            if row.get("status")!="AMBIGUOUS_MULTIPLE_PDF_ROWS":continue
            key=(row["date"],row["metric_id"],normalize(row["geography"]),"health_zone")
            matching=candidates.get(key,[])
            if len(matching)<2:raise ValueError("Ambiguous classification without multiple original PDF rows")
            entries=[]
            for c in matching:
                entries.append({
                    "value":c["pdf_value"],"report_number":c["report_number"],"pdf_sha256":c["pdf_sha256"],
                    "page":c["pdf_page"],"table_id":c["pdf_table_id"],"source_row":c["pdf_source_row"],
                    "province":c.get("province_pdf_raw"),
                    "machine_table_status":c["pdf_table_status"]})
            ids={(x["report_number"],x["pdf_sha256"],x["page"],x["table_id"],
                  x["source_row"],x["province"]) for x in entries}
            provinces={x["province"] for x in entries}
            values={x["value"] for x in entries}
            if len(ids)==1 and len(values)==1:
                diagnosis="EXACT_SOURCE_CELL_REPEATED_IN_PARSER"
            elif len(provinces)>1:
                diagnosis="SAME_ZONE_NAME_MULTIPLE_PROVINCES_CANNOT_DISAMBIGUATE"
            elif len(values)==1:
                diagnosis="SAME_NUMERIC_VALUE_DISTINCT_SOURCE_ROWS"
            else:
                diagnosis="DIFFERING_PDF_VALUES_FOR_SAME_ZONE_NAME"
            counter[diagnosis]+=1
            rows.append({"date":row["date"],"metric_id":row["metric_id"],
                "geography":row["geography"],"inrb_value_raw":row["inrb_value_raw"],
                "candidate_rows":entries,"distinct_cells":len(ids),"distinct_values":len(values),
                "diagnosis":diagnosis,
                "numerical_agreement_any_pdf_candidate":row.get("inrb_value_parsed") in values,
                "approved_for_analysis":False})
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with (out/"ambiguous_healthzone_pdf_rows.jsonl").open("w",encoding="utf-8") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False)+"\n")
    summary={"schema_version":"bdbv-ambiguous-zone-row-dissection-v1",
        "ambiguous_rows_examined":len(rows),
        "classifications":dict(counter),
        "status":"STRUCTURAL_SOURCE_ROW_AMBIGUITIES_CLASSIFIED_NOT_ALL_RESOLVED",
        "constraints":["Numeric equality never proves source-row identity.",
          "Distinct original PDF rows cannot be merged without source-page review.",
          "A repeated exact parser cell may be deduplicated as candidate evidence, not as validated outbreak data.",
          "No source observations approved or overwritten."]}
    (out/"ambiguous_healthzone_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2));return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--registry",type=Path,default=Path("state/registry.json"))
    p.add_argument("--published",type=Path,default=Path("published"))
    p.add_argument("--zone-ledger",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();inspect(a.registry,a.published,a.zone_ledger,a.out)
