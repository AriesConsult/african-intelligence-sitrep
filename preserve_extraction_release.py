#!/usr/bin/env python3
"""Make a durable, integrity-checked release from existing GitHub Actions evidence.

Does not imply PDF text, image reading order or historical cell values are verified.
"""
import argparse
import gzip
import hashlib
import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def bundle(source, destination):
    with tarfile.open(destination, "w:gz") as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.add(path,arcname=path.relative_to(source).as_posix(),recursive=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--registry",type=Path,default=Path("state/registry.json"))
    p.add_argument("--full-dir",type=Path,required=True)
    p.add_argument("--raster-dir",type=Path,required=True)
    p.add_argument("--comparison-dir",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--upstream-run",type=int,required=True)
    args=p.parse_args()
    registry=json.loads(args.registry.read_text(encoding="utf-8"))
    pdfs=json.loads((args.full_dir/"page_extraction_audit.json").read_text(encoding="utf-8"))
    raster=json.loads((args.raster_dir/"image_manifest.json").read_text(encoding="utf-8"))
    if pdfs["status"]!="ALL_ARCHIVED_PDFS_EXTRACTED_FIDELITY_REVIEW_PENDING":
        raise ValueError("Full-page audit is not verified for archival")
    if raster["status"]!="RASTER_RESOURCES_PRESERVED_REVIEW_PENDING":
        raise ValueError("Raster image preservation was not successful")
    original_ids={(x["report_number"],x["sha256"]) for x in registry["documents"].values()}
    recorded_ids={(x["report_number"],x["source_sha256"]) for x in pdfs["records"]}
    if original_ids!=recorded_ids:raise ValueError("Registry/report identity set mismatch")
    if raster["documents_examined"]!=len(recorded_ids):raise ValueError("Raster provenance document count mismatch")
    total_pages=0
    for r in pdfs["records"]:
        path=args.full_dir/r["extraction_file"]
        if sha(path)!=r["compressed_sha256"]:
            raise ValueError("Compressed full text checksum mismatch "+str(path))
        with gzip.open(path,"rt",encoding="utf-8") as fp:record=json.load(fp)
        if record["page_count"]!=r["pages"] or record["source_sha256"]!=r["source_sha256"]:
            raise ValueError("Full text original hash/page mismatch "+str(path))
        total_pages+=r["pages"]
    if total_pages!=pdfs["extracted_pages"]:raise ValueError("Page total mismatch")
    image_digests=set()
    for img in raster["images"]:
        digest=img["image_sha256"]
        if digest not in image_digests:
            path=args.raster_dir/img["asset_path"]
            if sha(path)!=digest:raise ValueError("Raster asset mismatch "+str(path))
            image_digests.add(digest)
    if len(image_digests)!=raster["distinct_binary_image_assets"]:
        raise ValueError("Unique raster assets mismatch")
    if len(raster["images"])!=raster["image_occurrences"]:
        raise ValueError("Image occurrence mismatch")
    for relative in ("national_banner_comparison.json","inrb_source_crosswalk.json",
                     "staged/inrb_staging_summary.json","staged/inrb_observation_candidates.jsonl.gz"):
        if not (args.comparison_dir/relative).is_file():
            raise ValueError("Missing pinned reconciliation source "+relative)
    args.out.mkdir(parents=True,exist_ok=True)
    sources=[("full_pages",args.full_dir),("raster_images",args.raster_dir),
             ("inrb_reconciliation",args.comparison_dir)]
    bundles=[]
    for name,src in sources:
        target=args.out/(name+".tar.gz")
        bundle(src,target)
        bundles.append({"filename":target.name,"sha256":sha(target),"bytes":target.stat().st_size})
    manifest={
       "schema_version":"bdbv-durable-extraction-evidence-v1",
       "created_at":datetime.now(timezone.utc).isoformat(),
       "source_workflow_run":args.upstream_run,
       "registered_source_documents":len(recorded_ids),
       "registered_source_pages":total_pages,
       "raster_image_occurrences":len(raster["images"]),
       "distinct_raster_binaries":len(image_digests),
       "original_pdf_sha256_values":sorted(x[1] for x in recorded_ids),
       "bundles":bundles,
       "status":"MECHANICAL_EXTRACTION_ARCHIVED_FIDELITY_REVIEW_PENDING",
       "preservation_policy":"Release files immutable by convention; never modify an existing tag. Raw INSP PDF originals remain in separate permanent release.",
       "not_certified":["PDF cell reading order and transcription","Missing scanned text","Unvalidated health-zone observations"],
    }
    (args.out/"evidence_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in manifest.items() if k!="original_pdf_sha256_values"},indent=2))

if __name__=="__main__":main()
