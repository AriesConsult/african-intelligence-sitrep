#!/usr/bin/env python3
"""Publish a strictly bounded primary-PDF *transcription* verification ledger.

A verified PDF reading is not the same as a verified epidemiological event,
an estimate corrected retrospectively, or an approved time-series observation.
Only pre-existing source-page visual review records are admissible here.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from collections import Counter

VERIFIED_169_ZONES={
 ("Nyankunde","cumulative_confirmed_cases"):154,
 ("Nyankunde","cumulative_confirmed_deaths"):57,
 ("Rimba","cumulative_confirmed_deaths"):12,
 ("Rwampara","cumulative_confirmed_cases"):1267,
 ("Tchomia","cumulative_confirmed_cases"):87,
 ("Tchomia","cumulative_confirmed_deaths"):36,
 ("Mutwanga","cumulative_confirmed_deaths"):14
}
SOURCE_169="8e2cd47248423d71341536e26671abfeb08364094334d2cee548dcb457532fa5"

def verify(cover,registry_path,table169,out):
    cover=json.loads(Path(cover).read_text(encoding="utf-8"))
    reg=json.loads(Path(registry_path).read_text(encoding="utf-8"))
    tab=json.loads(Path(table169).read_text(encoding="utf-8"))
    by_no={r["report_number"]:r for r in reg["documents"].values()}
    rows=[]
    for report in cover["evidence"]:
        no=report["report_number"];source=by_no.get(no)
        if not source or source["sha256"]!=report["registry_sha256"]:
            raise ValueError("Cover reading original PDF identity mismatch")
        for metric,d in report["metrics"].items():
            val=d["preferred_verbatim_pdf"]
            if type(val) is not int:raise ValueError("Noninteger verified reading")
            other=d.get("other_printed_values",[])
            rows.append({"report_number":no,"report_date":source["report_date"],
              "source_pdf_sha256":source["sha256"],"source_url":source.get("source_url"),
              "geography":"DRC","geographic_grain":"national",
              "metric_id":metric,"verbatim_source_value":val,
              "source_page":1,"visual_reference":"; ".join(d.get("locations",[])),
              "source_conflicts_json":json.dumps(other,ensure_ascii=False),
              "source_revision_note":d.get("issue",report.get("note","")),
              "adjudication_basis":"state/verified_original_cover_readings_20261108.json",
              "verbatim_transcription_verified":True,
              "epidemiological_value_independently_validated":False,
              "approved_as_final_historical_incidence":False})
    if tab.get("source_sha256")!=SOURCE_169 or by_no[169]["sha256"]!=SOURCE_169:
        raise ValueError("SitRep169 reference source identity mismatch")
    observed={}
    for item in tab["tables"]["table_2"]["rows"]:
        for metric,field in (("cumulative_confirmed_cases","cumulative_cases"),
                             ("cumulative_confirmed_deaths","cumulative_deaths")):
            key=(item.get("health_zone"),metric)
            if key in VERIFIED_169_ZONES and type(item.get(field)) is int:
                observed.setdefault(key,[]).append((item[field],item.get("source",{})))
    for (zone,metric),value in VERIFIED_169_ZONES.items():
        vals=observed.get((zone,metric),[])
        if not vals or all(v!=value for v,_ in vals):
            raise ValueError("SitRep169 PDF-derived source row differs from visually adjudicated value")
        matching=[src for v,src in vals if v==value]
        if len(matching)!=1:raise ValueError("Ambiguous visually reviewed row identity")
        src=matching[0]
        rows.append({"report_number":169,"report_date":by_no[169]["report_date"],
          "source_pdf_sha256":SOURCE_169,"source_url":by_no[169].get("source_url"),
          "geography":zone,"geographic_grain":"health_zone",
          "metric_id":metric,"verbatim_source_value":value,
          "source_page":src.get("page"),"visual_reference":f"Table II {src.get('table_id')} row {src.get('source_row')}",
          "source_conflicts_json":"[]",
          "source_revision_note":"Retrospective Ituri revision context; do not infer which earlier incidence dates changed.",
          "adjudication_basis":"docs/SITREP169_SOURCE_ADJUDICATION.md",
          "verbatim_transcription_verified":True,
          "epidemiological_value_independently_validated":False,
          "approved_as_final_historical_incidence":False})
    if len(rows)!=17:raise ValueError("Unexpected number of individually reviewed PDF observations")
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with (out/"verified_primary_pdf_verbatim_readings.csv").open("w",newline="",encoding="utf-8") as fp:
        writer=csv.DictWriter(fp,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary={"schema_version":"bdbv-primary-pdf-verbatim-verification-v1",
      "status":"LIMITED_VERBATIM_SOURCE_READINGS_VERIFIED_NOT_FULL_DATASET",
      "verified_verbatim_records":len(rows),
      "verified_national_records":10,"verified_healthzone_records":7,
      "verified_report_numbers":sorted({r["report_number"] for r in rows}),
      "source_registry_only":True,
      "approved_as_final_historical_incidence":0,
      "constraints":["Verifies only readings in existing explicitly recorded visual-review evidence.",
        "A table/cover discrepancy such as 9065 versus 9066 remains explicitly documented.",
        "Curated INRB values and revision snapshots are never overwritten.",
        "No unreviewed figure is promoted to source-verified."]}
    (out/"verified_pdf_readings_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--cover",type=Path,default=Path("state/verified_original_cover_readings_20261108.json"))
    p.add_argument("--registry",type=Path,default=Path("state/registry.json"))
    p.add_argument("--table169",type=Path,default=Path("published/tables/169_8e2cd4724842.json"))
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();verify(a.cover,a.registry,a.table169,a.out)
