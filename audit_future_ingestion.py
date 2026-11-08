#!/usr/bin/env python3
"""Daily change-control audit against the frozen historical SitRep source set.

Never promotes a newly discovered PDF, changed historical PDF or narrative
candidate without independent full-page and provenance review.
"""
import argparse,json
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone,date

def audit(freeze_path,registry_path,table_index_path,narrative_index_path,scanned_path,out):
    frozen=json.loads(Path(freeze_path).read_text(encoding="utf-8"))
    registry=json.loads(Path(registry_path).read_text(encoding="utf-8"))
    tables=json.loads(Path(table_index_path).read_text(encoding="utf-8"))
    narratives=json.loads(Path(narrative_index_path).read_text(encoding="utf-8"))
    scanned=json.loads(Path(scanned_path).read_text(encoding="utf-8"))
    originals={(x["report_number"],x["sha256"]) for x in frozen["registered_source_hashes"]}
    current={(x["report_number"],x["sha256"]) for x in registry["documents"].values()}
    if not originals.issubset(current):
        missing=sorted(originals-current)
        raise ValueError("Previously frozen historical source identity missing: "+repr(missing[:8]))
    scanned_nums={x["report_number"] for x in scanned["source_records"]}
    table_keys={(r["report_number"],r["sha256"]) for r in tables["reports"]}
    narrative_keys={(r["report_number"],r["source_sha256"]) for r in narratives["reports"]}
    baseline_by_number={}
    for num,sha in originals:baseline_by_number.setdefault(num,set()).add(sha)
    changes=[]
    for num,sha in sorted(current-originals):
        source=next(x for x in registry["documents"].values() if x["report_number"]==num and x["sha256"]==sha)
        status="REVISED_EXISTING_REPORT" if num in baseline_by_number else "NEW_SOURCE_REPORT"
        try:date.fromisoformat(source["report_date"])
        except (TypeError,ValueError):status="INVALID_REPORTING_DATE"
        changes.append({"report_number":num,"report_date":source.get("report_date"),
            "source_pdf_sha256":sha,"source_url":source.get("source_url"),
            "source_status":status,
            "table_snapshot_available":(num,sha) in table_keys,
            "narrative_snapshot_available":(num,sha) in narrative_keys,
            "full_page_source_fidelity_review_completed":False,
            "numerical_revision_reconciled":False,
            "approved_in_historical_freeze":False})
    summary={"schema_version":"bdbv-future-sitrep-change-control-v1",
       "timestamp_utc":datetime.now(timezone.utc).isoformat(),
       "historical_frozen_documents":len(originals),
       "historical_scanned_pending_full_transcription":sorted(scanned_nums),
       "current_documents":len(current),
       "new_or_revised_source_hashes":len(changes),
       "status":"REVIEW_NEW_SOURCE_REVISIONS" if changes else "NO_NEW_SOURCE_HASHES_SINCE_HISTORICAL_FREEZE",
       "changes":changes,
       "warning":"No automatic historical corrections, new-source approval or narrative completeness certification; source number gaps are not missing publications."}
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/"future_ingestion_change_control.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="changes"},indent=2))
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--freeze",type=Path,default=Path("state/historical_source_freeze_20261108.json"))
    p.add_argument("--registry",type=Path,default=Path("state/registry.json"))
    p.add_argument("--tables",type=Path,default=Path("published/table_index.json"))
    p.add_argument("--narratives",type=Path,default=Path("published/narrative_index.json"))
    p.add_argument("--scanned",type=Path,default=Path("published/scanned_source_index.json"))
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    audit(a.freeze,a.registry,a.tables,a.narratives,a.scanned,a.out)
