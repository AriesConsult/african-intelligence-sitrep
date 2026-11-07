"""Independent validation of material prepared for publication."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reprocess_tables import reprocess
from audit_ingestion import audit
from verify_publication import verify

FIX = next((Path(__file__).resolve().parents[1] / 'review_queue').glob('report_175_*.json'))


def build(tmp_path):
    d = json.loads(FIX.read_text(encoding='utf8'))
    sha = d['sha256']; no = d['report_number']
    q=tmp_path/'review_queue';q.mkdir()
    (q/f'report_{no:03d}_{sha[:12]}.json').write_text(json.dumps(d))
    p=tmp_path/'published';p.mkdir()
    (p/'feed.json').write_text('{"observations":[]}')
    reg=tmp_path/'registry.json';reg.write_text(json.dumps({
        'documents':{f'{no:03d}:{sha}':{'report_number':no,'sha256':sha,'report_date':d['report_date']}},
        'latest_by_report':{str(no):sha}}))
    reprocess(q,p,reg,p/'feed.json')
    a=audit(q,p/'table_index.json',reg,p/'feed.json',p)
    (p/'ingestion_audit.json').write_text(json.dumps(a))
    return p,reg


def test_original_175_publication_passes(tmp_path):
    p,reg=build(tmp_path)
    result=verify(p,reg,check_narratives=False)
    assert result['pass'],result['errors']
    assert result['counters']['machine_observations_reconciled']==5


def test_published_count_tampering_fails(tmp_path):
    p,reg=build(tmp_path)
    f=p/'feed.json';data=json.loads(f.read_text())
    next(o for o in data['observations'] if o['metric_id']=='contacts_seen')['value']+=1
    f.write_text(json.dumps(data))
    result=verify(p,reg,check_narratives=False)
    assert not result['pass']
    assert any(e['reason']=='published_observation_reconciliation_failure' for e in result['errors'])


def test_missing_validated_table_fails(tmp_path):
    p,reg=build(tmp_path)
    i=json.loads((p/'table_index.json').read_text())
    snapshot=p/i['reports'][0]['snapshot_path']
    data=json.loads(snapshot.read_text())
    data['tables']['table_4']['status']='REVIEW_REQUIRED'
    snapshot.write_text(json.dumps(data))
    assert not verify(p,reg,check_narratives=False)['pass']
