#!/usr/bin/env python3
"""Lossless reconstruction of candidate narrative sections from full-page text.

All characters in the mechanical PDF text are retained. Section headings are
heuristic and NOT manually confirmed; complete textual reconstruction does not
imply correct PDF reading order or OCR of scanned pages.
"""
import argparse,gzip,hashlib,json,re
from collections import Counter
from pathlib import Path

# Only obvious numbered section headings, never generic topic keyword matches.
HEADING=re.compile(r"^\s*(?:(?:\d{1,2}(?:\.\d{1,2}){0,3}|[IVX]{1,5})[.)]?\s+)([^\n]{5,95})$")
def candidate_heading(line):
    m=HEADING.match(line.rstrip("\r\n"))
    if not m:return None
    title=m.group(1).strip(" .:;-")
    if len(title.split())>14 or re.match(r"^\d+[ ,.]",title):return None
    # Number-only table rows should not be section headings.
    if sum(ch.isalpha() for ch in title)<5:return None
    return line.strip()

def split_document(document):
    pages=document["pages"]
    separator="\n\f\n"
    raw=separator.join(pg["text_sorted"] for pg in pages)
    page_starts=[];offset=0
    for n,pg in enumerate(pages):
        page_starts.append(offset)
        offset+=len(pg["text_sorted"])+(len(separator) if n<len(pages)-1 else 0)
    boundaries=[(0,None,1)]
    pos=0
    for page_i,page in enumerate(pages):
        if page_i:pos+=len(separator)
        for line in page["text_sorted"].splitlines(keepends=True):
            heading=candidate_heading(line)
            if heading and pos>boundaries[-1][0]:
                boundaries.append((pos,heading,page_i+1))
            pos+=len(line)
    if pos!=len(raw):raise ValueError("Mismatch computing source text offset")
    results=[]
    for i,(start,heading,first_page) in enumerate(boundaries):
        end=boundaries[i+1][0] if i+1<len(boundaries) else len(raw)
        original=raw[start:end]
        end_page=max(1,sum(1 for off in page_starts if off<end))
        results.append({"section_index":i,"heading_candidate":heading,
             "start_page":first_page,"end_page":end_page,
             "start_offset":start,"end_offset":end,
             "text":original,"text_sha256":hashlib.sha256(original.encode("utf-8")).hexdigest(),
             "segmentation_status":"NUMBERED_HEADING_HEURISTIC_REVIEW_REQUIRED" if heading else "UNASSIGNED_PREFACE_OR_UNDETECTED_SECTION",
             "complete_original_text_in_this_segment":True,
             "approved_for_interpretation":False})
    if "".join(section["text"] for section in results)!=raw:
        raise ValueError("Non-lossless narrative segmentation")
    return results,len(raw)

def run(full_dir:Path,out:Path):
    audit=json.loads((full_dir/"page_extraction_audit.json").read_text(encoding="utf-8"))
    out.mkdir(parents=True,exist_ok=True)
    counts=Counter();report_index=[]
    with gzip.open(out/"narrative_full_section_candidates.jsonl.gz","wt",encoding="utf-8",compresslevel=6) as dest:
        for r in audit["records"]:
            p=full_dir/r["extraction_file"]
            if hashlib.sha256(p.read_bytes()).hexdigest()!=r["compressed_sha256"]:
                raise ValueError("Original extraction ZIP member corruption")
            with gzip.open(p,"rt",encoding="utf-8") as fp:doc=json.load(fp)
            if doc["source_sha256"]!=r["source_sha256"]:raise ValueError("Source PDF identity mismatch")
            sections,text_chars=split_document(doc)
            for section in sections:
                record={"report_number":r["report_number"],"report_date":doc["report_date"],
                        "source_sha256":r["source_sha256"],**section}
                dest.write(json.dumps(record,ensure_ascii=False)+"\n")
            report_index.append({"report_number":r["report_number"],"source_sha256":r["source_sha256"],
                "pages":len(doc["pages"]),"sections":len(sections),"heading_candidates":sum(bool(s["heading_candidate"]) for s in sections),
                "digitally_extracted_chars":text_chars,"reconstruction":"BYTE_EXACT_TEXT_REASSEMBLY_VERIFIED",
                "section_boundaries":"HEURISTIC_NOT_VERIFIED"})
            counts["reports"]+=1;counts["candidate_sections"]+=len(sections)
            counts["headings"]+=sum(bool(s["heading_candidate"]) for s in sections)
            counts["source_chars"]+=text_chars
    summary={"schema_version":"bdbv-narrative-lossless-section-staging-v1",
        "status":"ALL_DIGITAL_PDF_PAGE_TEXT_REASSEMBLED_SECTION_LABELS_REVIEW_REQUIRED",
        "reports":counts["reports"],"candidate_sections":counts["candidate_sections"],
        "numbered_heading_candidates":counts["headings"],"text_characters_accounted_for":counts["source_chars"],
        "scanned_sources_excluded":[7,8,9],
        "limitations":["Heuristic headings can be false positives or miss unnumbered sections.",
            "Text is exactly preserved relative to PyMuPDF full-page extraction; raster, vector and scanned text may be missing.",
            "Sections include page separators; source-document page offsets remain reference points.",
            "No event/theme extraction or human section fidelity approval follows automatically."]}
    (out/"narrative_section_staging_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (out/"narrative_section_report_index.json").write_text(json.dumps(report_index,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))
    return summary

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--full-dir",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    a=parser.parse_args();run(a.full_dir,a.out)
