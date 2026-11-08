#!/usr/bin/env python3
"""Preserve every embedded raster image from SHA-verified SitRep originals.

Produce content-addressed image assets and a source/page/bbox manifest.
Source PDF bytes remain authoritative; visual assets are review copies.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

import pymupdf


def preserve(zip_path: Path, full_audit_path: Path, target: Path):
    audit=json.loads(full_audit_path.read_text(encoding="utf-8"))
    if audit.get("status") != "ALL_ARCHIVED_PDFS_EXTRACTED_FIDELITY_REVIEW_PENDING":
        raise ValueError("Full-page source verification is not complete")
    target.mkdir(parents=True,exist_ok=True)
    assets=target/"assets"
    assets.mkdir(parents=True,exist_ok=True)
    mapping=[]
    errors=[]
    seen={}
    source_images=0
    with zipfile.ZipFile(zip_path) as z:
        for record in audit["records"]:
            num,sha=record["report_number"],record["source_sha256"]
            name=f"SitRep_{num:03d}_{sha[:12]}.pdf"
            try:
                raw=z.read(name)
                if hashlib.sha256(raw).hexdigest()!=sha:
                    raise ValueError("PDF SHA mismatch")
                doc=pymupdf.open(stream=raw,filetype="pdf")
                if doc.page_count!=record["pages"]:
                    raise ValueError("PDF page count mismatch")
                for page_index,page in enumerate(doc):
                    blocks=page.get_text("dict",sort=False)["blocks"]
                    images=[b for b in blocks if b.get("type")==1]
                    for index,b in enumerate(images):
                        data=b.get("image")
                        if not data:
                            raise ValueError(f"Image without extractable bytes on page {page_index+1}")
                        digest=hashlib.sha256(data).hexdigest()
                        ext=str(b.get("ext") or "bin").lower()
                        if not re.fullmatch(r"[a-z0-9]{2,8}",ext):
                            ext="bin"
                        asset_name=f"{digest}.{ext}"
                        asset_path=assets/asset_name
                        if digest not in seen:
                            asset_path.write_bytes(data)
                            seen[digest]=asset_name
                        elif seen[digest]!=asset_name:
                            # Same bytes may have multiple reported formats; reuse original.
                            asset_name=seen[digest]
                        bbox=[round(float(v),2) for v in b.get("bbox",[])]
                        mapping.append({"report_number":num,"source_sha256":sha,
                            "page":page_index+1,"image_index":index,
                            "bbox":bbox,"width":b.get("width"),"height":b.get("height"),
                            "image_sha256":digest,"asset_path":"assets/"+asset_name})
                        source_images+=1
                print(f"Raster inventory SitRep {num:03d}: {doc.page_count} pages",flush=True)
            except Exception as exc:
                errors.append({"report_number":num,"reason":str(exc)[:180]})
    for digest,filename in seen.items():
        if hashlib.sha256((assets/filename).read_bytes()).hexdigest()!=digest:
            errors.append({"asset_path":filename,"reason":"Written image hash mismatch"})
    result={"schema_version":"bdbv-raster-preservation-v1",
        "status":"RASTER_RESOURCES_PRESERVED_REVIEW_PENDING" if not errors else "INCOMPLETE",
        "documents_examined":len(audit["records"]),"image_occurrences":source_images,
        "distinct_binary_image_assets":len(seen),"errors":errors,
        "limitations":["Embedded raster assets are preserved without OCR or interpretation",
                       "Vector drawings are retained in the original SHA-verified PDF, not reconstructed here",
                       "Visual reading order and completeness still require page-level review"],
        "images":mapping}
    (target/"image_manifest.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="images"},indent=2))
    if errors:raise SystemExit(1)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--zip",type=Path,required=True)
    parser.add_argument("--audit-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    opts=parser.parse_args()
    preserve(opts.zip,opts.audit_dir/"page_extraction_audit.json",opts.output)
