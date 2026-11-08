"""Independent fixture checks for complete page extraction; no OCR claims."""
import hashlib
import json
import zipfile
from pathlib import Path

import pymupdf
from extract_full_pages import extract_one, verify_member


def synthetic_pdf(text="FIRST PAGE"):
    doc=pymupdf.open()
    page=doc.new_page()
    page.insert_text((65,80),text)
    data=doc.tobytes()
    doc.close()
    return data


def test_extract_one_retains_full_text_positions_and_page_counts():
    raw=synthetic_pdf("SOURCE PAGE VALIDATION")
    item={"report_number":5,"report_date":"2026-05-20","source_sha256":hashlib.sha256(raw).hexdigest()}
    result=extract_one(raw,item,1)
    assert result["page_count"]==1
    assert result["source_sha256"]==item["source_sha256"]
    assert "SOURCE PAGE VALIDATION" in result["pages"][0]["text_sorted"]
    assert result["pages"][0]["text_blocks"]
    assert result["pages"][0]["text_sha256"]==hashlib.sha256(result["pages"][0]["text_sorted"].encode()).hexdigest()


def test_page_count_mismatch_is_rejected():
    import pytest
    raw=synthetic_pdf()
    item={"report_number":5,"report_date":"2026-05-20","source_sha256":hashlib.sha256(raw).hexdigest()}
    with pytest.raises(ValueError,match="page-count"):
        extract_one(raw,item,2)


def test_member_sha_mismatch_is_rejected(tmp_path):
    import pytest
    raw=synthetic_pdf()
    sha="0"*64
    item={"report_number":5,"source_sha256":sha,"archive_member":f"SitRep_005_{sha[:12]}.pdf","pdf_bytes":len(raw)}
    path=tmp_path/"test.zip"
    with zipfile.ZipFile(path,"w") as z:z.writestr(item["archive_member"],raw)
    with zipfile.ZipFile(path) as z:
        with pytest.raises(ValueError,match="mismatch"):
            verify_member(z,item,{"documents":{f"005:{sha}":{"report_number":5}}})
