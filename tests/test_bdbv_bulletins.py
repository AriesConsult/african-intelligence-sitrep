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


def test_annex_delta_markup_renders_in_both_languages_without_double_escaping():
    """Regression: trusted <small> markup must render, while values stay escaped."""
    from generate_bdbv_bulletins import numeric_annex_html
    current={'date':'2026-11-05','report_number':175,
      'source_sha256':'test-sha','source_url':'https://example.org/report.pdf',
      'tables':{'table_1':{'status':'MACHINE_VALIDATED',
        'original_table_number':1,
        'national':{'cumulative_cases':10803,'reported_cfr_pct':48.8},
        'rows':[{'scope':'Ituri','cumulative_cases':7543,'reported_cfr_pct':47.3}]}}}
    previous={'date':'2026-11-01','report_number':171,
      'tables':{'table_1':{'status':'MACHINE_VALIDATED',
        'national':{'cumulative_cases':10532,'reported_cfr_pct':48.7},
        'rows':[{'scope':'Ituri','cumulative_cases':7431,'reported_cfr_pct':47.0}]}}}
    for lang in ('en','fr'):
        page=numeric_annex_html(current,previous,lang)
        assert '10,803 <small>(+271)</small>' in page
        assert '7,543 <small>(+112)</small>' in page
        assert '48.8 <small>(+0.1 pp)</small>' in page
        assert '<div class="annex-scroll"><table>' in page
        assert '&lt;small&gt;' not in page
        # Values without a matching prior observation must remain plain text.
        page_unmatched=numeric_annex_html(current,None,lang)
        assert '10,803</td>' in page_unmatched
        assert '<small>(+271)</small>' not in page_unmatched


def test_digest_never_reuses_same_source_passage_across_topics():
    from generate_bdbv_bulletins import period_narratives
    shared='En Ituri, la rupture de stock de sang persiste, 37 malades sont critiques et les équipes signalent des difficultés.'
    distinct='Les équipes ont fourni de nouveaux équipements aux structures de santé pour soutenir les interventions quotidiennes.'
    snap={'date':'2026-11-05','report_number':175,'source_url':'https://example.org/sitrep.pdf',
      'candidates':[
        {'candidate_id':'c1','page':7,'excerpt':shared,'topic_tags':['treatment_capacity','logistics_and_supplies','service_continuity'],
         'review_status':'REVIEW_REQUIRED','excerpt_truncated':False,'event_type_candidates':['challenge']},
        {'candidate_id':'c2','page':8,'excerpt':distinct,'topic_tags':['logistics_and_supplies'],
         'review_status':'REVIEW_REQUIRED','excerpt_truncated':False,'event_type_candidates':[]}]}
    result=period_narratives([snap],'2026-11-05','2026-11-05')
    assert [x['topic'] for x in result]==['treatment_capacity','logistics_and_supplies']
    assert [x['candidate_id'] for x in result]==['c1','c2']
    assert len({x['excerpt'].casefold() for x in result})==len(result)
    assert all(x['status']=='REVIEW_REQUIRED' for x in result)
    # If only one paragraph supports multiple topics, omit the duplicate topic.
    result=period_narratives([{**snap,'candidates':snap['candidates'][:1]}],
                             '2026-11-05','2026-11-05')
    assert len(result)==1


def test_full_source_paragraph_is_preserved_and_long_passages_are_expandable():
    from generate_bdbv_bulletins import period_narratives, source_digest_html, render_html
    original=' '.join(['Un paragraphe source décrit les activités de surveillance et la situation dans les zones affectées.']*15)
    snap={'date':'2026-11-05','report_number':175,'source_url':'https://example.org/175.pdf',
      'candidates':[{'candidate_id':'p7-a','page':7,'excerpt':original,
        'topic_tags':['surveillance_and_alerts'],'review_status':'REVIEW_REQUIRED',
        'excerpt_truncated':False,'event_type_candidates':[]}]}
    selected=period_narratives([snap],'2026-11-05','2026-11-05')
    assert len(selected)==1 and selected[0]['excerpt']==original
    for language in ('en','fr'):
        markup=source_digest_html({'narrative':selected},language)
        assert original in markup
        assert 'REVIEW_REQUIRED' in markup
        assert '<details class="passage">' in markup
        assert 'https://example.org/175.pdf' in markup
        assert not markup.count('…')
    # Unverified truncated archived fragments cannot be silently promoted to full paragraphs.
    snap['candidates'][0]['excerpt_truncated']=True
    assert period_narratives([snap],'2026-11-05','2026-11-05')==[]


def test_bilingual_bulletin_layout_keeps_site_stylesheet_and_responsive_tables():
    from generate_bdbv_bulletins import render_html
    report={'frequency':'daily','period_start':'2026-11-05','period_end':'2026-11-05',
      'cases':10803,'deaths':5267,'source_date':'2026-11-05',
      'source_quality':'historical_qualified','source_commit':'abc123',
      'changes':{},'table4':None,'narrative':[],
      'original_report':None,'prior_report':None}
    for language in ('en','fr'):
        page=render_html(report,language)
        assert 'lang="'+language+'"' in page
        assert '/assets/css/african-intelligence.css' in page
        assert 'class="bulletin-page"' in page
        assert 'class="source-digest"' not in page
        assert 'class="data-table-scroll"' in page
        assert 'id="annex"' in page
        assert '@media(max-width:760px)' in page
        assert '<table>' in page


def test_narrative_fixture_topic_tags_align_with_real_registry():
    from generate_bdbv_bulletins import TOPIC_NAMES
    assert 'logistics_and_supplies' in TOPIC_NAMES
    assert 'logistics' not in TOPIC_NAMES
