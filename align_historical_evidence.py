#!/usr/bin/env python3
"""Merge frozen INRB historic candidate series with ORIGINAL PDF concordance.

Every value retains its unmodified INRB vintage; PDF evidence is separate.
Same-source agreement ≠ independently verified outbreak incidence.
"""
import argparse,csv,gzip,json,unicodedata,re
from pathlib import Path
from collections import Counter,defaultdict

def norm(s):
    return re.sub(r"\s+"," ","".join(x for x in unicodedata.normalize("NFKD",str(s or "").lower()) if not unicodedata.combining(x))).strip()

def build(history,zone_ledger,national_csv,output):
    h=Path(history);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    summary=json.loads((h/"historical_assembly_summary.json").read_text(encoding="utf-8"))
    zones=defaultdict(list)
    with Path(zone_ledger).open(encoding="utf-8") as fp:
        for line in fp:
            a=json.loads(line)
            if a.get("inrb_commit")!=summary["inrb_commit"]:raise ValueError("Cross-vintage zone ledger")
            key=(a["date"],a["metric_id"],norm(a["geography"]),a.get("inrb_csv_path"),a.get("inrb_csv_row"))
            zones[key].append(a)
    nationals=defaultdict(list)
    with Path(national_csv).open(encoding="utf-8-sig",newline="") as fp:
        for row in csv.DictReader(fp):
            if row["inrb_commit"]!=summary["inrb_commit"]:raise ValueError("Cross-vintage national ledger")
            nationals[(row["report_date"],row["metric_id"])].append(row)
    counts=Counter()
    with gzip.open(h/"historical_curated_candidates.jsonl.gz","rt",encoding="utf-8") as src,gzip.open(output/"historical_evidence_aligned.jsonl.gz","wt",encoding="utf-8") as dest:
        for line in src:
            item=json.loads(line)
            if item["inrb_commit"]!=summary["inrb_commit"]:raise ValueError("Historical candidate commit mismatch")
            metric=item["metric_id"]
            evidence=[]
            if metric in ("cumulative_confirmed_cases","cumulative_confirmed_deaths"):
                for rec in item["source_records"]:
                    key=(item["date"],metric,norm(item["geography_raw"]),rec["inrb_csv_path"],rec["inrb_csv_row_number"])
                    evidence.extend(zones.get(key,[]))
            elif metric in ("national_cumulative_confirmed_cases","national_cumulative_confirmed_deaths") and item["geography_raw"]=="DRC":
                evidence.extend(nationals.get((item["date"],metric),[]))
            outcomes={r.get("status",r.get("outcome")) for r in evidence}
            if item["status"]!="SINGLE_SOURCE_NUMERIC_CANDIDATE":
                rating=item["status"]
            elif len(evidence)>1 and len(outcomes)>1:
                rating="AMBIGUOUS_MULTIPLE_CONCORDANCE_RECORDS"
            elif any(x in outcomes for x in ("DIFFERENCE_REQUIRES_SOURCE_PAGE_REVIEW","DIFFERENCE_REVIEW_REQUIRED","POSSIBLE_REPORTING_DATE_ALIGNMENT_REVIEW_REQUIRED")):
                rating="PDF_INRB_DIFFERENCE_PENDING_ADJUDICATION"
            elif "MATCH_WITH_MACHINE_VALIDATED_TABLE_REQUIRES_VISUAL_QA" in outcomes:
                rating="PDF_MACHINE_VALIDATED_CONCORDANCE_VISUAL_QA_PENDING"
            elif "MATCH_BUT_PDF_TABLE_NOT_VALIDATED" in outcomes or "AGREES_WITH_INRB_PENDING_SOURCE_VISUAL_QA" in outcomes:
                rating="PDF_CANDIDATE_CONCORDANCE_REVIEW_PENDING"
            elif "AMBIGUOUS_MULTIPLE_PDF_ROWS" in outcomes:
                rating="AMBIGUOUS_PDF_ROW_MATCH"
            elif evidence:rating="PDF_EVIDENCE_UNRESOLVED"
            else:rating="INRB_VINTAGE_ONLY_NO_CELL_LINK"
            refs=[]
            for r in evidence:
                refs.append({"comparison_status":r.get("status",r.get("outcome")),
                  "report_number":r.get("pdf_report",r.get("report_number")),
                  "pdf_sha256":r.get("pdf_sha256",r.get("source_pdf_sha256")),
                  "pdf_page":r.get("pdf_page"),"pdf_table_id":r.get("pdf_table_id"),
                  "pdf_source_row":r.get("pdf_source_row"),
                  "pdf_candidate_value":r.get("pdf_value",r.get("pdf_value_candidate"))})
            item["pdf_comparison_evidence"]=refs
            item["evidence_class"]=rating
            item["decision_value"]=item["value"]
            item["decision_value_role"]="CURATED_INRB_VINTAGE_NOT_APPROVED_EPIDEMIOLOGICAL_ESTIMATE"
            item["as_reported_pdf_confirmed"]=False
            item["research_grade_approved"]=False
            counts[rating]+=1
            dest.write(json.dumps(item,ensure_ascii=False,separators=(",",":"))+"\n")
    result={"schema_version":"bdbv-historical-evidence-alignment-v1",
     "source_inrb_commit":summary["inrb_commit"],
     "records":sum(counts.values()),"statuses":dict(counts),
     "status":"RECONCILED_PROVISIONAL_REVIEW_REQUIRED",
     "approved_numeric_observations":0,
     "limitations":[
       "INRB curated values remain frozen at a historical Git commit, not proven as-reported originals.",
       "PDF candidate agreements are not independent epidemiological checks.",
       "Source-cell mismatches are retained, never auto-corrected.",
       "Values may include carried-forward or derived data; chronology is not a reconstructed incidence curve.",
       "Country/province/zone mapping aliases are not inferred.",
       "Human visual source verification is required for research-grade approval."]}
    (output/"historical_evidence_alignment_summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--historical",type=Path,required=True)
    p.add_argument("--zone-ledger",type=Path,required=True)
    p.add_argument("--national-ledger",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();build(a.historical,a.zone_ledger,a.national_ledger,a.out)
