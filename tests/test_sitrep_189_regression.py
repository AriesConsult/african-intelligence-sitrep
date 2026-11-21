"""Regression against the archived SitRep 189, 19 November 2026.

The source extraction in review_queue is immutable. Do not promote
unvalidated case/death cells merely because one parser test passes.
"""
import copy
import json
from pathlib import Path

from sitrep_tables import extract_five_tables

ROOT=Path(__file__).resolve().parents[1]


def _doc():
    path=next((ROOT/'review_queue').glob('report_189_276b1b002a47.json'))
    return json.loads(path.read_text(encoding='utf8'))


def test_original_189_tables_1_3_4_reconcile():
    s=extract_five_tables(_doc())
    t=s['tables']
    assert t['table_1']['status']=='MACHINE_VALIDATED',t['table_1']['flags']
    assert t['table_1']['national']['cumulative_cases']==11723
    assert t['table_1']['national']['cumulative_deaths']==5752
    assert t['table_1']['national']['new_cases_24h']==43
    assert sum(p['cumulative_cases'] for p in t['table_1']['rows'])==11723
    assert t['table_3']['status']=='MACHINE_VALIDATED',t['table_3']['flags']
    assert t['table_3']['national']['alerts_received']==4565
    assert t['table_3']['national']['suspected_alerts']==518
    assert t['table_3']['national']['suspects_transferred']==283
    assert len(t['table_3']['rows'])==6
    assert t['table_4']['status']=='MACHINE_VALIDATED',t['table_4']['flags']
    assert t['table_4']['national']['contacts_to_follow']==29891
    assert t['table_4']['national']['contacts_seen']==25501
    assert t['table_4']['national']['contact_follow_up_rate']==85.3
    assert sum(r['contacts_seen'] for r in t['table_4']['rows'])==25501
    # The new Table 5 has eight provinces but no Global column: keep quarantined.
    assert t['table_5']['status']=='REVIEW_REQUIRED'


def test_189_tampered_case_count_cannot_validate():
    doc=_doc()
    grid=next(x for x in doc['tables'] if x['page']==2 and x['table_id']=='p2-t3')
    grid['rows'][7][3]='8006'
    t=extract_five_tables(doc)['tables']['table_1']
    assert t['status']=='REVIEW_REQUIRED'


def test_189_tampered_alerts_cannot_validate():
    doc=_doc()
    grid=next(x for x in doc['tables'] if x['page']==5 and x['table_id']=='p5-t12')
    grid['rows'][12][3]='1611'
    t=extract_five_tables(doc)['tables']['table_3']
    assert t['status']=='REVIEW_REQUIRED'


def test_189_tampered_next_page_contact_total_cannot_validate():
    doc=_doc()
    p=next(p for p in doc['pages'] if p['page']==6)
    assert '25 501' in p['text']
    p['text']=p['text'].replace('25 501','25 500',1)
    t=extract_five_tables(doc)['tables']['table_4']
    assert t['status']=='REVIEW_REQUIRED'
