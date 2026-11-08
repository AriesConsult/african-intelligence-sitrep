#!/usr/bin/env python3
"""Inspect curated French narrative passage overlap with source PDF full-page text.

A detected literal phrase is a *page locator*, not proof of complete or exact
manual INRB transcription. Lack of overlap is not proof of missing reporting.
"""
import argparse,gzip,json,re,unicodedata
from pathlib import Path
from collections import Counter,defaultdict

def norm(text):
    s="".join(x for x in unicodedata.normalize("NFKD",str(text or "").lower())
              if not unicodedata.combining(x))
    return re.sub(r"[^a-z0-9]+"," ",s).strip()
def phrases(text):
    words=norm(text).split()
    if len(words)<10:return [] # Too short for useful low-false-match snippet
    span=12
    if len(words)<span:return [" ".join(words)]
    locations=sorted(set((0,max(0,(len(words)-span)//2),len(words)-span)))
    return [" ".join(words[i:i+span]) for i in locations]

def compare(narratives,sourcepages,out):
    pages=defaultdict(list)
    with gzip.open(sourcepages,"rt",encoding="utf-8") as f:
        for line in f:
            page=json.loads(line)
            pages[page["report_date"]].append({"report_number":page["report_number"],
                "pdf_sha256":page["source_sha256"],"page":page["page"],
                "source_page_text_sha256":page["text_sha256"],
                "normalized_text":norm(page["full_text"])})
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    counts=Counter();by_pillar=defaultdict(Counter)
    with gzip.open(narratives,"rt",encoding="utf-8") as inp,gzip.open(out/"operational_narrative_source_leads.jsonl.gz","wt",encoding="utf-8") as dest:
        for line in inp:
            item=json.loads(line)
            date=item["date_iso"]
            if not date:status="UPSTREAM_DATE_INVALID"
            elif item["language"]=="en":status="EN_TRANSLATION_NOT_VERBATIM_PDF_COMPARABLE"
            elif not item["text_raw"].strip():status="EMPTY_UPSTREAM_SOURCE_TEXT"
            elif date not in pages:status="NO_SAME_DATE_ORIGINAL_PDF_SOURCE"
            else:
                snippets=phrases(item["text_raw"])
                if not snippets:status="TOO_SHORT_FOR_RELIABLE_LITERAL_LOCATOR"
                else:status="NO_LITERAL_TEXT_WINDOW_FOUND_REVIEW_REQUIRED"
            hits=[]
            if date and item["language"]=="fr" and status=="NO_LITERAL_TEXT_WINDOW_FOUND_REVIEW_REQUIRED":
                for pg in pages[date]:
                    matched=[idx for idx,snippet in enumerate(snippets) if snippet in pg["normalized_text"]]
                    if matched:
                        hits.append({"report_number":pg["report_number"],
                            "source_pdf_sha256":pg["pdf_sha256"],
                            "source_page":pg["page"],"original_text_sha256":pg["source_page_text_sha256"],
                            "matched_phrase_window_indices":matched})
                if hits:status="LITERAL_PHRASE_WINDOW_LOCATED_VISUAL_QA_PENDING"
            counts[status]+=1
            by_pillar[item["upstream_pillar_label"]][status]+=1
            dest.write(json.dumps({"source_git_commit":item["source_git_commit"],
                "source_csv_path":item["source_csv_path"],
                "source_csv_sha256":item["source_csv_sha256"],
                "source_csv_row":item["source_csv_row"],"language":item["language"],
                "date_raw":item["date_raw"],"date_iso":date,
                "geography_raw":item["geography_raw"],
                "geographic_grain":item["upstream_geographic_grain"],
                "pillar_label_unverified":item["upstream_pillar_label"],
                "match_status":status,"source_page_leads":hits,
                "excerpt_chars":len(item["text_raw"]),"approved_for_interpretation":False},ensure_ascii=False)+"\n")
    result={"schema_version":"bdbv-operational-narrative-source-comparison-v1",
        "status":"LITERAL_LOCATORS_ONLY_SEMANTIC_COMPLETENESS_PENDING",
        "rows_evaluated":sum(counts.values()),
        "source_link_status_counts":dict(counts),
        "pillars_with_source_link_counts":{k:dict(v) for k,v in sorted(by_pillar.items())},
        "limitations":[
            "English translations are NOT independently matched against French source PDFs.",
            "Failure to find literal wording is not evidence of missing content: INRB may paraphrase or edit text.",
            "A matching 12-word phrase identifies candidate source pages but does not verify full section completeness or classification.",
            "All reporting dates and source labels are preserved exactly; none are silently corrected or promoted to publication."]}
    (out/"operational_narrative_source_comparison_summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="pillars_with_source_link_counts"},indent=2))
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--inrb-narratives",type=Path,required=True)
    p.add_argument("--pdf-pages",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();compare(a.inrb_narratives,a.pdf_pages,a.out)
