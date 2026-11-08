#!/usr/bin/env python3
"""Pin and stage every INRB public-health-response narrative CSV with raw provenance.

No headline event/section identity is inferred from upstream pillar alone.
Dates are explicitly DD-MM-YYYY, source wording is retained unchanged.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,io,json,re
from datetime import datetime
from pathlib import Path
from collections import Counter,defaultdict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

REPO="INRB-UMIE/BDBV2026-Data"
PREFIX="data/public_health_response/processed/"
RX=re.compile(r"^"+PREFIX+r"public_health_response__(.+)_(fr|en)__daily\.csv$")

def parse_date(raw):
    try:return datetime.strptime(raw.strip(),"%d-%m-%Y").date().isoformat()
    except (ValueError,AttributeError):return None

def category(filename):
    m=RX.match(filename)
    if not m:raise ValueError("Unexpected narrative filename "+filename)
    body,lang=m.group(1),m.group(2)
    if body.startswith("national_"):grain,topic="national",body[len("national_"):]
    elif body.startswith("provincial_"):grain,topic="province",body[len("provincial_"):]
    else:grain,topic="health_zone",body
    return grain,topic,lang

def stage(registry_path,commit,out):
    if not re.fullmatch(r"[a-f0-9]{40}",commit):raise ValueError("Pin upstream full SHA")
    reg=json.loads(Path(registry_path).read_text(encoding="utf-8"))
    known_dates={x["report_date"] for x in reg["documents"].values()}
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    sources=out/"original_csv";sources.mkdir(exist_ok=True)
    s=requests.Session()
    retry=Retry(total=5,connect=5,read=5,backoff_factor=2,
                status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
    s.mount("https://",HTTPAdapter(max_retries=retry))
    tree=s.get(f"https://api.github.com/repos/{REPO}/git/trees/{commit}?recursive=1",timeout=90)
    tree.raise_for_status();tree=tree.json()
    if tree.get("truncated"):raise ValueError("Upstream Git tree incomplete")
    paths=sorted(x["path"] for x in tree["tree"] if x.get("type")=="blob" and RX.match(x["path"]))
    if not paths:raise ValueError("Upstream narrative files unavailable")
    counts=Counter();by_file=[];exceptions=[];by_topic=defaultdict(Counter)
    with gzip.open(out/"inrb_operational_narrative_candidates.jsonl.gz","wt",encoding="utf-8") as dest:
        for path in paths:
            grain,topic,language=category(path)
            url=f"https://raw.githubusercontent.com/{REPO}/{commit}/{path}"
            response=s.get(url,timeout=120);response.raise_for_status();raw=response.content
            digest=hashlib.sha256(raw).hexdigest()
            (sources/Path(path).name).write_bytes(raw)
            table=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
            if not table.fieldnames or not {"nom","date"}.issubset(table.fieldnames):
                raise ValueError("Missing nom/date column "+path)
            text_columns=[h for h in table.fieldnames if h not in ("nom","date")]
            if len(text_columns)!=1:raise ValueError("Ambiguous response narrative value column "+path)
            column=text_columns[0]
            n=0;present_dates=set();unmatched=0
            for lineno,row in enumerate(table,2):
                raw_date=row["date"];iso=parse_date(raw_date)
                if iso is None:exceptions.append({"csv_path":path,"row":lineno,"issue":"INVALID_SOURCE_DD_MM_YYYY_DATE","raw_date":raw_date})
                body=row.get(column) or ""
                if not body.strip():counts["empty_narrative_text_rows"]+=1
                if iso and iso not in known_dates:unmatched+=1
                if iso:present_dates.add(iso)
                dest.write(json.dumps({"source_repo":REPO,"source_git_commit":commit,
                    "source_csv_path":path,"source_csv_sha256":digest,"source_csv_row":lineno,
                    "source_text_column":column,"upstream_pillar_label":topic,
                    "upstream_geographic_grain":grain,"language":language,
                    "geography_raw":row["nom"],"date_raw":raw_date,
                    "date_iso":iso,"text_raw":body,"text_chars":len(body),
                    "same_date_pdf_registered":iso in known_dates if iso else False,
                    "source_pdf_page_verified":False,"pillar_assignment_verified":False,
                    "approved_for_interpretation":False},ensure_ascii=False)+"\n")
                n+=1;counts["rows"]+=1;by_topic[(topic,grain,language)]["rows"]+=1
            by_file.append({"path":path,"sha256":digest,"pillar_label":topic,
                "grain":grain,"language":language,"rows":n,
                "different_date_without_registry_pdf":unmatched,
                "distinct_reporting_dates":len(present_dates)})
    summary={"schema_version":"bdbv-inrb-operational-narratives-v1",
        "status":"PINNED_OPERATIONAL_NARRATIVES_STAGED_NOT_PDF_VERIFIED",
        "upstream_commit":commit,"files":len(paths),
        "rows":counts["rows"],"empty_text_rows":counts["empty_narrative_text_rows"],
        "source_dates_not_always_in_PDF_registry":sum(x["different_date_without_registry_pdf"] for x in by_file),
        "source_input_exceptions":exceptions,
        "source_file_inventory":by_file,
        "warning":["Upstream French and English translations are not independent accounts.",
                   "Operational pillar assignment is supplied metadata and may mix topics.",
                   "Date presence does not establish the original PDF page/source section.",
                   "No narrative event or causal assertion is automatically approved."]}
    (out/"inrb_operational_narrative_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="source_file_inventory"},indent=2))
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--registry",type=Path,default=Path("state/registry.json"))
    p.add_argument("--inrb-commit",required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();stage(a.registry,a.inrb_commit,a.out)
