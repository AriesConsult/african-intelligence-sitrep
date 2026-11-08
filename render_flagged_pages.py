#!/usr/bin/env python3
"""Render PDF pages flagged by full-page extraction for human visual inspection.

Images are evidence for review, not a source-text verification or OCR result.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import zipfile
from pathlib import Path
import pymupdf

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--zip",type=Path,required=True)
    p.add_argument("--audit-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    audit=json.loads((a.audit_dir/"page_extraction_audit.json").read_text(encoding="utf-8"))
    a.output.mkdir(parents=True,exist_ok=True)
    review=[]
    with zipfile.ZipFile(a.zip) as original:
        for r in audit["records"]:
            compressed=a.audit_dir/r["extraction_file"]
            with gzip.open(compressed,"rt",encoding="utf-8") as fp:
                data=json.load(fp)
            flagged=[page for page in data["pages"] if page["flags"]]
            if not flagged:
                continue
            name=f"SitRep_{r['report_number']:03d}_{r['source_sha256'][:12]}.pdf"
            raw=original.read(name)
            if hashlib.sha256(raw).hexdigest()!=r["source_sha256"]:
                raise RuntimeError(f"PDF identity mismatch: {name}")
            doc=pymupdf.open(stream=raw,filetype="pdf")
            for page in flagged:
                page_number=page["page"]
                outname=f"SitRep_{r['report_number']:03d}_page_{page_number:02d}.png"
                pix=doc[page_number-1].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
                pix.save(a.output/outname)
                review.append({"report_number":r["report_number"],"page":page_number,
                    "source_sha256":r["source_sha256"],"image_file":outname,
                    "flags":page["flags"],"status":"VISUAL_REVIEW_REQUIRED"})
    (a.output/"review_index.json").write_text(json.dumps({
        "status":"VISUAL_REVIEW_REQUIRED",
        "note":"Page renderings from original SHA-verified PDFs, not OCR or validated transcriptions",
        "flagged_pages":len(review),"pages":review},indent=2)+"\n",encoding="utf-8")
    print(f"Rendered {len(review)} pages for visual review")
    if len(review) != audit["image_heavy_pages"]:
        raise RuntimeError("Rendered page count disagrees with flagged-page audit")

if __name__=="__main__":
    main()
