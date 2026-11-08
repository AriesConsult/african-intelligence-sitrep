#!/usr/bin/env python3
"""Find primary SitRep revision-language leads for curated cumulative decreases.

Signals only; a revision keyword near a place is never a numerical
adjudication. Preserve actual source PDF SHA/page and exact quoted context.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,re,unicodedata
from collections import Counter,defaultdict
from datetime import date,timedelta
from pathlib import Path

REVISION=re.compile(
 r"harmonis|reconcili|rectifi|corrig|correcti|reclass|revis|ajust|actualis|mise(?:s)?\s+a\s+jour|"
 r"regul|data\s+clean|apure|retrospect|discordan",re.I)
def norm(s):
    return "".join(c for c in unicodedata.normalize("NFKD",str(s).lower()) if not unicodedata.combining(c))

def run(revision_file,full_pages,out):
    audit=json.loads((Path(full_pages)/"page_extraction_audit.json").read_text(encoding="utf-8"))
    bydate=defaultdict(list)
    for r in audit["records"]:
        p=Path(full_pages)/r["extraction_file"]
        if hashlib.sha256(p.read_bytes()).hexdigest()!=r["compressed_sha256"]:
            raise ValueError("Source page extraction hash mismatch")
        with gzip.open(p,"rt",encoding="utf-8") as f:doc=json.load(f)
        if doc["source_sha256"]!=r["source_sha256"]:raise ValueError("Original source identity mismatch")
        for pg in doc["pages"]:
            bydate[doc["report_date"]].append({"report_number":doc["report_number"],
                "pdf_sha256":doc["source_sha256"],"page":pg["page"],"text":pg["text_sorted"]})
    with Path(revision_file).open(encoding="utf-8-sig",newline="") as fp:
        revisions=list(csv.DictReader(fp))
    counts=Counter();data=[]
    for r in revisions:
        day=date.fromisoformat(r["current_date"])
        dates={(day+timedelta(days=k)).isoformat() for k in (0,1,2)}
        zone=norm(r["geography_raw"])
        zone_regex=re.compile(r"(?<!\w)"+re.escape(zone)+r"(?!\w)") if len(zone)>=3 else None
        leads=[]
        for d in sorted(dates):
            for pg in bydate.get(d,[]):
                text=norm(pg["text"])
                mentions_zone=bool(zone_regex.search(text)) if zone_regex else False
                for match in list(REVISION.finditer(text))[:18]:
                    start=max(0,match.start()-140);end=min(len(text),match.end()+180)
                    context=pg["text"][start:end] # approximate: Unicode normalization may change indices slightly
                    leads.append({"report_date":d,"report_number":pg["report_number"],
                        "source_pdf_sha256":pg["pdf_sha256"],"page":pg["page"],
                        "geography_mentioned_on_same_page":mentions_zone,
                        "match_term":match.group(0),"approximate_context":context.strip()})
        if not leads:classification="NO_EXPLICIT_REVISION_LEXICON_LEAD_IN_NEARBY_REPORTS"
        elif any(x["geography_mentioned_on_same_page"] for x in leads):
            classification="REVISION_TERM_AND_ZONE_ON_SAME_REPORT_PAGE_NOT_CAUSALLY_LINKED"
        else:classification="REVISION_TERM_PRESENT_GEOGRAPHY_NOT_ON_SAME_PAGE"
        counts[classification]+=1
        data.append({"metric_id":r["metric_id"],"geography_raw":r["geography_raw"],
            "previous_date":r["previous_date"],"current_date":r["current_date"],
            "previous_value":r["previous_value"],"current_value":r["current_value"],
            "delta":r["delta"],"classification":classification,
            "source_page_candidates":leads[:30],
            "approved_as_documented_revision":False})
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with (out/"cumulative_revision_source_page_leads.jsonl").open("w",encoding="utf-8") as fp:
        for r in data:fp.write(json.dumps(r,ensure_ascii=False)+"\n")
    result={"schema_version":"bdbv-revision-source-language-leads-v1",
      "status":"PRIMARY_SOURCE_TEXT_LEADS_NOT_ADJUDICATION",
      "cumulative_decreases_reviewed":len(data),
      "classification_counts":dict(counts),
      "notes":["Search the observed date and following two calendar days; do not assume every SitRep was published.",
       "An explicit correction must identify the same metric, place and reference period to prove the reported numerical change.",
       "The original source PDFs remain the evidence of record, and source-page context is only a locator.",
       "The appearance of correction language does not license rewriting older case counts or redistributing deaths."]}
    (out/"cumulative_revision_source_lead_summary.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    return result
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--revisions",type=Path,required=True)
    p.add_argument("--full-pages",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();run(a.revisions,a.full_pages,a.out)
