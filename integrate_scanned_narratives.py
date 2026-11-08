#!/usr/bin/env python3
"""Stage scanned-SitRep OCR as labelled narrative candidates alongside 158 originals.

Never call OCR human-verified source text. All page hashes and source IDs must
match the standalone scanned-original custody register.
"""
import argparse,gzip,hashlib,json
from collections import defaultdict
from pathlib import Path
from stage_narrative_sections import split_document

def integrate(ocr_file,index_file,summary_file,out):
    origin=json.loads(Path(index_file).read_text(encoding="utf-8"))
    ocr_summary=json.loads(Path(summary_file).read_text(encoding="utf-8"))
    if ocr_summary.get("page_count")!=37:raise ValueError("37 scanned pages not all processed")
    originals={r["report_number"]:r for r in origin["source_records"]}
    pages=defaultdict(list)
    with gzip.open(ocr_file,"rt",encoding="utf-8") as inp:
        for line in inp:
            p=json.loads(line)
            num=p["report_number"]
            if num not in originals or p["pdf_sha256"]!=originals[num]["source_sha256"]:
                raise ValueError("Scanned source identity mismatch")
            if hashlib.sha256(p["text"].encode("utf-8")).hexdigest()!=p["text_sha256"]:
                raise ValueError("Unverified/corrupt OCR text hash")
            pages[num].append(p)
    if set(pages)!={7,8,9}:raise ValueError("Expected three scanned reports")
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    counts={"scanned_reports":0,"scanned_pages":0,"provisional_sections":0,"ocr_words":0}
    indexes=[]
    with gzip.open(out/"scanned_narrative_section_candidates.jsonl.gz","wt",encoding="utf-8") as dest:
        for num in sorted(pages):
            group=sorted(pages[num],key=lambda x:x["page"])
            expected=originals[num]
            if len(group)!=expected["pdf_pages"] or [p["page"] for p in group]!=list(range(1,len(group)+1)):
                raise ValueError("OCR pages incomplete or duplicated")
            doc={"pages":[{"text_sorted":p["text"]} for p in group]}
            sections,total=split_document(doc)
            counts["scanned_reports"]+=1;counts["scanned_pages"]+=len(group)
            counts["ocr_words"]+=sum(p["word_count"] for p in group)
            counts["provisional_sections"]+=len(sections)
            for section in sections:
                row={"report_number":num,"source_sha256":expected["source_sha256"],
                     "report_date":expected["report_date"],
                     "source_text_method":"FRENCH_ENGLISH_OCR_UNVERIFIED",
                     "approved_for_interpretation":False,**section}
                dest.write(json.dumps(row,ensure_ascii=False)+"\n")
            indexes.append({"report_number":num,"original_pages":len(group),
                "ocr_words":sum(x["word_count"] for x in group),
                "ocr_text_chars":total,"section_candidates":len(sections),
                "transcription_status":"OCR_UNVERIFIED",
                "source_sha256":expected["source_sha256"]})
    summary={"schema_version":"bdbv-scanned-narrative-integration-v1",
        "status":"SCANNED_NARRATIVE_OCR_STAGED_REVIEW_REQUIRED",
        "original_digital_text_reports":158,
        "scanned_reports":counts["scanned_reports"],
        "combined_source_reports":158+counts["scanned_reports"],
        "scanned_pages":counts["scanned_pages"],
        "scanned_ocr_words":counts["ocr_words"],
        "scanned_provisional_sections":counts["provisional_sections"],
        "scanned_report_coverage":indexes,
        "limitations":["OCR text is not independently visually checked; word-confidence estimates cannot certify completeness.",
          "No original source narrative or numerical table cell is automatically approved.",
          "Digital-text section staging is archived separately and is not rewritten."]}
    (out/"scanned_narrative_integration_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="scanned_report_coverage"},indent=2))
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--ocr",type=Path,required=True)
    p.add_argument("--index",type=Path,default=Path("published/scanned_source_index.json"))
    p.add_argument("--summary",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();integrate(a.ocr,a.index,a.summary,a.out)
