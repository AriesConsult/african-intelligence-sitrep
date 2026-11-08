"""Scanned OCR narrative integration must detect missing pages and wrong hashes."""
import gzip,hashlib,json,pytest
from integrate_scanned_narratives import integrate

def test_fails_when_scanned_page_count_is_incomplete(tmp_path):
    sha="a"*64
    index=tmp_path/"index.json";index.write_text(json.dumps({"source_records":[
        {"report_number":7,"pdf_pages":2,"source_sha256":sha,"report_date":"2026-05-21"},
        {"report_number":8,"pdf_pages":1,"source_sha256":"b"*64,"report_date":"2026-05-22"},
        {"report_number":9,"pdf_pages":1,"source_sha256":"c"*64,"report_date":"2026-05-23"}]}))
    summary=tmp_path/"sum.json";summary.write_text('{"page_count":37}')
    txt="test page"
    entry={"report_number":7,"pdf_sha256":sha,"text":txt,
           "text_sha256":hashlib.sha256(txt.encode()).hexdigest(),
           "page":1,"word_count":2}
    ocr=tmp_path/"ocr.gz"
    with gzip.open(ocr,"wt") as f:f.write(json.dumps(entry)+"\n")
    with pytest.raises(ValueError,match="Expected three scanned reports"):
        integrate(ocr,index,summary,tmp_path/"out")
