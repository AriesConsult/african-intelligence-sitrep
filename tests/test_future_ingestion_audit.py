"""Future sources never silently change the historical source identity set."""
import json
import pytest
from audit_future_ingestion import audit

def test_detects_new_pdf_and_does_not_approve_it(tmp_path):
    old="a"*64;new="b"*64
    freeze=tmp_path/"freeze.json";freeze.write_text(json.dumps({
        "registered_source_hashes":[{"report_number":175,"sha256":old}]}))
    reg=tmp_path/"registry.json";reg.write_text(json.dumps({"documents":{
      "175:"+old:{"report_number":175,"sha256":old,"report_date":"2026-11-05"},
      "176:"+new:{"report_number":176,"sha256":new,"report_date":"2026-11-06",
          "source_url":"https://insp.cd/test.pdf"}}}))
    table=tmp_path/"table.json";table.write_text('{"reports":[]}')
    nar=tmp_path/"nar.json";nar.write_text('{"reports":[]}')
    scan=tmp_path/"scan.json";scan.write_text('{"source_records":[]}')
    result=audit(freeze,reg,table,nar,scan,tmp_path/"out")
    assert result["status"]=="REVIEW_NEW_SOURCE_REVISIONS"
    assert result["new_or_revised_source_hashes"]==1
    assert result["changes"][0]["approved_in_historical_freeze"] is False

def test_freeze_cannot_lose_source(tmp_path):
    freeze=tmp_path/"freeze.json";freeze.write_text(json.dumps({"registered_source_hashes":[
      {"report_number":1,"sha256":"a"*64}]}))
    args=[]
    for filename,body in [("reg",{"documents":{}}),("table",{"reports":[]}),
                          ("nar",{"reports":[]}),("scan",{"source_records":[]})]:
        p=tmp_path/(filename+".json");p.write_text(json.dumps(body));args.append(p)
    with pytest.raises(ValueError,match="historical source identity missing"):
        audit(freeze,*args,tmp_path/"out")
