#!/usr/bin/env python3
"""Locate missing health-zone candidates in full-page original-PDF text.

Creates reproducible evidence pointers, never validates an INRB number from a
mere place-name occurrence. No source value enters the approved feed.
"""
from __future__ import annotations
import argparse
import gzip
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

def norm(text):
    s="".join(c for c in unicodedata.normalize("NFKD",str(text or "").lower())
              if not unicodedata.combining(c))
    return re.sub(r"\s+"," ",s.replace("’","'")).strip()

def locate(ledger, fullpages, output):
    audit=json.loads((Path(fullpages)/"page_extraction_audit.json").read_text(encoding="utf-8"))
    if audit["status"]!="ALL_ARCHIVED_PDFS_EXTRACTED_FIDELITY_REVIEW_PENDING":
        raise ValueError("Full page source audit is not complete")
    by_date=defaultdict(list)
    for record in audit["records"]:
        p=Path(fullpages)/record["extraction_file"]
        with gzip.open(p,"rt",encoding="utf-8") as inp:
            doc=json.load(inp)
        if doc.get("source_sha256")!=record["source_sha256"]:
            raise ValueError("Full page source hash mismatch")
        pages=[(item["page"],norm(item.get("text_sorted",""))) for item in doc["pages"]]
        by_date[doc["report_date"]].append({"report_number":doc["report_number"],
                                             "source_sha256":doc["source_sha256"],"pages":pages})
    counts=Counter()
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with Path(ledger).open(encoding="utf-8") as fp,(output/"unmatched_zone_page_leads.jsonl").open("w",encoding="utf-8") as dest:
        for line in fp:
            rec=json.loads(line)
            if rec.get("status")!="NO_DIRECT_PDF_TABLE2_CELL_FOR_DATE_AND_ZONE":
                continue
            date=rec["date"];geo=norm(rec["geography"])
            targets=by_date.get(date,[])
            found=[]
            if targets and geo:
                expr=re.compile(r"(?<!\w)"+re.escape(geo)+r"(?!\w)")
                for target in targets:
                    for page,text in target["pages"]:
                        if expr.search(text):
                            found.append({"report_number":target["report_number"],
                                          "pdf_sha256":target["source_sha256"],
                                          "page":page,"matching_text":"ZONE_NAME_ONLY_NOT_A_CELL"})
            if not targets:status="NO_SAME_DATE_ARCHIVED_SITREP"
            elif found:status="ZONE_MENTIONED_ON_PDF_PAGE_SOURCE_CELL_UNVERIFIED"
            else:status="ZONE_NAME_NOT_FOUND_IN_EXTRACTED_TEXT"
            counts[status]+=1
            dest.write(json.dumps({"date":date,"metric_id":rec["metric_id"],
              "geography":rec["geography"],"inrb_value_raw":rec["inrb_value_raw"],
              "inrb_csv_path":rec["inrb_csv_path"],"inrb_csv_row":rec["inrb_csv_row"],
              "source_candidates":found,"status":status,
              "approved_for_analysis":False},ensure_ascii=False)+"\n")
    report={"schema_version":"bdbv-historical-zone-page-locator-v1",
        "status":"SOURCE_PAGE_LEADS_REVIEW_REQUIRED","counts":dict(counts),
        "inrb_candidate_rows_located":sum(counts.values()),
        "warning":"A name appearing anywhere on a PDF page is not proof that the INRB value appears on that page, was reported directly, or matches a table cell."}
    (output/"unmatched_zone_page_locator_summary.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--ledger",type=Path,required=True)
    parser.add_argument("--full-pages",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    a=parser.parse_args()
    locate(a.ledger,a.full_pages,a.out)
