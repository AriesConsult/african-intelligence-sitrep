import json
from resolve_zone_numerical_invariants import reconcile

def test_numeric_consensus_never_certifies_source_row(tmp_path):
    rows=[]
    for i in range(174):
        a={"pdf_sha256":"a"*64,"page":2,"table_id":"p2-t1","source_row":1,
           "value":5,"province":"Ituri"}
        b={"pdf_sha256":"a"*64,"page":2,"table_id":"p2-t1","source_row":2,
           "value":5 if i<113 else 7,"province":"Ituri" if i<172 else "Nord-Kivu"}
        rows.append({"date":"2026-08-08","metric_id":"cumulative_confirmed_cases",
                     "geography":f"Zone{i}","candidate_rows":[a,b],"inrb_value_raw":"5"})
    f=tmp_path/"source.jsonl";f.write_text("\n".join(json.dumps(x) for x in rows)+"\n")
    summary=reconcile(f,tmp_path/"out")
    assert summary["numeric_consensus_candidates"]==113
    assert summary["numerical_or_geographic_ambiguities_remaining"]==61
    assert summary["source_row_identity_still_unverified"]==174
    assert summary["approved_for_analysis"]==0
