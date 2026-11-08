#!/usr/bin/env python3
"""Quarantine and permanently preserve INRB scanned SitReps 007–009.

Only visually reviewed cover identities are accepted; no OCR, extracted tables,
or national banner numbers are silently promoted into the analytical feed.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import pymupdf
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

REPO="INRB-UMIE/BDBV2026-Data"
COMMIT="c00b8843e6ebae8f0cd846bc43cb564a3893bfd9"
SOURCES={
 7:{"sha":"db9a6efa6cc73d9d229409ac3009b74499f24f7c6633321d2a83f14cda4a8079",
    "pages":12,"report_date":"2026-05-21","publication_date":"2026-05-22"},
 8:{"sha":"ac11fd6fe024375deef47e3d7070573d61db03bf2b3fe30ea5b4f207886b7d49",
    "pages":12,"report_date":"2026-05-22","publication_date":"2026-05-23"},
 9:{"sha":"a13ff30b3cb5363fffab1197a971a71f2c205748583d3d56c9bc384a09726440",
    "pages":13,"report_date":"2026-05-23","publication_date":"2026-05-24"}
}
def digest(raw):
 return hashlib.sha256(raw).hexdigest()

def collect(output,session=None,fetch_bytes=None):
 output.mkdir(parents=True,exist_ok=True)
 s=session or requests.Session()
 if session is None:
  retry=Retry(total=4,read=4,connect=4,backoff_factor=2,status_forcelist=[429,500,502,503,504])
  s.mount("https://",HTTPAdapter(max_retries=retry))
 archive=output/"scanned_sitrep_originals.zip"
 preview=output/"scanned_sitrep_page_renders.zip"
 records=[];pages_total=0
 with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z,zipfile.ZipFile(preview,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=5) as rendered:
  for number,expected in SOURCES.items():
   filename=f"SitRep_MVE_{number:03d}-2026.pdf"
   url=f"https://media.githubusercontent.com/media/{REPO}/{COMMIT}/data/insp_sitrep/raw/{filename}"
   if fetch_bytes is None:
    response=s.get(url,timeout=180);response.raise_for_status();raw=response.content
   else:raw=fetch_bytes(number,url)
   if not raw.startswith(b"%PDF-") or digest(raw)!=expected["sha"]:
    raise ValueError(f"SitRep {number}: unexpected source bytes/SHA-256")
   with pymupdf.open(stream=raw,filetype="pdf") as pdf:
    if pdf.is_encrypted or pdf.page_count!=expected["pages"]:
     raise ValueError(f"SitRep {number}: unexpected PDF page count or encryption")
    page_records=[]
    for idx,page in enumerate(pdf):
     page_name=f"SitRep_{number:03d}_page_{idx+1:02d}.png"
     rendered_bytes=page.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2),alpha=False).tobytes("png")
     rendered.writestr(page_name,rendered_bytes)
     text=page.get_text("text",sort=True)
     page_records.append({"page":idx+1,"render_archive_member":page_name,
                          "page_render_sha256":digest(rendered_bytes),
                          "extractable_text_characters":len(text),
                          "ocr_status":"NOT_ATTEMPTED"})
   z.writestr(filename,raw)
   pages_total+=len(page_records)
   records.append({"report_number":number,"source_sha256":expected["sha"],
      "source_git_commit":COMMIT,"source_url":url,"archive_member":filename,
      "report_date_cover_review":expected["report_date"],
      "publication_date_cover_review":expected["publication_date"],
      "pdf_pages":len(page_records),"pdf_bytes":len(raw),
      "source_identity_status":"INRB_HOSTED_COVER_VISUALLY_REVIEWED",
      "transcription_status":"SCANNED_REQUIRES_PAGE_TABLE_REVIEW",
      "approved_for_analysis":False,"pages":page_records})
 result={"schema_version":"bdbv-scanned-source-quarantine-v1",
    "created_at":datetime.now(timezone.utc).isoformat(),
    "upstream_repository":REPO,"upstream_commit_sha":COMMIT,
    "status":"THREE_SCANNED_ORIGINALS_PRESERVED_EXTRACTION_PENDING",
    "reports":len(records),"pages":pages_total,"documents":records,
    "policy":"Source identities and full-page images archived; not yet incorporated into the machine-validated 158-SitRep analytical registry. No OCR or verified cell data."}
 (output/"scanned_source_manifest.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 result["archive_sha256"]=digest(archive.read_bytes())
 result["page_render_archive_sha256"]=digest(preview.read_bytes())
 print(json.dumps({k:v for k,v in result.items() if k!="documents"},indent=2))
 return result

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--out",type=Path,required=True)
 args=p.parse_args()
 collect(args.out)
