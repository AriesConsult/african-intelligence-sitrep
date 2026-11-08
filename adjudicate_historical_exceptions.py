#!/usr/bin/env python3
"""Conservative resolution register for BDBV source discrepancies.

Reduces broad exception counts into explicit, evidence-backed states:
  * a verified original SitRep 169 cell is a *resolved transcription dispute*,
    NOT proof that INRB's retrospective epidemiological vintage is wrong;
  * duplicate PDF rows with the same numeric value are numerically consistent
    but still structurally ambiguous;
  * negative cumulative differences are classified as temporal revisions
    or anomalies, never interpreted as negative incidence.

No imported source observation is auto-approved for public analysis.
"""
from __future__ import annotations
import argparse,csv,gzip,json
from collections import Counter,defaultdict
from pathlib import Path
from datetime import date

SITREP169_HASH="8e2cd47248423d71341536e26671abfeb08364094334d2cee548dcb457532fa5"
SITREP169_ADJUDICATED={
    ("Nyankunde","cumulative_confirmed_cases"):154,
    ("Nyankunde","cumulative_confirmed_deaths"):57,
    ("Rimba","cumulative_confirmed_deaths"):12,
    ("Rwampara","cumulative_confirmed_cases"):1267,
    ("Tchomia","cumulative_confirmed_cases"):87,
    ("Tchomia","cumulative_confirmed_deaths"):36,
    ("Mutwanga","cumulative_confirmed_deaths"):14,
}
ALIGNED_NATIONAL_169={"national_cumulative_confirmed_deaths":5372}
def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as f:
        for s in f:
            if s.strip():yield json.loads(s)

