import csv,json
from pathlib import Path
from generate_bdbv_bulletins import build,aggregate,FROZEN

def test_qualified_bulletin_excludes_restricted_and_does_not_infer_incidence(tmp_path):
    accepted=tmp_path/'accepted.csv'
    with accepted.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['date','metric_id','geography_raw','curated_value',
              'curated_revision_commit','acceptance_tier','curated_value_eligible_for_qualified_descriptive_use'])
        w.writeheader()
        for day,cases,deaths in [('2026-05-14',8,4),('2026-05-18',33,4),('2026-05-20',64,6)]:
            for key,value,geography in [('national_cumulative_confirmed_cases',cases,'DRC'),
                      ('national_cumulative_confirmed_deaths',deaths,'DRC'),
                      ('contacts_seen',7,'Bunia')]:
                w.writerow({'date':day,'metric_id':key,'geography_raw':geography,
                   'curated_value':value,'curated_revision_commit':FROZEN,
                   'acceptance_tier':'C_PINNED_CURATED_INRB_ONLY',
                   'curated_value_eligible_for_qualified_descriptive_use':'TRUE'})
        w.writerow({'date':'2026-05-21','metric_id':'contacts_seen',
            'geography_raw':'Bunia','curated_value':999,'curated_revision_commit':FROZEN,
            'acceptance_tier':'RESTRICTED_EVIDENCE_ONLY',
            'curated_value_eligible_for_qualified_descriptive_use':'FALSE'})
    result=build(accepted,tmp_path/'output')
    assert result['edition_counts']['daily']==3
    public=tmp_path/'output/bdvd2026/assets/data'
    contacts=json.loads((public/'contact_tracing_public.json').read_text())
    assert contacts['days']['2026-05-18']['contacts_seen']['reported_sum']==7
    assert '2026-05-21' not in contacts['days']
    weekly=json.loads((public/'weekly_national_public.json').read_text())
    assert 'not epi onset incidence' in weekly['note']
    catalog=json.loads((public/'bulletins_public.json').read_text())
    assert catalog['publication_mode']=='automated_unreviewed_no_ai'
    assert len(catalog['bulletins'])==result['edition_counts']['daily']+result['edition_counts']['weekly']+result['edition_counts']['monthly']

def test_zone_aggregation_is_not_a_followup_percentage():
    nat,contacts=aggregate([dict(day='2026-06-01',metric='contacts_seen',
                                  geo='Bunia',value=12,kind='historical_qualified')])
    assert nat=={}
    assert contacts['2026-06-01']['contacts_seen']['reported_sum']==12
    assert 'followup_rate' not in contacts['2026-06-01']
