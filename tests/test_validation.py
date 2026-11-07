import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from validation import validate_document
from candidates import parsed_numeric
from run_pipeline import update_feed

SOURCE='https://raw.githubusercontent.com/INRB-UMIE/BDBV2026-Data/main/data/insp_sitrep/raw/SitRep_MVE_174_2026.pdf'

def make_doc(rows,date='2026-11-04',sha='a'*64):
    return {'report_number':174,'report_date':date,'sha256':sha,'source_url':SOURCE,
      'tables':[{'page':3,'table_id':'p3-t4','indicator_families':['contact_tracing'],
                 'title_context':'Tableau 4 - Suivi des contacts','rows':rows}]}

def test_french_count_parsing():
    assert parsed_numeric('30 882')==('30882','count')
    assert parsed_numeric('30.882')==('30882','count')
    assert parsed_numeric('30,882')==('30882','count')
    assert parsed_numeric('82,7%')==('82.7','percent')
    assert parsed_numeric('82.7%')==('82.7','percent')
    assert parsed_numeric('ND')==('','')
    assert parsed_numeric('30 882/37 364')==('','')

def test_whitelisted_national_pair():
    d=make_doc([['Province','Contacts à suivre','Contacts vus','Taux de suivi'],
                ['Ituri','20 000','15 000','75%'],
                ['Total','37 364','30 882','82,7%']])
    r,flags=validate_document(d)
    assert not flags
    assert len(r)==3
    assert {x['metric_id']:x['value'] for x in r} == {'contacts_seen':30882,'contacts_to_follow':37364,'contact_follow_up_rate':82.7}
    assert all(x['page']==3 and x['source_sha256']=='a'*64 for x in r)

def test_reject_inconsistent_rate():
    d=make_doc([['Province','Contacts à suivre','Contacts vus','Taux de suivi'],['Total','37 364','30 882','98%']])
    r,flags=validate_document(d)
    assert not r and flags[0]['reason']=='ratio_or_count_validation_failed'

def test_reject_missing_total_and_ambiguous_total():
    header=['Province','Contacts à suivre','Contacts vus','Taux de suivi']
    for rows in [[header,['Ituri','100','80','80%']],
                 [header,['Total','100','80','80%'],['Total','100','80','80%']]]:
        r,_=validate_document(make_doc(rows))
        assert not r

def test_reject_non_contact_table():
    doc=make_doc([['Province','Contacts à suivre','Contacts vus','Taux de suivi'],['Total','100','80','80%']])
    doc['tables'][0]['indicator_families']=['laboratory']
    r,flags=validate_document(doc)
    assert not r

def test_update_feed_retains_previously_published_data_on_empty_run():
    d=make_doc([['Province','Contacts à suivre','Contacts vus','Taux de suivi'],['Total','100','80','80%']])
    r,_=validate_document(d)
    feed=update_feed({'observations':r},[],{'documents':{}},'2026-11-07T00:00:00Z',[])
    assert len(feed['observations'])==3
    assert feed['publication_status']=='VALIDATED_OBSERVATIONS'

def test_conflicting_republication_does_not_overwrite():
    d=make_doc([['Province','Contacts à suivre','Contacts vus','Taux de suivi'],['Total','100','80','80%']])
    old,_=validate_document(d)
    d2=make_doc([['Province','Contacts à suivre','Contacts vus','Taux de suivi'],['Total','100','75','75%']])
    replacement,_=validate_document(d2)
    feed=update_feed({'observations':old},[{'approved':replacement}],{'documents':{}},'2026-11-07T00:00:00Z',[])
    assert len(feed['validation_conflicts'])==2
    assert next(x for x in feed['observations'] if x['metric_id']=='contacts_seen')['value']==80
