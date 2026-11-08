"""Operational narrative text windows are only source-page leads."""
import gzip,json
from compare_operational_narrative_sources import phrases,compare

def test_short_text_is_not_falsely_placed():
    assert phrases("Ituri, 100 cases.")==[]

def test_french_long_passage_produces_review_only_page_lead(tmp_path):
    paragraph="La coordination nationale a examine les nouvelles alertes provenant des zones de sante en Ituri"
    p=tmp_path/"pages.gz"
    with gzip.open(p,"wt") as f:
        f.write(json.dumps({"report_date":"2026-05-21","report_number":7,"source_sha256":"a"*64,
            "page":4,"text_sha256":"b"*64,"full_text":paragraph})+"\n")
    n=tmp_path/"n.gz"
    with gzip.open(n,"wt") as f:
        f.write(json.dumps({"date_iso":"2026-05-21","date_raw":"21-05-2026","language":"fr",
            "text_raw":paragraph,"upstream_pillar_label":"coordination",
            "source_git_commit":"a"*40,"source_csv_path":"a.csv",
            "source_csv_sha256":"b"*64,"source_csv_row":2,
            "geography_raw":"DRC","upstream_geographic_grain":"national"})+"\n")
    result=compare(n,p,tmp_path/"out")
    assert result["source_link_status_counts"]["LITERAL_PHRASE_WINDOW_LOCATED_VISUAL_QA_PENDING"]==1
    with gzip.open(tmp_path/"out/operational_narrative_source_leads.jsonl.gz","rt") as f:
        row=json.loads(f.readline())
    assert row["approved_for_interpretation"] is False
    assert row["source_page_leads"][0]["source_page"]==4
