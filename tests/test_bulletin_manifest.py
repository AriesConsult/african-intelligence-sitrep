from pathlib import Path
import hashlib
import pytest
from create_bulletin_manifest import build, SCHEMA

def test_manifest_proves_source_only_and_hashes_expected_assets(tmp_path):
    root=tmp_path/'bdvd2026'
    expected=[
        'assets/data/bulletins_public.json',
        'assets/data/contact_tracing_public.json',
        'assets/data/weekly_national_public.json',
        'assets/data/analysis_inputs/daily_evidence.json',
        'assets/data/analysis_inputs/weekly_evidence_packs.json',
        'assets/data/analysis_inputs/monthly_evidence_packs.json',
    ]
    for rel in expected:
        p=root/rel
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text('{}')
    result=build(root)
    assert result['schema_version']==SCHEMA
    assert not result['ai_assessment_included']
    assert result['files'][expected[0]]['sha256']==hashlib.sha256(b'{}').hexdigest()
    assert set(result['files'])==set(expected)
    (root/'release_manifest.json').write_text('{}')
    assert 'release_manifest.json' not in build(root)['files']

def test_manifest_rejects_symlinks_and_missing_feeds(tmp_path):
    root=tmp_path/'bdvd2026'
    root.mkdir()
    with pytest.raises(ValueError,match='Missing required'):
        build(root)
    (root/'outside').symlink_to(tmp_path)
    with pytest.raises(ValueError,match='Symbolic links'):
        build(root)
