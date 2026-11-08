#!/usr/bin/env python3
"""Render source-hash-verified PDF pages for unresolved 2026 BDBV decisions.

Each image is associated with the exact immutable archived PDF identity and a
list of review questions. This creates evidence, not human-approved figures.
"""
import argparse,csv,hashlib,io,json,re,zipfile
from collections import defaultdict,Counter
from pathlib import Path
import pymupdf

def add_target(targets,sha,page,issue):
    if not sha or not re.fullmatch(r"[a-f0-9]{64}",str(sha)):return
    try:page=int(page)
    except (TypeError,ValueError):return
    if page>=1:targets[(sha,page)].add(issue)

def build(archive,archive_index,decision_csv,ambiguity_jsonl,out,max_pages=750):
    idx=json.loads(Path(archive_index).read_text(encoding="utf-8"))
    by_sha={v["source_sha256"]:v for v in idx["archived"].values()}
    targets=defaultdict(set);counts=Counter()
    with Path(decision_csv).open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            if r["category"] not in ("NATIONAL","HEALTH_ZONE"):continue
            add_target(targets,r["source_pdf_sha256"],r["pdf_page"],
                f'{r["category"]}|{r["date"]}|{r["metric"]}|{r["geography"]}|{r["disposition"]}')
            # A missing page pointer is a source review lead on the cover, explicitly labelled.
            if not r.get("pdf_page") and r.get("source_pdf_sha256"):
                add_target(targets,r["source_pdf_sha256"],1,
                    f'UNLOCATED_NUMBER_COVER_LEAD_ONLY|{r["category"]}|{r["metric"]}')
    with Path(ambiguity_jsonl).open(encoding="utf-8") as f:
        for line in f:
            row=json.loads(line)
            for cand in row["candidate_rows"]:
                add_target(targets,cand["pdf_sha256"],cand["page"],
                    f'AMBIGUOUS|{row["metric_id"]}|{row["geography"]}|{row["diagnosis"]}|{cand["value"]}')
    if len(targets)>max_pages:raise ValueError("Source review packet exceeds explicit page safety cap")
    missing=[(sha,p) for sha,p in targets if sha not in by_sha]
    if missing:raise ValueError("Target source PDF not preserved in archive: "+repr(missing[:5]))
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    findings=[]
    with zipfile.ZipFile(archive) as originals,zipfile.ZipFile(out/"review_page_images.zip","w",compression=zipfile.ZIP_DEFLATED,compresslevel=5) as review:
        grouped=defaultdict(list)
        for (sha,page),questions in targets.items():
            grouped[sha].append((page,sorted(questions)))
        for sha,pages in sorted(grouped.items()):
            record=by_sha[sha]
            member=record["archive_member"]
            raw=originals.read(member)
            if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError("Original PDF hash mismatch "+member)
            with pymupdf.open(stream=raw,filetype="pdf") as pdf:
                for page_num,issues in sorted(pages):
                    if page_num>pdf.page_count:
                        raise ValueError(f"Review page {page_num} outside PDF {member} ({pdf.page_count} pages)")
                    image=pdf.load_page(page_num-1).get_pixmap(matrix=pymupdf.Matrix(1.65,1.65),alpha=False).tobytes("jpg",jpg_quality=87)
                    path=f'SitRep_{record["report_number"]:03d}_{sha[:12]}_page_{page_num:02d}.jpg'
                    review.writestr(path,image)
                    findings.append({"report_number":record["report_number"],"source_sha256":sha,
                        "original_archive_member":member,"source_report_date":record["report_date"],
                        "page":page_num,"image_member":path,
                        "render_sha256":hashlib.sha256(image).hexdigest(),
                        "review_questions":issues,"human_review_completed":False})
                    counts["pages_rendered"]+=1
        counts["source_pdfs"]=len(grouped)
    for x in findings:
        if not x["review_questions"]:raise ValueError("Page without issue provenance")
    (out/"review_page_manifest.json").write_text(json.dumps({
      "schema_version":"bdbv-original-page-review-pack-v1",
      "source_release_tag":"bdbv-sitrep-originals-42413796114",
      "images_zip_sha256":hashlib.sha256((out/"review_page_images.zip").read_bytes()).hexdigest(),
      "source_pdf_count":counts["source_pdfs"],"unique_review_pages":counts["pages_rendered"],
      "pages":findings,"status":"ORIGINAL_PDF_VISUAL_EVIDENCE_PREPARED_REVIEW_REQUIRED",
      "warning":"This ZIP is a visual audit packet, not a claim that PDF reading has been checked by a human."},
      ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in {"source_pdfs":counts["source_pdfs"],
       "unique_review_pages":counts["pages_rendered"],"status":"REVIEW_REQUIRED"}.items()},indent=2))
    return counts["pages_rendered"]

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--index",type=Path,default=Path("published/source_archive_index.json"))
    p.add_argument("--decisions",type=Path,required=True)
    p.add_argument("--ambiguities",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();build(a.archive,a.index,a.decisions,a.ambiguities,a.out)
