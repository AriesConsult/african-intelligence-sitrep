"""Regression tests against the actual GitHub-catalogued SitRep extracts."""
import json
from pathlib import Path
import pytest
from sitrep_tables import extract_five_tables
from sitrep_narratives import narrative_from_pdf
from audit_ingestion import audit

ROOT=Path(__file__).resolve().parents[1]

def report(no):
    files=list((ROOT/'review_queue').glob(f'report_{no:03d}_*.json'))
    assert len(files)==1, files
    return json.loads(files[0].read_text(encoding='utf-8'))

def test_actual_sitrep_174_contact_header_shift():
    # This is the archived PDF extraction, not a hypothetical handbuilt grid.
    x=extract_five_tables(report(174))
    t=x['tables']['table_4']
    assert t['status']=='MACHINE_VALIDATED',t['flags']
    assert t['national']['contacts_to_follow']==37364
    assert t['national']['contacts_seen']==30882
    assert t['national']['contact_follow_up_rate']==82.7

def test_actual_sitrep_175_all_five_tables():
    x=extract_five_tables(report(175))
    assert x['tables_machine_validated']==5,x['quality_flags']
    assert x['tables']['table_2']['unallocated_deaths'][0]['unallocated_deaths']==493

def test_narrative_sha_revision_is_blocked():
    with pytest.raises(ValueError,match='SHA256'):
        narrative_from_pdf(b'%PDF-fake',report_number=175,date='2026-11-05',
          source_url='https://insp.cd/sitrep/',expected_sha='a'*64)

def test_ingestion_audit_counts_registry_and_queues():
    p=ROOT/'published'
    if not (p/'table_index.json').exists():pytest.skip('Initial backfill has not run')
    a=audit(ROOT/'review_queue',p/'table_index.json',ROOT/'state/registry.json',
            p/'feed.json',p)
    assert a['collected']['queue_documents_verified']==a['collected']['registry_documents']
    assert a['tables']['indexed_reports']==a['collected']['unique_report_numbers']
    assert a['feed']['observations_declared']==a['feed']['observations_verified']
