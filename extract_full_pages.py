#!/usr/bin/env python3
"""Extract every PDF page from SHA-verified SitRep release bundles.

Full, unredacted page extracts stay in CI artifacts, NOT in the public Git tree.
This is mechanical transcription, NOT an OCR/fidelity certificate.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
import re
import tempfile
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
import requests

ROOT = Path(__file__).resolve().parent

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def verify_member(z, item, registry):
    key = f"{item['report_number']:03d}:{item['source_sha256']}"
    if key not in registry["documents"]:
        raise ValueError("Unregistered PDF identity: " + key)
    member = item["archive_member"]
    if not re.fullmatch(r"SitRep_\d{3}_[a-f0-9]{12}\.pdf", member):
        raise ValueError("Invalid archive member name: " + member)
    raw = z.read(member)
    if len(raw) != item["pdf_bytes"] or hashlib.sha256(raw).hexdigest() != item["source_sha256"]:
        raise ValueError("PDF bytes/hash mismatch: " + key)
    if not raw.startswith(b"%PDF-"):
        raise ValueError("Not a PDF: " + key)
    return raw

def extract_one(raw, item, expected_pages):
    doc = pymupdf.open(stream=raw, filetype="pdf")
    if doc.is_encrypted or doc.page_count != expected_pages:
        raise ValueError("Encrypted or page-count mismatch")
    pages, flags = [], Counter()
    for pno, page in enumerate(doc, 1):
        blocks = page.get_text("dict", sort=False)["blocks"]
        text_blocks = []
        images = []
        chars = 0
        for block in blocks:
            bbox = [round(float(v), 2) for v in block.get("bbox", [])]
            if block.get("type") == 0:
                lines = []
                for line in block.get("lines", []):
                    spans = []
                    for span in line.get("spans", []):
                        content = span.get("text", "")
                        chars += len(content)
                        spans.append({"text": content, "bbox": [round(float(v),2) for v in span["bbox"]],
                                      "font": span.get("font"), "size": round(span.get("size", 0),2),
                                      "flags": span.get("flags")})
                    lines.append({"spans": spans, "bbox": [round(float(v),2) for v in line.get("bbox", [])]})
                text_blocks.append({"bbox": bbox, "lines": lines})
            elif block.get("type") == 1:
                images.append({"bbox": bbox, "width": block.get("width"), "height": block.get("height"),
                               "ext": block.get("ext"), "image_sha256": hashlib.sha256(block.get("image", b"")).hexdigest()
                               if block.get("image") else None})
        full_text = page.get_text("text", sort=True)
        # A zero-text page may be legitimately graphical; it requires independent review.
        page_flags = []
        if not full_text.strip():
            page_flags.append("NO_EXTRACTABLE_TEXT")
        if len(full_text.strip()) < 50 and images:
            page_flags.append("IMAGE_HEAVY_LOW_TEXT_REVIEW_OCR_POSSIBLE")
        for flag in page_flags: flags[flag] += 1
        pages.append({"page": pno, "width": round(page.rect.width,2),
                      "height": round(page.rect.height,2), "text_sorted": full_text,
                      "text_sha256": hashlib.sha256(full_text.encode("utf-8")).hexdigest(),
                      "text_blocks": text_blocks, "image_locations": images,
                      "drawing_count": len(page.get_drawings()), "flags": page_flags,
                      "character_count": len(full_text)})
    return {"schema_version": "bdbv-full-page-extraction-v1", "report_number": item["report_number"],
            "report_date": item["report_date"], "source_sha256": item["source_sha256"],
            "pdf_bytes": len(raw), "page_count": doc.page_count,
            "pages": pages, "review_flags": dict(flags)}

def audit(archive_zip, registry_path, index_path, out):
    registry, index = load(registry_path), load(index_path)
    out.mkdir(parents=True, exist_ok=True)
    extract_dir = out / "full_pages"
    extract_dir.mkdir(parents=True, exist_ok=True)
    records, errors = [], []
    with zipfile.ZipFile(archive_zip) as z:
        embedded = load_manifest(z)
        manifest_by_key = {f"{r['report_number']:03d}:{r['source_sha256']}": r for r in embedded.get("files", [])}
        indexed = index["archived"]
        if set(manifest_by_key) != set(indexed):
            raise ValueError("Embedded ZIP manifest does not match registered archive identities")
        for key, item in sorted(indexed.items(), key=lambda x: x[1]["report_number"]):
            num, sha = item["report_number"], item["source_sha256"]
            try:
                if item["archive_member"] != manifest_by_key[key]["archive_member"]:
                    raise ValueError("Archive manifest member mismatch")
                raw = verify_member(z, item, registry)
                document = extract_one(raw, item, registry["documents"][key]["pages"])
                filename = f"{num:03d}_{sha[:12]}.json.gz"
                destination = extract_dir / filename
                with gzip.open(destination, "wt", encoding="utf-8", compresslevel=6) as fp:
                    json.dump(document, fp, ensure_ascii=False, separators=(",", ":"))
                records.append({"report_number": num, "source_sha256": sha,
                    "pages": document["page_count"], "empty_text_pages": document["review_flags"].get("NO_EXTRACTABLE_TEXT",0),
                    "image_heavy_pages": document["review_flags"].get("IMAGE_HEAVY_LOW_TEXT_REVIEW_OCR_POSSIBLE",0),
                    "characters": sum(p["character_count"] for p in document["pages"]),
                    "extraction_file": "full_pages/" + filename,
                    "compressed_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                    "status": "EXTRACTED_REQUIRES_PAGE_FIDELITY_REVIEW"})
                print(f"SitRep {num:03d}: {document['page_count']} pages; verified original SHA", flush=True)
            except Exception as exc:
                errors.append({"report_number": num, "source_sha256": sha, "error": str(exc)[:200]})
                print(f"SitRep {num:03d} failed: {exc}", flush=True)
    report = {
      "schema_version": "bdbv-complete-page-ingestion-audit-v1",
      "created_at": datetime.now(timezone.utc).isoformat(),
      "status": "ALL_ARCHIVED_PDFS_EXTRACTED_FIDELITY_REVIEW_PENDING" if not errors and len(records)==len(index["archived"]) else "INCOMPLETE",
      "archived_documents": len(index["archived"]), "extracted_documents": len(records),
      "extracted_pages": sum(r["pages"] for r in records),
      "empty_text_pages": sum(r["empty_text_pages"] for r in records),
      "image_heavy_pages": sum(r["image_heavy_pages"] for r in records),
      "errors": errors, "records": records,
      "limitations": [
        "Original PDF checksum and page counts checked against registered sources",
        "All digitally extractable text and position-aware text spans retained; raster image positions and hashes captured",
        "Raster images, vector drawings and scanned text are not themselves fully transcribed",
        "No OCR is performed; image-heavy pages explicitly flagged for review",
        "Mechanical extraction is not a proof of completeness or visual fidelity",
        "Workflow artifacts expire and are not permanent preservation"],
    }
    (out / "page_extraction_audit.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    with (out / "page_extraction_audit.csv").open("w",newline="",encoding="utf-8") as fp:
        writer=csv.DictWriter(fp,fieldnames=list(records[0]) if records else ["report_number","source_sha256"])
        writer.writeheader()
        writer.writerows(records)
    print(json.dumps({k:v for k,v in report.items() if k!="records"},ensure_ascii=False,indent=2))
    if report["status"]=="INCOMPLETE":
        raise SystemExit(1)

def load_manifest(z):
    return json.loads(z.read("archive_manifest.json").decode("utf-8"))

def download(url, destination):
    if not url.startswith("https://github.com/") or "/releases/download/" not in url:
        raise ValueError("Unexpected archive URL")
    with requests.get(url,timeout=(30,180),stream=True) as response:
        response.raise_for_status()
        with destination.open("wb") as fp:
            for chunk in response.iter_content(1024*1024):
                if chunk: fp.write(chunk)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--registry",type=Path,default=ROOT/"state/registry.json")
    p.add_argument("--archive-index",type=Path,default=ROOT/"published/source_archive_index.json")
    p.add_argument("--out",type=Path,default=ROOT/"work/full_page_audit")
    p.add_argument("--zip",type=Path)
    args=p.parse_args()
    idx=load(args.archive_index)
    releases={r["download_url"] for r in idx["archived"].values()}
    if len(releases)!=1:
        raise ValueError("This audit run requires exactly one archived ZIP; run per-release for multiple archives")
    if args.zip:
        audit(args.zip,args.registry,args.archive_index,args.out)
    else:
        args.out.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory() as temp:
            archive=Path(temp)/"original_sitreps.zip"
            download(next(iter(releases)),archive)
            audit(archive,args.registry,args.archive_index,args.out)

if __name__=="__main__":
    main()
