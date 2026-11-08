"""Historical declines cannot be labelled verified revisions without source evidence."""
import csv,json
from triage_historical_acceptance import audit_revisions
def test_cumulative_decline_is_an_exception_not_negative_incidence(tmp_path):
    csvpath=tmp_path/"declines.csv"
    with csvpath.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["metric_id","geography_raw","previous_date","current_date","previous_value","current_value"])
        w.writeheader();w.writerow({"metric_id":"cumulative_confirmed_deaths","geography_raw":"Ituri",
              "previous_date":"2026-09-10","current_date":"2026-09-11","previous_value":200,"current_value":194})
    out=tmp_path/"out";out.mkdir()
    result=audit_revisions(csvpath,out)
    assert result["cases"]==1
    rows=list(csv.DictReader((out/"cumulative_revision_adjudication.csv").open()))
    assert rows[0]["adjudication"]=="UNRESOLVED"
    assert rows[0]["calculated_delta"]=="-6"
    assert rows[0]["does_not_imply_negative_incidence"]=="True"
