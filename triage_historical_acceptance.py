#!/usr/bin/env python3
"""Adjudication triage of actual historic revisions and duplicate zone matches.

This is a source-controlled decision ledger, not an auto-certification engine.
Positive determinations require direct primary-source evidence in a
separately versioned/manual adjudication record.
"""
from __future__ import annotations
import argparse,csv,json,re
from collections import Counter,defaultdict
from pathlib import Path

def load_jsonl(path):
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():yield json.loads(line)

def audit_revisions(revisions,out):
    rows=list(csv.DictReader(open(revisions,encoding="utf-8-sig",newline="")))
    classes=Counter();result=[]
    for row in rows:
        prev=int(row["previous_value"]);cur=int(row["current_value"])
        if cur>=prev:raise ValueError("Revision file includes nondecrease")
        delta=cur-prev
        # Describe the observed change, never assert a causal reason.
        classification="NEGATIVE_CURATED_CUMULATIVE_STEP_OR_RECALCULATION_UNEXPLAINED"
        if cur==0 and prev>0:classification="CUMULATIVE_SERIES_RESET_OR_DEFINITION_CHANGE_REVIEW"
        result.append({**row,"verified_previous":prev,"verified_current":cur,
            "calculated_delta":delta,"triage":classification,
            "requires_report_page_or_revision_note":True,
            "does_not_imply_negative_incidence":True,"adjudication":"UNRESOLVED"})
        classes[classification]+=1
    with (out/"cumulative_revision_adjudication.csv").open("w",encoding="utf-8",newline="") as f:
        cols=list(result[0]) if result else ["triage"]
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(result)
    return {"cases":len(rows),"classes":dict(classes)}

def audit_ambiguous(zoneledger,registry,published,out):
    reg=json.loads(Path(registry).read_text(encoding="utf-8"))
    files={}
    for record in reg["documents"].values():
        n,h=record["report_number"],record["sha256"]
        p=Path(published)/"tables"/f"{n:03d}_{h[:12]}.json"
        if p.is_file():files[(n,record["report_date"])]=p
    groups=defaultdict(list)
    for row in load_jsonl(zoneledger):
        if row["status"]=="AMBIGUOUS_MULTIPLE_PDF_ROWS":
            groups[(row["date"],row["metric_id"],row["geography"])].append(row)
    counts=Counter();answers=[]
    for (day,metric,name),upstream in sorted(groups.items()):
        # Reconstruct all source candidates that share the same source-derived
        # geography label. A same numeric value is NOT used to choose a row.
        matches=[]
        field="cumulative_cases" if metric=="cumulative_confirmed_cases" else "cumulative_deaths"
        for (number,report_date),p in files.items():
            if report_date!=day:continue
            doc=json.loads(p.read_text(encoding="utf-8"))
            rows=(doc.get("tables",{}).get("table_2") or {}).get("rows",[])
            for r in rows:
                if r.get("health_zone","").strip().casefold()!=name.strip().casefold():continue
                value=r.get(field)
                if type(value) is not int:continue
                src=r.get("source") or {}
                matches.append({"report_number":number,"pdf_sha256":doc["source_sha256"],
                    "province":r.get("province"),"value":value,
                    "page":src.get("page"),"table":src.get("table_id"),
                    "row":src.get("source_row")})
        unique={(m["pdf_sha256"],m["page"],m["table"],m["row"],m["value"],m["province"]) for m in matches}
        if len(unique)==1:
            klass="IDENTICAL_EXTRACTED_PDF_CELL_DUPLICATED_IN_COMPARISON"
        elif len({(m["pdf_sha256"],m["province"]) for m in matches})==1 and len({m["value"] for m in matches})==1:
            klass="EQUAL_VALUES_MULTIPLE_PDF_ROWS_REQUIRE_LAYOUT_REVIEW"
        elif len({m["value"] for m in matches})>1:
            klass="CONFLICTING_PDF_ROW_VALUES_REQUIRE_VISUAL_REVIEW"
        elif not matches:
            klass="NO_PDF_ROW_RECONSTRUCTED"
        else:
            klass="MULTIPLE_SOURCE_ROWS_UNRESOLVED"
        counts[klass]+=len(upstream)
        answers.append({"report_date":day,"metric":metric,"health_zone_raw":name,
            "upstream_row_occurrences":len(upstream),"pdf_candidates":matches,
            "distinct_pdf_cell_keys":len(unique),"classification":klass,
            "selected_pdf_value":matches[0]["value"] if klass=="IDENTICAL_EXTRACTED_PDF_CELL_DUPLICATED_IN_COMPARISON" else None,
            "approved_for_analysis":False,
            "requires_visual_review":klass!="IDENTICAL_EXTRACTED_PDF_CELL_DUPLICATED_IN_COMPARISON"})
    with (out/"ambiguous_healthzone_source_rows.jsonl").open("w",encoding="utf-8") as f:
        for row in answers:f.write(json.dumps(row,ensure_ascii=False)+"\n")
    return {"ambiguous_inrb_rows":sum(x["upstream_row_occurrences"] for x in answers),
            "unique_geo_date_metric_groups":len(answers),"classification_counts":dict(counts)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--revisions",type=Path,required=True)
    p.add_argument("--zones",type=Path,required=True)
    p.add_argument("--registry",type=Path,default=Path("state/registry.json"))
    p.add_argument("--published",type=Path,default=Path("published"))
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    rev=audit_revisions(a.revisions,a.out)
    ambiguity=audit_ambiguous(a.zones,a.registry,a.published,a.out)
    summary={"schema_version":"bdbv-historical-exception-adjudication-v1",
        "status":"TRIAGED_NOT_FULLY_ADJUDICATED",
        "cumulative_decreases":rev,"healthzone_ambiguity":ambiguity,
        "accepted_value_changes":0,
        "research_controls":[
          "An equal numerical value from multiple extracted rows cannot establish which PDF cell was reported.",
          "Cumulative declines may represent correction, geographic change, changing definitions, or error; never infer negative incident counts.",
          "Only direct original-source proof can close scientific approval.",
          "All rows remain unapproved until separate documented visual adjudication."
        ]}
    (a.out/"historical_exception_adjudication_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
