#!/usr/bin/env python3
"""Audit narrative *coverage* against every immutable SitRep full-page extract.

This is a diagnostic, NOT an assertion that extracted PDF reading order,
paragraphs, headings or 37 scanned pages are semantically verified.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SECTION_PATTERNS={
 "coordination":r"\bcoordination\b",
 "surveillance":r"\bsurveillance\b|\balertes?\b",
 "border_points":r"\b(?:points?\s+d['’ ]entree|points?\s+de\s+controle|poe\s*/\s*poc)\b",
 "laboratory":r"\blaboratoire\b|\bdiagnostic\b",
 "case_management":r"\bprise\s+en\s+charge\b|\btraitement\b",
 "infection_prevention":r"\b(?:pci|prevention\s+et\s+controle|enterrements?\s+dignes?)\b",
 "vaccination":r"\bvaccination\b|\bvaccins?\b",
 "community_engagement":r"\b(?:engagement\s+communautaire|communication\s+des\s+risques|mobilisation\s+sociale|sensibilisation)\b",
 "logistics":r"\blogistique\b|\bapprovisionnement\b",
 "security":r"\bsecurite\b|\binsecurite\b",
 "psychosocial":r"\bpsychosocial\b|\bpsychologique\b",
}
ACCENTS=str.maketrans({"é":"e","è":"e","ê":"e","ë":"e","à":"a","â":"a","ô":"o","î":"i","ï":"i","ù":"u","û":"u","ç":"c"})

def normalize(s):return re.sub(r"\s+"," ",str(s).lower().translate(ACCENTS))

def audit(full_dir:Path, published:Path, source_index:Path, output:Path):
    registry=json.loads((published/"narrative_index.json").read_text(encoding="utf-8"))
    candidates={r["source_sha256"]:r for r in registry["reports"]}
    full=json.loads((full_dir/"page_extraction_audit.json").read_text(encoding="utf-8"))
    scanned=json.loads(source_index.read_text(encoding="utf-8"))
    if full["status"]!="ALL_ARCHIVED_PDFS_EXTRACTED_FIDELITY_REVIEW_PENDING":raise ValueError("PDF page audit incomplete")
    rows=[];headings=[];totals=Counter();section_report_counts=Counter()
    output.mkdir(parents=True,exist_ok=True)
    with gzip.open(output/"full_narrative_page_evidence.jsonl.gz","wt",encoding="utf-8") as dest:
        for source in full["records"]:
            sha=source["source_sha256"];num=source["report_number"]
            path=full_dir/source["extraction_file"]
            if hashlib.sha256(path.read_bytes()).hexdigest()!=source["compressed_sha256"]:raise ValueError("Corrupt page extraction")
            with gzip.open(path,"rt",encoding="utf-8") as fp:doc=json.load(fp)
            if doc["source_sha256"]!=sha:raise ValueError("Source hash mismatch")
            snap_ref=candidates.get(sha)
            snap=None
            if snap_ref:
                rel=snap_ref["snapshot_path"]
                if not rel.startswith("narrative_candidates/") or ".." in rel:raise ValueError("Unsafe narrative path")
                snap=json.loads((published/rel).read_text(encoding="utf-8"))
                if snap["source_sha256"]!=sha or snap["report_number"]!=num:raise ValueError("Candidate source mismatch")
            by_page=defaultdict(list)
            if snap:
                for cand in snap["candidates"]:by_page[cand["page"]].append(cand)
            page_topics=set()
            for pg in doc["pages"]:
                text=pg.get("text_sorted","")
                if hashlib.sha256(text.encode("utf-8")).hexdigest()!=pg["text_sha256"]:raise ValueError("Page text hash mismatch")
                page=pg["page"];cands=by_page.get(page,[])
                count_truncated=sum(bool(c.get("excerpt_truncated")) for c in cands)
                headings_here=[]
                for line in text.splitlines():
                    trimmed=line.strip()
                    if len(trimmed)>145 or len(trimmed)<5:continue
                    # Heading candidate is a structural locator, not a verified section boundary.
                    if re.match(r"^(?:\d+(?:\.\d+){0,3}[.)]?\s+|[IVX]+[.)]\s+)",trimmed):
                        headings_here.append(trimmed)
                for h in headings_here[:35]:
                    headings.append({"report_number":num,"source_sha256":sha,"page":page,
                                     "heading_candidate":h,"verified_as_section":False})
                for topic,rx in SECTION_PATTERNS.items():
                    if re.search(rx,normalize(text)):
                        page_topics.add(topic)
                status=("NO_DIGITALLY_EXTRACTABLE_TEXT" if not text.strip()
                    else "FULL_PAGE_TEXT_RETAINED_READING_ORDER_UNVERIFIED")
                record={"report_number":num,"source_sha256":sha,"report_date":doc["report_date"],
                    "page":page,"full_text":text,"text_sha256":pg["text_sha256"],
                    "image_occurrences":len(pg.get("image_locations",[])),
                    "narrative_candidate_blocks":len(cands),"truncated_candidate_excerpts":count_truncated,
                    "structural_heading_candidates":headings_here[:35],"page_status":status}
                dest.write(json.dumps(record,ensure_ascii=False)+"\n")
                totals["pages"]+=1
                totals["chars"]+=len(text)
                totals["truncated_excerpts"]+=count_truncated
                if cands:totals["pages_with_narrative_candidates"]+=1
                if not text.strip():totals["zero_text_pages"]+=1
            totals["documents"]+=1
            if not snap:totals["documents_without_candidate_snapshot"]+=1
            for topic in page_topics:section_report_counts[topic]+=1
            rows.append({"report_number":num,"report_date":doc["report_date"],"source_sha256":sha,
                "pages":len(doc["pages"]),"candidate_snapshot":bool(snap),
                "candidate_blocks":len(snap["candidates"]) if snap else 0,
                "truncated_candidate_excerpts":sum(bool(c.get("excerpt_truncated")) for v in by_page.values() for c in v),
                "pages_with_candidate_blocks":len(by_page),"heading_candidates":sum(1 for h in headings if h["report_number"]==num),
                "text_chars":sum(len(p["text_sorted"]) for p in doc["pages"]),
                "topic_terms_seen_on_full_pages":";".join(sorted(page_topics)),
                "status":"FULL_TEXT_AVAILABLE_SECTION_BOUNDARIES_NOT_VERIFIED"})
    for scan in scanned["source_records"]:
        rows.append({"report_number":scan["report_number"],"report_date":scan["report_date"],
           "source_sha256":scan["source_sha256"],"pages":scan["pdf_pages"],
           "candidate_snapshot":False,"candidate_blocks":0,"truncated_candidate_excerpts":0,
           "pages_with_candidate_blocks":0,"heading_candidates":0,"text_chars":0,
           "topic_terms_seen_on_full_pages":"",
           "status":"SCANNED_ORIGINALS_PRESERVED_TRANSCRIPTION_REVIEW_REQUIRED"})
    with (output/"narrative_report_coverage.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(sorted(rows,key=lambda r:r["report_number"]))
    with (output/"narrative_heading_candidates.csv").open("w",newline="",encoding="utf-8") as f:
        fieldnames=["report_number","source_sha256","page","heading_candidate","verified_as_section"]
        w=csv.DictWriter(f,fieldnames=fieldnames);w.writeheader();w.writerows(headings)
    summary={"schema_version":"bdbv-complete-narrative-coverage-audit-v1",
      "status":"PAGE_TEXT_PRESERVED_NARRATIVE_BOUNDARIES_UNVERIFIED",
      "digitally_extractable_documents":totals["documents"],
      "scanned_documents_pending_transcription":len(scanned["source_records"]),
      "all_documents_inventory":len(rows),"full_text_pages":totals["pages"],
      "zero_text_pages":totals["zero_text_pages"],
      "pages_with_narrative_candidates":totals["pages_with_narrative_candidates"],
      "truncated_previous_candidate_excerpts":totals["truncated_excerpts"],
      "documents_without_candidate_snapshot":totals["documents_without_candidate_snapshot"],
      "source_text_chars":totals["chars"],
      "unverified_section_heading_candidates":len(headings),
      "report_counts_with_topic_term_anywhere":dict(section_report_counts),
      "caveats":["Occurrence of a keyword on a page does not prove complete narrative section extraction.",
                 "Text page order and section boundaries must be visually checked on a stratified sample.",
                 "The original candidate index truncated some excerpts, but full page text is preserved separately.",
                 "37 scanned pages from SitReps 007-009 require separately reviewed transcription.",
                 "This does not label absent terms as missing reporting."]}
    (output/"narrative_coverage_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--full-dir",type=Path,required=True)
    parser.add_argument("--published",type=Path,default=Path("published"))
    parser.add_argument("--scanned-index",type=Path,default=Path("published/scanned_source_index.json"))
    parser.add_argument("--out",type=Path,required=True)
    a=parser.parse_args();audit(a.full_dir,a.published,a.scanned_index,a.out)
