#!/usr/bin/env python3
"""Exhaustive source-linked *inventory* of extractable content in SitRep full-page records.

Do not confuse presence of topic terms or numbers with validated observations.
No source text is published by this step. All output is review-only metadata.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from sitrep_narratives import TOPICS, PROVINCES, normalize

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def inventory(directory: Path, registry_path: Path, output: Path):
    registry=read(registry_path)
    audit=read(directory/"page_extraction_audit.json")
    expected=registry["documents"]
    rows=[]; exceptions=[]; totals=Counter(); by_topic=Counter(); by_province=Counter()
    audited=set()
    for record in audit["records"]:
        num,sha=record["report_number"],record["source_sha256"]
        key=f"{num:03d}:{sha}"
        faults=[]
        def err(msg):
            faults.append(msg)
            exceptions.append({"report_number":num,"reason":msg})
        if key in audited:err("duplicate_document_in_audit")
        audited.add(key)
        if key not in expected:err("source_not_registered")
        path=directory/record["extraction_file"]
        if not path.is_file():
            err("full_page_extract_missing")
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record["compressed_sha256"]:
            err("compressed_extract_sha_mismatch")
            continue
        with gzip.open(path,"rt",encoding="utf-8") as fp:
            doc=json.load(fp)
        pages=doc.get("pages",[])
        if doc.get("source_sha256")!=sha or doc.get("report_number")!=num:
            err("extraction_source_identity_mismatch")
        if expected.get(key,{}).get("pages")!=len(pages):
            err("registry_page_count_mismatch")
        page_ids=[p.get("page") for p in pages]
        if page_ids!=list(range(1,len(pages)+1)):
            err("missing_or_duplicate_page_number")
        text_chars=0;text_pages=0; image_pages=0; drawing_pages=0
        pages_with_digits=0; pages_with_text_blocks=0
        top=Counter();prov=Counter(); numeric_tokens=0; empty_pages=[]
        for page in pages:
            text=page.get("text_sorted","")
            if hashlib.sha256(text.encode("utf-8")).hexdigest()!=page.get("text_sha256"):
                err("page_text_hash_mismatch")
            page_num=page.get("page")
            text_chars+=len(text)
            if text.strip():text_pages+=1
            else:empty_pages.append(page_num)
            if page.get("image_locations"):image_pages+=1
            if page.get("drawing_count",0):drawing_pages+=1
            if page.get("text_blocks"):pages_with_text_blocks+=1
            numeric_tokens+=len(re.findall(r"(?<!\w)\d[\d\s.,%]*",text))
            if re.search(r"\d",text):pages_with_digits+=1
            cleaned=normalize(text)
            for name,pattern in TOPICS.items():
                if re.search(pattern,cleaned,re.I):top[name]+=1
            for name,pattern in PROVINCES.items():
                if re.search(pattern,cleaned,re.I):prov[name]+=1
        # These are coverage indicators. A page may have content without a narrative keyword.
        if not text_pages:err("no_extracted_text_in_document")
        if not top:err("no_existing_topic_lexicon_match")
        totals.update({"documents":1,"pages":len(pages),"pages_with_text":text_pages,
            "pages_with_images":image_pages,"pages_with_drawings":drawing_pages,
            "pages_with_text_blocks":pages_with_text_blocks,"pages_with_digits":pages_with_digits,
            "text_characters":text_chars,"numeric_token_matches":numeric_tokens})
        by_topic.update(top)
        by_province.update(prov)
        rows.append({"report_number":num,"report_date":expected.get(key,{}).get("report_date"),
            "source_sha256":sha,"pages":len(pages),"text_pages":text_pages,
            "pages_with_images":image_pages,"pages_with_drawings":drawing_pages,
            "text_characters":text_chars,"numeric_token_matches_unverified":numeric_tokens,
            "topic_matches_page_count":dict(sorted(top.items())),
            "province_mentions_page_count":dict(sorted(prov.items())),
            "empty_text_page_numbers":empty_pages,"flags":faults,
            "status":"SOURCE_LINKED_MACHINE_EXTRACTION_REVIEW_REQUIRED"})
    missing=sorted(set(expected)-audited)
    for key in missing:exceptions.append({"report_number":expected[key]["report_number"],"reason":"registered_source_not_in_full_page_audit"})
    result={"schema_version":"bdbv-content-availability-inventory-v1",
        "scope":"machine extraction content presence by original SitRep and page",
        "status":"INCOMPLETE" if missing or any(x["reason"] not in ("no_existing_topic_lexicon_match",) for x in exceptions) else "ALL_REGISTERED_DOCUMENTS_INVENTORIED_REVIEW_REQUIRED",
        "counters":dict(totals),"topic_page_occurrences":dict(by_topic),
        "province_mention_page_occurrences":dict(by_province),
        "documents_without_lexicon_hits":[x["report_number"] for x in rows if "no_existing_topic_lexicon_match" in x["flags"]],
        "registered_documents_missing":missing,"exceptions":exceptions,
        "interpretation_limits":[
            "Lexical matches locate relevant pages; they are not verified events or epidemiological values.",
            "Numeric token counts measure text presence, not correctly parsed table cells.",
            "Extracted reading order, graphics, raster-only text and table structure require comparison with source PDF.",
            "This inventory does not select which variables or themes should be used for analysis."],
        "reports":sorted(rows,key=lambda r:r["report_number"])}
    output.mkdir(parents=True,exist_ok=True)
    (output/"content_availability_inventory.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (output/"content_availability_inventory.csv").open("w",encoding="utf-8",newline="") as fp:
        fields=["report_number","report_date","source_sha256","pages","text_pages","pages_with_images",
                "pages_with_drawings","text_characters","numeric_token_matches_unverified","topic_matches_page_count",
                "province_mentions_page_count","empty_text_page_numbers","flags","status"]
        w=csv.DictWriter(fp,fieldnames=fields);w.writeheader()
        for row in rows:w.writerow({k:json.dumps(row[k],ensure_ascii=False) if isinstance(row[k],(list,dict)) else row[k] for k in fields})
    print(json.dumps({k:v for k,v in result.items() if k!="reports"},ensure_ascii=False,indent=2))
    if result["status"]=="INCOMPLETE":raise SystemExit(1)
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--full-pages",type=Path,required=True)
    parser.add_argument("--registry",type=Path,default=Path("state/registry.json"))
    parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args()
    inventory(a.full_pages,a.registry,a.output)
