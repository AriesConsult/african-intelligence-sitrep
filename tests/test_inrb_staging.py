"""Preserve INRB raw values, missingness, malformed dates, and provenance."""
from stage_inrb_series import decode_value,candidate_policy

def test_missing_is_never_zero():
 assert decode_value("ND")== (None,"NOT_REPORTED")
 assert decode_value("0")== (0,"NUMERIC_UNVERIFIED")
 assert decode_value("")==(None,"MISSING_OR_NOT_APPLICABLE")

def test_decimal_and_unparseable_values():
 assert decode_value("1 024")== (1024,"NUMERIC_UNVERIFIED")
 assert decode_value("12,5")== (12.5,"NUMERIC_UNVERIFIED")
 assert decode_value("unknown")[1]=="UNPARSEABLE"

def test_cumulative_derivation_not_assumed_direct():
 assert "CARRIED_FORWARD_OR_DERIVED" in candidate_policy("cumulative_confirmed_cases")


def test_tree_request_uses_github_token_only_for_api(tmp_path,monkeypatch):
 import json
 import requests
 from stage_inrb_series import stage
 monkeypatch.setenv('GH_TOKEN','test-token-123')
 registry=tmp_path/'registry.json'
 registry.write_text(json.dumps({'documents':{}}),encoding='utf-8')
 seen=[]
 class Response:
  def __init__(self, data):
   self._data=data
   self.content=b'nom,date,example'+bytes([10])+b'Test,2026-05-22,1'+bytes([10])
  def raise_for_status(self):pass
  def json(self):return self._data
 class Session:
  def mount(self,*args):pass
  def get(self,url,**kwargs):
   seen.append((url,kwargs))
   if 'api.github.com' in url:
    return Response({'tree':[{'type':'blob','path':'data/insp_sitrep/processed/insp_sitrep__example__daily.csv'}]})
   return Response({})
 monkeypatch.setattr(requests,'Session',Session)
 result=stage(registry,'a'*40,tmp_path/'out')
 assert result['metric_files']==1
 assert seen[0][1]['headers']['Authorization']=='Bearer test-token-123'
 assert 'headers' not in seen[1][1]
