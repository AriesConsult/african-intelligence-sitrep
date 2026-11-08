"""Regression tests for source-derived partial health-zone and split contact tables."""
import json
from pathlib import Path
from sitrep_tables import extract_five_tables

ROOT = Path(__file__).resolve().parents[1]

def archived(no):
    matches = list((ROOT / 'review_queue').glob(f'report_{no:03d}_*.json'))
    assert len(matches) == 1, matches
    return json.loads(matches[0].read_text(encoding='utf-8'))


def test_sitrep_173_followup_table_continues_on_next_page():
    snap=extract_five_tables(archived(173))
    t=snap['tables']['table_4']
    assert t['status']=='MACHINE_VALIDATED', t['flags']
    assert t['national']['contacts_to_follow']==39667
    assert t['national']['contacts_seen']==33281
    assert t['national']['contact_follow_up_rate']==83.9
    assert t['national']['source']['page']==6


def test_sitrep_174_partial_ituri_healthzone_table_not_validated():
    snap=extract_five_tables(archived(174))
    t=snap['tables']['table_2']
    assert t['status']=='REVIEW_REQUIRED'
    reasons={f['reason'] for f in t['flags']}
    # Table 1 now validates after the shifted national CFR fix. Table 2 must
    # still be quarantined when a province total is missing from the extracted
    # health-zone coverage; the older generic crosscheck flag is obsolete.
    assert snap['tables']['table_1']['status'] == 'MACHINE_VALIDATED'
    assert 'table2_missing_province_total' in reasons


def test_sitrep_175_all_zone_and_unallocated_deaths_reconcile():
    snap=extract_five_tables(archived(175))
    t=snap['tables']['table_2']
    assert t['status']=='MACHINE_VALIDATED', t['flags']
    assert len(t['rows'])==67
    ituri=next(r for r in t['province_totals'] if r['province']=='Ituri')
    cases=sum(r['cumulative_cases'] for r in t['rows'] if r['province']=='Ituri')
    deaths=sum(r['cumulative_deaths'] for r in t['rows'] if r['province']=='Ituri')
    pending=sum(u['unallocated_deaths'] for u in t['unallocated_deaths'] if u['province']=='Ituri')
    assert (cases,deaths,pending)==(7543,3072,493)
    assert deaths+pending==ituri['cumulative_deaths']
