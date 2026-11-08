"""Cumulative decline rebound is diagnostic only, not a corrected incidence."""
import csv,gzip,json
from diagnose_cumulative_declines import diagnose

def test_drop_rebounds_and_no_values_approved(tmp_path):
    rows=[{"metric_id":"cumulative_confirmed_cases","geography_raw":"Bunia",
           "extra_columns_raw":{},"date":f"2026-05-{day:02d}",
           "status":"SINGLE_SOURCE_NUMERIC_CANDIDATE","value":value}
          for day,value in [(20,20),(21,18),(22,21),(23,22)]]
    source=tmp_path/"source.gz"
    with gzip.open(source,"wt") as f:
        for row in rows:f.write(json.dumps(row)+"\n")
    flags=tmp_path/"flags.csv"
    with flags.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["metric_id","geography_raw","previous_date","previous_value",
                     "current_date","current_value","delta"]);w.writeheader()
        w.writerow({"metric_id":"cumulative_confirmed_cases","geography_raw":"Bunia",
            "previous_date":"2026-05-20","previous_value":"20",
            "current_date":"2026-05-21","current_value":"18","delta":"-2"})
    reg=tmp_path/"reg.json";reg.write_text('{"documents":{}}')
    out=tmp_path/"out";result=diagnose(source,flags,reg,out)
    assert result["classification_counts"]["EARLY_REBOUND_TO_PRIOR_CUMULATIVE_LEVEL"]==1
    row=json.loads((out/"cumulative_decline_followup.jsonl").read_text())
    assert row["explanation_confirmed_in_original_pdf"] is False
    assert row["accepted_revised_incidence"] is False
