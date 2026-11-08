"""Revision keywords generate review leads, not automatic corrections."""
import csv,gzip,hashlib,json
from locate_explicit_historical_revisions import run

def test_same_page_revision_keyword_still_unapproved(tmp_path):
    dir=tmp_path/"full";(dir/"full_pages").mkdir(parents=True)
    text="Ituri: harmonisation et correction des chiffres cumulatifs rapportes."
    doc={"report_date":"2026-10-30","source_sha256":"a"*64,"report_number":169,
         "pages":[{"page":1,"text_sorted":text}]}
    path=dir/"full_pages/169.json.gz"
    with gzip.open(path,"wt") as fp:json.dump(doc,fp)
    (dir/"page_extraction_audit.json").write_text(json.dumps({"records":[{
      "report_number":169,"source_sha256":"a"*64,
      "compressed_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
      "extraction_file":"full_pages/169.json.gz"}]}))
    rev=tmp_path/"rev.csv"
    with rev.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["metric_id","geography_raw","previous_date",
                          "current_date","previous_value","current_value","delta"])
        w.writeheader();w.writerow({"metric_id":"cumulative_confirmed_deaths",
          "geography_raw":"Ituri","previous_date":"2026-10-29","current_date":"2026-10-30",
          "previous_value":100,"current_value":90,"delta":-10})
    result=run(rev,dir,tmp_path/"out")
    assert result["classification_counts"]["REVISION_TERM_AND_ZONE_ON_SAME_REPORT_PAGE_NOT_CAUSALLY_LINKED"]==1
    item=json.loads((tmp_path/"out/cumulative_revision_source_page_leads.jsonl").read_text())
    assert item["approved_as_documented_revision"] is False
