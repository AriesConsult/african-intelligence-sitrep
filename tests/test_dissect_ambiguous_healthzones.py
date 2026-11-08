"""Ambiguous source-row labels must never auto-approve identical figures."""
import json
from dissect_ambiguous_healthzones import inspect

def test_ambiguous_distinct_source_cells_retained(tmp_path):
    sha="a"*64
    reg=tmp_path/"reg.json";reg.write_text(json.dumps({"documents":{"175:"+sha:{
        "report_number":175,"sha256":sha,"report_date":"2026-11-05"}}}))
    table_dir=tmp_path/"published/tables";table_dir.mkdir(parents=True)
    table={"report_number":175,"source_sha256":sha,"tables":{"table_2":{
       "status":"REVIEW_REQUIRED","rows":[
         {"health_zone":"Bunia","province":"Ituri","cumulative_cases":20,
          "source":{"page":2,"table_id":"t2","source_row":5}},
         {"health_zone":"Bunia","province":"Ituri","cumulative_cases":20,
          "source":{"page":3,"table_id":"t3","source_row":7}}]}}}
    (table_dir/f"175_{sha[:12]}.json").write_text(json.dumps(table))
    ledger=tmp_path/"ledger.jsonl";ledger.write_text(json.dumps({
        "date":"2026-11-05","metric_id":"cumulative_confirmed_cases","geography":"Bunia",
        "status":"AMBIGUOUS_MULTIPLE_PDF_ROWS","inrb_value_raw":"20","inrb_value_parsed":20})+"\n")
    result=inspect(reg,tmp_path/"published",ledger,tmp_path/"out")
    assert result["classifications"]["SAME_NUMERIC_VALUE_DISTINCT_SOURCE_ROWS"]==1
    row=json.loads((tmp_path/"out/ambiguous_healthzone_pdf_rows.jsonl").read_text())
    assert row["approved_for_analysis"] is False
    assert row["distinct_cells"]==2
