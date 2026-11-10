#!/usr/bin/env python3
"""Deterministic integrity manifest for One.com HTTPS-pulled BDBV site releases.

Only files within the explicitly supplied bdvd2026 release root are included.
The manifest is informational integrity metadata; the One.com importer must
also verify the downloaded release ZIP against GitHub's release asset digest.
"""
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA='ai-bdbv-https-release-v1'

def build(root):
    root=Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Release root does not exist')
    files={}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symbolic links prohibited in release: '+str(path))
        if not path.is_file():
            continue
        rel=path.relative_to(root).as_posix()
        if rel=='release_manifest.json':
            continue
        if rel.startswith('/') or '..' in Path(rel).parts:
            raise ValueError('Unsafe relative path')
        raw=path.read_bytes()
        files[rel]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    required={
        'assets/data/bulletins_public.json',
        'assets/data/contact_tracing_public.json',
        'assets/data/weekly_national_public.json',
        'assets/data/analysis_inputs/daily_evidence.json',
        'assets/data/analysis_inputs/weekly_evidence_packs.json',
        'assets/data/analysis_inputs/monthly_evidence_packs.json'
    }
    if not required<=files.keys():
        raise ValueError('Missing required data feeds: '+str(sorted(required-files.keys())))
    return {
        'schema_version':SCHEMA,
        'publication_type':'source_evidence_only',
        'ai_analysis_location':'one_com_existing_protocols',
        'ai_assessment_included':False,
        'editorial_approval_included':False,
        'root':'bdvd2026',
        'files':files
    }

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--root',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args(argv)
    output=Path(a.output)
    if output.resolve().parent!=Path(a.root).resolve():
        raise ValueError('Manifest must be written to release root')
    obj=build(a.root)
    output.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('Manifest validated:',len(obj['files']),'release files')

if __name__=='__main__':
    main()
