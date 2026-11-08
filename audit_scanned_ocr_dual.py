#!/usr/bin/env python3
"""Independent-layout OCR check for scanned SitReps 007-009.

Compares Tesseract PSM 3 vs PSM 6 on exact source-PDF image bytes.
Agreement between two OCR layouts is NOT visual confirmation of an original
numeric table cell; it only prioritizes manual source inspection.
"""
import argparse,gzip,hashlib,json,re,subprocess,zipfile
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
import pymupdf
from recover_scanned_sitreps_ocr import parse_tsv

def numeric_tokens(text):
    return re.findall(r"(?<!\w)\d+(?:[.,]\d+)*(?!\w)",text)
def normalized(text):
    return " ".join(re.findall(r"[a-zà-ÿ0-9]+",str(text).lower()))
def compare_text(first,second):
    a=numeric_tokens(first);b=numeric_tokens(second)
    similarity=round(SequenceMatcher(None,normalized(first),normalized(second),autojunk=False).ratio(),4)
    return {"numeric_tokens_psm3":a,"numeric_tokens_psm6":b,
        "numeric_token_sequences_identical":a==b,
        "normalized_text_similarity":similarity,
        "numerically_agreeing_token_count":len(a) if a==b else 0}
def ocr_second(png):
    p=subprocess.run(["tesseract","stdin","stdout","-l","fra+eng","--psm","6","tsv"],
       input=png,capture_output=True,timeout=150)
    if p.returncode:raise RuntimeError("Second OCR engine layout failed")
    words=parse_tsv(p.stdout.decode("utf-8",errors="replace"))
    lines={}
    for w in words:
        key=(w["block_num"],w["par_num"],w["line_num"])
        lines.setdefault(key,[]).append(w["word"])
    return "\n".join(" ".join(words) for words in lines.values())

def audit(archive,index_path,original_ocr,out):
    index=json.loads(Path(index_path).read_text(encoding="utf-8"))
    sources={r["report_number"]:r for r in index["source_records"]}
    original={}
    with gzip.open(original_ocr,"rt",encoding="utf-8") as f:
        for line in f:
            row=json.loads(line)
            key=(row["report_number"],row["page"])
            if key in original:raise ValueError("Duplicate first OCR page")
            original[key]=row
    counts=Counter();rows=[]
    with zipfile.ZipFile(archive) as z:
        for num,source in sorted(sources.items()):
            raw=z.read(f"SitRep_MVE_{num:03d}-2026.pdf")
            if hashlib.sha256(raw).hexdigest()!=source["source_sha256"]:
                raise ValueError("Source original hash mismatched")
            with pymupdf.open(stream=raw,filetype="pdf") as pdf:
                if len(pdf)!=source["pdf_pages"]:raise ValueError("Scanned source page count mismatch")
                for i,page in enumerate(pdf,1):
                    key=(num,i)
                    if key not in original:raise ValueError("Missing first OCR page")
                    png=page.get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False).tobytes("png")
                    first=original[key]
                    if first["rendered_image_sha256"]!=hashlib.sha256(png).hexdigest():
                        raise ValueError("First and second OCR source images differ")
                    second=ocr_second(png)
                    diff=compare_text(first["text"],second)
                    if not diff["numeric_tokens_psm3"] and not diff["numeric_tokens_psm6"]:
                        klass="NO_NUMBER_DETECTED_IN_EITHER_OCR"
                    elif diff["numeric_token_sequences_identical"] and diff["normalized_text_similarity"]>=0.86:
                        klass="DUAL_OCR_NUMERIC_AND_TEXT_CONCORDANT_VISUAL_REVIEW_STILL_REQUIRED"
                    elif diff["numeric_token_sequences_identical"]:
                        klass="DUAL_OCR_NUMBERS_AGREE_TEXT_ORDER_DISAGREES"
                    else:klass="DUAL_OCR_NUMERIC_DISAGREEMENT_VISUAL_REVIEW_PRIORITY"
                    counts[klass]+=1
                    rows.append({"report_number":num,"page":i,"source_pdf_sha256":source["source_sha256"],
                       "psm3_text_sha256":first["text_sha256"],
                       "psm6_text_sha256":hashlib.sha256(second.encode()).hexdigest(),
                       "diagnosis":klass,**diff,"approved_for_numerical_analysis":False})
    if len(rows)!=37:raise ValueError("Scanned original OCR comparison incomplete")
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with (out/"scanned_dual_ocr_page_checks.jsonl").open("w",encoding="utf-8") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False)+"\n")
    summary={"schema_version":"bdbv-dual-ocr-page-review-v1",
      "status":"DUAL_OCR_COMPLETED_NUMERICAL_PAGE_FIDELITY_NOT_CERTIFIED",
      "pages":len(rows),"classification_counts":dict(counts),
      "method":"Tesseract French+English 2x: PSM 3 vs PSM 6; token ordering and text similarity",
      "limitations":["Same OCR engine with two page-layout modes is not independent human transcription.",
        "Matching OCR token lists may consistently omit or misread a digit.",
        "Numeric discordances, tables, dates and narrative headings require original-page visual verification."]}
    (out/"scanned_dual_ocr_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2));return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--index",type=Path,default=Path("published/scanned_source_index.json"))
    p.add_argument("--first-ocr",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();audit(a.archive,a.index,a.first_ocr,a.out)
