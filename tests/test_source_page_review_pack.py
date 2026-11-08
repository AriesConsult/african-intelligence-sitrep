"""Target original-PDF page images retain SHA256 and never imply review approval."""
import csv,hashlib,json,zipfile
import fitz
from render_exception_source_pages import build

def test_visual_packet_hashes_pdf_and_image_and_lists_questions(tmp_path):
    doc=fitz.open();doc.new_page().insert_text((50,50),"ITURI REPORTED TOTAL 123")
    raw=doc.tobytes();sha=hashlib.sha256(raw).hexdigest()
    archive=tmp_path/"pdf.zip"
    with zipfile.ZipFile(archive,"w") as z:z.writestr("x.pdf",raw)
    idx=tmp_path/"index.json";idx.write_text(json.dumps({"archived":{"key":{"archive_member":"x.pdf",
        "report_number":169,"report_date":"2026-10-30","source_sha256":sha}}}))
    decision=tmp_path/"decision.csv"
    with decision.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["category","date","metric","geography","disposition",
            "source_pdf_sha256","pdf_page"])
        w.writeheader();w.writerow({"category":"NATIONAL","date":"2026-10-30",
            "metric":"national_cumulative_confirmed_cases","geography":"DRC",
            "disposition":"REVIEW_REQUIRED","source_pdf_sha256":sha,"pdf_page":1})
    ambiguous=tmp_path/"ambiguous.jsonl";ambiguous.write_text("")
    count=build(archive,idx,decision,ambiguous,tmp_path/"out")
    assert count==1
    j=json.loads((tmp_path/"out/review_page_manifest.json").read_text())
    assert j["status"].endswith("REVIEW_REQUIRED")
    assert j["pages"][0]["human_review_completed"] is False
    with zipfile.ZipFile(tmp_path/"out/review_page_images.zip") as z:
        assert z.read(j["pages"][0]["image_member"])[:2]==b"\xff\xd8"
