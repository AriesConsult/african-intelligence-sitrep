import gzip
import hashlib
import json
from pathlib import Path

from inventory_extracted_content import inventory

def test_all_pages_indexed_with_source_hash_and_unvalidated_topics(tmp_path):
    source_sha="a"*64
    registry={"documents":{"001:"+source_sha:{"report_number":1,"pages":2,"report_date":"2026-05-14"}}}
    registry_path=tmp_path/"registry.json"
    registry_path.write_text(json.dumps(registry),encoding="utf-8")
    extracted=tmp_path/"extracted"
    (extracted/"full_pages").mkdir(parents=True)
    pages=[]
    for no,text in enumerate(("Suivi des contacts en Ituri : 123.", "Laboratoire PCR."),1):
        pages.append({"page":no,"text_sorted":text,"text_sha256":hashlib.sha256(text.encode()).hexdigest(),
                      "text_blocks":[{"bbox":[0,0,100,50]}],"image_locations":[],"drawing_count":0})
    doc={"source_sha256":source_sha,"report_number":1,"pages":pages}
    path=extracted/"full_pages/001.json.gz"
    with gzip.open(path,"wt",encoding="utf-8") as out:json.dump(doc,out)
    audit={"records":[{"report_number":1,"source_sha256":source_sha,"extraction_file":"full_pages/001.json.gz",
                       "compressed_sha256":hashlib.sha256(path.read_bytes()).hexdigest()}]}
    (extracted/"page_extraction_audit.json").write_text(json.dumps(audit),encoding="utf-8")
    out=tmp_path/"output"
    result=inventory(extracted,registry_path,out)
    assert result["status"]=="ALL_REGISTERED_DOCUMENTS_INVENTORIED_REVIEW_REQUIRED"
    assert result["counters"]["pages"]==2
    assert result["reports"][0]["numeric_token_matches_unverified"]>0
    assert result["reports"][0]["status"].endswith("REVIEW_REQUIRED")
    assert (out/"content_availability_inventory.csv").exists()
