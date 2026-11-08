#!/usr/bin/env python3
"""OCR source recovery for three scanned 2026 INSP SitReps.

OCR is NEVER a certified table transcription or verified narrative section.
Retain page image evidence and word-level confidences for visual adjudication.
"""
import argparse,csv,gzip,hashlib,io,json,subprocess,zipfile
from pathlib import Path
from collections import Counter
import pymupdf

def digest(raw):return hashlib.sha256(raw).hexdigest()

def parse_tsv(raw):
    words=[]
    for row in csv.DictReader(io.StringIO(raw),delimiter="\t"):
        text=row.get("text","").strip()
        if not text:continue
        try:conf=float(row.get("conf","-1"))
        except ValueError:conf=-1
        words.append({"word":text,"confidence":conf,
            "left":int(row["left"]),"top":int(row["top"]),
            "width":int(row["width"]),"height":int(row["height"]),
            "block_num":row.get("block_num"),"par_num":row.get("par_num"),
            "line_num":row.get("line_num")})
    return words

def ocr_png(png,language="fra+eng"):
    cmd=["tesseract","stdin","stdout","-l",language,"--psm","3","tsv"]
    result=subprocess.run(cmd,input=png,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=150)
    if result.returncode:raise RuntimeError("Tesseract failed: "+result.stderr.decode(errors="replace")[:280])
    return result.stdout.decode("utf-8",errors="replace")

def recover(index_path,archive,output):
    index=json.loads(Path(index_path).read_text(encoding="utf-8"))
    records=index["source_records"]
    if len(records)!=3 or {r["report_number"] for r in records}!={7,8,9}:
        raise ValueError("Unexpected source index; review before OCR")
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    summary=Counter();report_rows=[]
    with zipfile.ZipFile(archive) as source, gzip.open(output/"scanned_page_ocr_candidates.jsonl.gz","wt",encoding="utf-8") as dest:
        for report in records:
            number=report["report_number"]
            name=f"SitRep_MVE_{number:03d}-2026.pdf"
            raw=source.read(name)
            if digest(raw)!=report["source_sha256"]:
                raise ValueError("Archived original source checksum mismatch for "+name)
            with pymupdf.open(stream=raw,filetype="pdf") as doc:
                if doc.page_count!=report["pdf_pages"]:raise ValueError("Original page count mismatch")
                for page_number,page in enumerate(doc,1):
                    image=page.get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False).tobytes("png")
                    tsv=ocr_png(image)
                    words=parse_tsv(tsv)
                    confidence=[w["confidence"] for w in words if w["confidence"]>=0]
                    score=round(sum(confidence)/len(confidence),2) if confidence else None
                    blocks={}
                    for w in words:
                        key=(w["block_num"],w["par_num"],w["line_num"])
                        blocks.setdefault(key,[]).append(w["word"])
                    lines=[" ".join(line) for line in blocks.values()]
                    text="\n".join(lines)
                    record={"report_number":number,"pdf_sha256":report["source_sha256"],"page":page_number,
                        "report_date_cover_review":report["report_date"],
                        "text":text,"text_sha256":digest(text.encode("utf-8")),
                        "word_count":len(words),"mean_word_confidence":score,
                        "ocr_word_boxes":words,"rendered_image_sha256":digest(image),
                        "ocr_engine":"tesseract_5_fra_eng_psm3_2x",
                        "status":"MACHINE_OCR_PENDING_VISUAL_LINE_AND_TABLE_REVIEW",
                        "approved_for_analysis":False}
                    dest.write(json.dumps(record,ensure_ascii=False)+"\n")
                    summary["pages"]+=1;summary["words"]+=len(words)
                    if score is None or score<65:summary["pages_low_confidence_or_empty"]+=1
            report_rows.append({"report_number":number,"source_pdf_sha256":report["source_sha256"],
                "pages":report["pdf_pages"],"status":"OCR_COMPLETED_UNVERIFIED"})
    result={"schema_version":"bdbv-scanned-ocr-review-v1",
        "status":"SCANNED_OCR_COMPLETED_VISUAL_VERIFICATION_PENDING",
        "reports":report_rows,"page_count":summary["pages"],
        "word_count":summary["words"],
        "pages_low_confidence_or_empty":summary["pages_low_confidence_or_empty"],
        "ocr_languages":["fra","eng"],
        "source_archive_release":index["release_url"],
        "caveats":["OCR text and numbers may be wrong; compare each table cell to the original PDF image.",
            "No OCR result is promoted as a validated cases/deaths observation.",
            "The source registry's 158 fully digitally extracted documents remains unchanged until formal re-audit."]}
    if summary["pages"]!=sum(x["pdf_pages"] for x in records):raise ValueError("Missing scanned pages")
    (output/"scanned_ocr_summary.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="reports"},indent=2))
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--index",type=Path,default=Path("published/scanned_source_index.json"))
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();recover(a.index,a.archive,a.out)