def read_csv(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        yield from csv.DictReader(f)

def val(v):
    try:return int(str(v).replace(",","").strip())
    except (TypeError,ValueError):return None

def resolve(revisions,zone_ledger,national_csv,triage,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    priority=[];counts=Counter()
    z=list(read_jsonl(zone_ledger))
    by_zone={(r["date"],r["metric_id"],r["geography"],str(r.get("pdf_report") or "")):r
             for r in z if r.get("pdf_report")}
    for r in read_jsonl(zone_ledger):
        status=r["status"]
        if status not in ("DIFFERENCE_REQUIRES_SOURCE_PAGE_REVIEW","AMBIGUOUS_MULTIPLE_PDF_ROWS"):
            continue
        actual=val(r.get("pdf_value"));expected=SITREP169_ADJUDICATED.get((r["geography"],r["metric_id"]))
        is169=(r.get("pdf_report")==169 and r.get("pdf_sha256")==SITREP169_HASH)
        if is169 and expected is not None and actual==expected:
            disposition="PRIMARY_PDF_169_CELL_TRANSCRIPTION_RESOLVED"
            evidence="docs/SITREP169_SOURCE_ADJUDICATION.md"
        elif status=="AMBIGUOUS_MULTIPLE_PDF_ROWS":
            disposition="DUPLICATE_PDF_ROW_AMBIGUITY_UNRESOLVED"
            evidence=""
        else:
            disposition="NUMERICAL_SOURCE_DIFFERENCE_UNRESOLVED"
            evidence=""
        counts[disposition]+=1
        priority.append({"category":"HEALTH_ZONE","date":r["date"],"metric":r["metric_id"],
         "geography":r["geography"],"report_number":r.get("pdf_report"),
         "source_pdf_sha256":r.get("pdf_sha256"),
         "pdf_page":r.get("pdf_page"),"curated_INRB_value":r.get("inrb_value_raw"),
         "original_pdf_candidate":r.get("pdf_value"),
         "verified_pdf_value":expected if is169 and expected==actual else "",
         "machine_pdf_reading_agrees_with_verified_value":expected==actual if is169 and expected is not None else "",
         "disposition":disposition,"evidence_document":evidence,
         "epidemiological_revision_explained":False,"approved_for_analysis":False})
    for r in read_csv(national_csv):
        if r["outcome"] not in ("DIFFERENCE_REVIEW_REQUIRED","POSSIBLE_REPORTING_DATE_ALIGNMENT_REVIEW_REQUIRED","AMBIGUOUS_PDF_BANNER_CANDIDATE","NO_PDF_BANNER_CANDIDATE"):
            continue
        number=val(r["report_number"])
        expected=ALIGNED_NATIONAL_169.get(r["metric_id"])
        is169=(number==169 and r["source_pdf_sha256"]==SITREP169_HASH)
        if is169 and expected is not None:
            disposition="PRIMARY_PDF_169_NATIONAL_REVISION_EXPLAINED"
            evidence="docs/SITREP169_SOURCE_ADJUDICATION.md"
            explained=True
        else:
            disposition="NATIONAL_BANNER_OR_DATE_REVIEW_REQUIRED"
            evidence="";explained=False
        counts[disposition]+=1
        priority.append({"category":"NATIONAL","date":r["report_date"],"metric":r["metric_id"],
         "geography":"DRC","report_number":number,
         "source_pdf_sha256":r["source_pdf_sha256"],"pdf_page":r.get("pdf_page"),
         "curated_INRB_value":r["inrb_value"],"original_pdf_candidate":r["pdf_value_candidate"],
         "verified_pdf_value":expected if is169 else "",
         "machine_pdf_reading_agrees_with_verified_value":val(r["pdf_value_candidate"])==expected if is169 else "",
         "disposition":disposition,"evidence_document":evidence,
         "epidemiological_revision_explained":explained,"approved_for_analysis":False})
    for r in read_csv(revisions):
        delta=val(r["delta"])
        if delta is None or delta>=0:raise ValueError("Revision flag must be downward cumulative")
        try:
            gap=(date.fromisoformat(r["current_date"])-date.fromisoformat(r["previous_date"])).days
        except ValueError:gap=None
        if gap is None or gap<1:disposition="INVALID_OR_NONCHRONOLOGICAL_DATE_REVIEW_REQUIRED"
        elif gap>1:disposition="CUMULATIVE_DROP_ACROSS_REPORTING_GAP_REVIEW_REQUIRED"
        else:disposition="CUMULATIVE_DROP_BETWEEN_CONSECUTIVE_DATES_REVIEW_REQUIRED"
        counts[disposition]+=1
        priority.append({"category":"CUMULATIVE_REVISION","date":r["current_date"],"metric":r["metric_id"],
          "geography":r["geography_raw"],"report_number":"",
          "source_pdf_sha256":"","pdf_page":"",
          "curated_INRB_value":r["current_value"],"original_pdf_candidate":"",
          "previous_date":r["previous_date"],"previous_value":r["previous_value"],
          "delta":delta,"reporting_gap_days":gap,
          "disposition":disposition,"evidence_document":"",
          "epidemiological_revision_explained":False,"approved_for_analysis":False})
    # Triage offsets are *hypotheses*, not verified reporting-date corrections.
    shifts=list(read_csv(triage))
    shift_counts=Counter(r.get("diagnosis") for r in shifts)
    fields=["category","date","metric","geography","report_number","source_pdf_sha256",
      "pdf_page","curated_INRB_value","original_pdf_candidate","verified_pdf_value",
      "machine_pdf_reading_agrees_with_verified_value","previous_date","previous_value","delta",
      "reporting_gap_days","disposition","evidence_document",
      "epidemiological_revision_explained","approved_for_analysis"]
    with (out/"historical_exception_decision_register.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        writer.writeheader();writer.writerows(priority)
    result={"schema_version":"bdbv-historical-exception-decision-v1",
      "status":"SITREP169_REPORTED_CELL_DISPUTES_DOCUMENTED_OTHERS_REVIEW_PENDING",
      "records":len(priority),"decisions_by_type":dict(counts),
      "date_neighbourhood_diagnostic_counts":dict(shift_counts),
      "resolved_original_pdf_169_cells":counts["PRIMARY_PDF_169_CELL_TRANSCRIPTION_RESOLVED"],
      "resolved_169_national_revision":counts["PRIMARY_PDF_169_NATIONAL_REVISION_EXPLAINED"],
      "approved_for_research_grade":0,
      "constraints":["SitRep 169 values validated against visually reviewed original-page note; all other PDF values remain candidate readings.",
        "Resolution of PDF-versus-INRB transcription is not resolution of why each upstream historical vintage differs.",
        "Do not replace INRB reported values with newer cumulative totals or infer daily incidence.",
        "Adjacent-date matches are merely candidate explanations; retain actual report dates.",
        "Duplicate-row ambiguity requires layout and original cell identity review."]}
    (out/"historical_exception_decision_summary.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--revisions",type=Path,required=True)
    p.add_argument("--zone-ledger",type=Path,required=True)
    p.add_argument("--national-csv",type=Path,required=True)
    p.add_argument("--zone-triage",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();resolve(a.revisions,a.zone_ledger,a.national_csv,a.zone_triage,a.out)
