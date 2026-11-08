"""Historical assembly preserves ND, conflicting duplicates and retroactive changes."""
import gzip,json
from assemble_historical_series import assemble

def test_historical_assembly_never_converts_nd_or_cumulative_drop_to_incidence(tmp_path):
    staged=tmp_path/"staged";staged.mkdir()
    rows=[]
    def add(date,value,status="NUMERIC_UNVERIFIED",geo="Bunia",line=2):
        rows.append({"inrb_commit":"b"*40,"metric_id":"cumulative_confirmed_cases",
            "geography_raw":geo,"date_raw":date,"extra_columns_raw":{},
            "value_raw":str(value),"value_parsed":value if status=="NUMERIC_UNVERIFIED" else None,
            "value_status":status,"inrb_csv_path":"cases.csv","inrb_csv_sha256":"a"*64,
            "inrb_csv_row_number":line,"date_valid":True,"date_matched_registry_sources":[]})
    add("2026-05-20",9)
    add("2026-05-21",8)
    add("2026-05-22","ND","NOT_REPORTED")
    add("2026-05-23",10,line=5)
    add("2026-05-23",11,line=6)
    (staged/"inrb_staging_summary.json").write_text(json.dumps({
        "status":"INRB_SERIES_STAGED_NOT_PDF_VERIFIED",
        "inrb_commit":"b"*40,"counts":{"rows":len(rows)}}))
    with gzip.open(staged/"inrb_observation_candidates.jsonl.gz","wt",encoding="utf-8") as f:
        for r in rows:f.write(json.dumps(r)+"\n")
    out=tmp_path/"out"
    summary=assemble(staged,out)
    assert summary["source_rows"]==5
    assert summary["cumulative_decrease_flags"]==1
    assert summary["observations_by_status"]["EXPLICIT_ND"]==1
    assert summary["observations_by_status"]["CONFLICTING_DUPLICATE_SOURCE_ROWS"]==1
    assert summary["approved_for_analysis"]==0
    with gzip.open(out/"historical_curated_candidates.jsonl.gz","rt",encoding="utf-8") as f:
        candidates=[json.loads(x) for x in f]
    assert next(x for x in candidates if x["status"]=="EXPLICIT_ND")["value"] is None
    assert next(x for x in candidates if x["status"]=="CONFLICTING_DUPLICATE_SOURCE_ROWS")["value"] is None
