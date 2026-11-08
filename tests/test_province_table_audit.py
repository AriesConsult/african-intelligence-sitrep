"""Province audit cannot equate incomplete zone sums with verified totals."""
import json
from pathlib import Path
from audit_province_tables import audit

def test_incomplete_province_coverage_never_approved(tmp_path):
    sha="a"*64
    registry={"documents":{"010:"+sha:{"report_number":10,"report_date":"2026-05-24","sha256":sha}}}
    registry_path=tmp_path/"registry.json";registry_path.write_text(json.dumps(registry))
    tables=tmp_path/"published/tables";tables.mkdir(parents=True)
    snapshot={"source_sha256":sha,"tables":{
      "table_1":{"status":"REVIEW_REQUIRED","rows":[{"scope":"Ituri","cumulative_cases":100,
                 "cumulative_deaths":20,"source":{"page":2}}]},
      "table_2":{"status":"REVIEW_REQUIRED","province_totals":[{"province":"Ituri",
                 "cumulative_cases":100,"cumulative_deaths":20,"source":{"page":3}}],
                 "rows":[{"province":"Ituri","scope":"health_zone","health_zone":"Bunia",
                 "cumulative_cases":30,"cumulative_deaths":5}]}}}
    (tables/f"010_{sha[:12]}.json").write_text(json.dumps(snapshot))
    out=tmp_path/"out";result=audit(registry_path,tmp_path/"published",out)
    assert result["counts"]["REPORTED_PROVINCE_TOTALS_MATCH"]==2
    data=(out/"provincial_cells_review.csv").read_text()
    assert "sum_of_extracted_zones_NOT_PROVINCE_TOTAL" in data
    assert "False" in data
