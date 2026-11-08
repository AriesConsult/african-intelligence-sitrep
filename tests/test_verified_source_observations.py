"""Only previously visually adjudicated source readings can be promoted as verbatim."""
import json, pytest
from build_verified_source_observations import verify

def test_mismatched_source_pdf_identity_is_rejected(tmp_path):
    cover=tmp_path/"cover.json"
    cover.write_text(json.dumps({"evidence":[{"report_number":169,"registry_sha256":"a"*64,
        "metrics":{"national_cumulative_confirmed_deaths":{"preferred_verbatim_pdf":5372}}}]}))
    registry=tmp_path/"reg.json"
    registry.write_text(json.dumps({"documents":{"169:other":{"report_number":169,"sha256":"b"*64}}}))
    table=tmp_path/"tab.json";table.write_text("{}")
    with pytest.raises(ValueError,match="identity mismatch"):
        verify(cover,registry,table,tmp_path/"out")
