"""Durable original-PDF archiving safety and idempotence (offline only)."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from archive_originals import build, finalize


def setup_one(tmp):
    raw=b'%PDF-1.4\n% source-byte-hash-test\n'
    sha=hashlib.sha256(raw).hexdigest()
    p=tmp/'originals';p.mkdir();(p/'report_175.pdf').write_bytes(raw)
    output=tmp/'published';output.mkdir()
    reg=tmp/'registry.json'
    reg.write_text(json.dumps({'documents':{'175:'+sha:{'report_number':175,
        'report_date':'2026-11-05','source_url':'https://insp.cd/sitrep.pdf'}},
        'latest_by_report':{'175':sha}}))
    return p,output,reg,sha


def test_original_pdf_release_roundtrip(tmp_path):
    originals,published,reg,sha=setup_one(tmp_path)
    out=tmp_path/'out'
    assert build(reg,published,out,0,originals)['new']==1
    with zipfile.ZipFile(out/'original_sitreps.zip') as z:
        names=z.namelist()
        assert 'archive_manifest.json' in names
        assert hashlib.sha256(z.read('SitRep_175_'+sha[:12]+'.pdf')).hexdigest()==sha
    info=finalize(published,out/'archive_manifest.json','bdbv-sitrep-originals-1234',
        'AriesConsult/african-intelligence-sitrep')
    assert info['archived_documents']==1
    assert build(reg,published,tmp_path/'again',0,originals)['new']==0


def test_mismatched_pdf_never_creates_releasable_archive(tmp_path):
    originals,published,reg,sha=setup_one(tmp_path)
    (originals/'report_175.pdf').write_bytes(b'%PDF-1.4\nchanged but still PDF marker')
    output=tmp_path/'bad_archive'
    with pytest.raises(RuntimeError,match='archive incomplete'):
        build(reg,published,output,0,originals)
    assert not (output/'original_sitreps.zip').exists()
    assert not (output/'archive_manifest.json').exists()
