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


def test_original_table4_national_and_provincial_is_preferred_over_old_csv(tmp_path):
    import json
    from generate_bdbv_bulletins import load_table4,load_narratives,period_narratives,source_digest_html
    pub=tmp_path/'published'
    (pub/'tables').mkdir(parents=True)
    source={'date':'2026-11-03','source_sha256':'123abc','report_number':173,
      'source_url':'https://insp.cd/example.pdf',
      'tables':{'table_4':{'status':'MACHINE_VALIDATED',
        'national':{'contacts_seen':33281,'contacts_to_follow':39667,
          'contact_follow_up_rate':83.9,'source':{'page':6}},
        'rows':[{'scope':'Ituri','contacts_seen':15704,'contacts_to_follow':17670}],
        'reporting_gaps':[{'scope':'Bas-Uélé'}]}}}
    (pub/'tables/173.json').write_text(json.dumps(source))
    (pub/'table_index.json').write_text(json.dumps({'reports':[{
      'snapshot_path':'tables/173.json','sha256':'123abc','date':'2026-11-03'}]}))
    result=load_table4(pub)
    assert result['2026-11-03']['national']['contacts_seen']==33281
    assert result['2026-11-03']['national']['contacts_to_follow']==39667
    assert result['2026-11-03']['national']['follow_up_pct']==83.9
    assert result['2026-11-03']['provinces'][0]['province']=='Ituri'

    # Fail closed on a mismatched source identity and an invalid national rate.
    source['tables']['table_4']['national']['contact_follow_up_rate']=70.0
    (pub/'tables/173.json').write_text(json.dumps(source))
    assert load_table4(pub)=={}

def test_source_excerpt_digest_retains_review_flag_and_page_reference(tmp_path):
    import json
    from generate_bdbv_bulletins import load_narratives,period_narratives,source_digest_html
    pub=tmp_path/'published'
    (pub/'narrative_candidates').mkdir(parents=True)
    source={'date':'2026-11-03','source_sha256':'source-hash','report_number':173,
       'source_url':'https://insp.cd/example.pdf','candidates':[{
         'topic_tags':['vaccination'],'review_status':'REVIEW_REQUIRED',
         'excerpt_truncated':False,
         'excerpt':'Au Bas-Uélé, une équipe de vaccination a poursuivi ses activités communautaires dans plusieurs localités durant la journée.',
         'event_type_candidates':[],'page':7,'candidate_id':'173-p7-b1'}]}
    (pub/'narrative_candidates/173.json').write_text(json.dumps(source))
    (pub/'narrative_index.json').write_text(json.dumps({'reports':[{
       'snapshot_path':'narrative_candidates/173.json','source_sha256':'source-hash','date':'2026-11-03'}]}))
    sel=period_narratives(load_narratives(pub),'2026-11-03','2026-11-03')
    assert len(sel)==1 and sel[0]['status']=='REVIEW_REQUIRED'
    doc={'narrative':sel}
    page=source_digest_html(doc,'en')
    assert 'https://insp.cd/example.pdf' in page and 'p. 7' in page
    assert 'verification pending' in page
