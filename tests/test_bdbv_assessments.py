import datetime as dt
import json

import pytest

from build_bdbv_assessments import make_packs, model_draft, load


def observation(day, cases, deaths, quality='historical_qualified'):
    return {'date':day,'cases':cases,'deaths':deaths,'source_quality':quality,
        'source_commit':'frozen','original_sitrep_number':100,
        'original_source_url':'https://example.org/report.pdf',
        'follow_up_pct':None,'narrative_source_excerpts':[]}


def test_weekly_and_monthly_derive_from_daily_and_preserve_coverage():
    rows=[observation('2026-10-26',100,50),
          observation('2026-10-28',108,51),
          observation('2026-11-01',112,52),
          observation('2026-11-02',114,54,'new_inrb_unverified'),
          observation('2026-11-06',135,61,'new_inrb_unverified')]
    weekly,monthly=make_packs(rows,dt.date(2026,11,9))
    assert weekly[-1]['start']=='2026-11-02'
    assert weekly[-1]['end']=='2026-11-08'
    assert weekly[-1]['coverage']['observed_days']==2
    assert '2026-11-03' in weekly[-1]['coverage']['missing_dates']
    assert weekly[-1]['reported_snapshots']['net_reported_changes_not_incidence'] is None
    october=[p for p in monthly if p['start']=='2026-10-01'][0]
    assert october['end']=='2026-10-31'
    assert october['coverage']['observed_days']==2
    assert october['iso_week_summaries'][0]['iso_week_start']=='2026-10-26'
    assert october['monthly_snapshots']['net_reported_changes_not_incidence']['cases_net_reported_change']==8
    assert all(p['end']!='2026-11-30' for p in monthly)


def test_evidence_file_rejects_duplicate_dates_and_wrong_version(tmp_path):
    path=tmp_path/'input.json'
    rows=[observation('2026-10-26',100,50)]
    path.write_text(json.dumps({'schema_version':'unknown','days':rows}))
    with pytest.raises(ValueError,match='Unknown evidence pack'):
        load(path)
    path.write_text(json.dumps({'schema_version':'ai-bdbv-analytical-evidence-v1','days':rows+rows}))
    with pytest.raises(ValueError,match='Repeated date'):
        load(path)


def test_model_output_needs_valid_citations_and_remains_unpublished(monkeypatch):
    pack={'frequency':'weekly','start':'2026-11-02','end':'2026-11-08',
        'daily_observations':[observation('2026-11-02',114,54)]}
    class FakeResponse:
        def raise_for_status(self):pass
        def json(self):
            return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps({
                'headline':'A provisional snapshot',
                'assessment':'This period contains limited observations.',
                'signals':[{'finding':'A source snapshot was reported.',
                    'evidence_dates':['2026-11-02'],'confidence':'low'}],
                'data_limitations':['Only one reported day.'],'editorial_checks':['Verify source.']})}}]}
    monkeypatch.setattr('build_bdbv_assessments.requests.post',lambda *args,**kwargs:FakeResponse())
    draft=model_draft(pack,'fake-key','test-model')
    assert draft['status']=='REVIEW_REQUIRED'
    assert draft['auto_publish'] is False
    assert draft['draft']['signals'][0]['evidence_dates']==['2026-11-02']
