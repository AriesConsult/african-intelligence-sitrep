#!/usr/bin/env python3
"""Preserve unchanged, SHA-verified INSP SitRep PDF bytes in GitHub Releases.

Build downloads only report/hash pairs absent from a prior release inventory.
Finalize is called only AFTER the GitHub Release assets upload succeeds. No
unverified report is ever added to the durable inventory.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from discovery import session
from ingest import pdf_download
from run_pipeline import write_json

ROOT=Path(__file__).resolve().parent
SHA=re.compile(r'^[a-f0-9]{64}$')


def load(path, default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:return default


def build(registry_path:Path,published:Path,out:Path,pause:float=1.0,offline:Path|None=None):
    registry=load(registry_path,{'documents':{},'latest_by_report':{}})
    existing=load(published/'source_archive_index.json',{'archived':{}}).get('archived',{})
    targets=[]
    for num_str,sha in registry.get('latest_by_report',{}).items():
        no=int(num_str)
        key=f'{no:03d}:{sha}'
        if key in existing:continue
        record=registry.get('documents',{}).get(key)
        if record is None or not SHA.fullmatch(sha) or record.get('report_number')!=no:
            raise ValueError(f'Registry identity unavailable or invalid: {key}')
        targets.append((no,sha,record))
    targets.sort()
    out.mkdir(parents=True,exist_ok=True)
    zip_path=out/'original_sitreps.zip';manifest_path=out/'archive_manifest.json'
    if not targets:
        print(json.dumps({'status':'NOTHING_NEW_TO_ARCHIVE','already_archived':len(existing)}))
        return {'new':0,'already_archived':len(existing)}
    source=session();records=[];failures=[]
    with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for no,sha,record in targets:
            try:
                if offline:
                    raw=(offline/f'report_{no:03d}.pdf').read_bytes()
                    actual_url='offline:report_'+str(no)
                else:
                    raw,actual_url=pdf_download(source,{'url':record['source_url'],'provider':record.get('provider','INSP-official')})
                if not raw.startswith(b'%PDF-') or len(raw)>35_000_000 or hashlib.sha256(raw).hexdigest()!=sha:
                    raise ValueError('Source bytes, size or registered SHA256 mismatch')
                filename=f'SitRep_{no:03d}_{sha[:12]}.pdf'
                archive.writestr(filename,raw)
                records.append({'report_number':no,'report_date':record['report_date'],
                    'source_url':record['source_url'],'retrieval_url':actual_url,
                    'source_sha256':sha,'archive_member':filename,'pdf_bytes':len(raw)})
                print(f'Verified original PDF {no} ({len(raw)} bytes)',flush=True)
            except Exception as e:
                failures.append({'report_number':no,'sha256':sha,'reason':str(e)[:180]})
            finally:
                if not offline:time.sleep(max(0,pause))
    if failures or len(records)!=len(targets):
        zip_path.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)
        raise RuntimeError('Source archive incomplete; no release allowed: '+json.dumps(failures[:10]))
    meta={'schema_version':'bdbv-original-pdf-archive-v1',
        'created_at':datetime.now(timezone.utc).isoformat(),
        'files':records,'source_count':len(records),
        'note':'Original public INSP SitRep bytes, retained unchanged and verified by SHA-256; no endorsement implied.'}
    write_json(manifest_path,meta)
    # Bundle includes its own inventory for independent source-to-PDF verification.
    with zipfile.ZipFile(zip_path,'a',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        archive.writestr('archive_manifest.json',manifest_path.read_bytes())
    print(json.dumps({'status':'READY_FOR_RELEASE','new':len(records),'already_archived':len(existing),
                      'zip_bytes':zip_path.stat().st_size}))
    return {'new':len(records),'already_archived':len(existing)}


def finalize(published:Path,manifest:Path,tag:str,repository:str):
    if not re.fullmatch(r'bdbv-sitrep-originals-\d+',tag):raise ValueError('Unexpected immutable release tag')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):raise ValueError('Invalid repository identity')
    meta=load(manifest,{})
    if meta.get('source_count',0)!=len(meta.get('files',[])) or not meta.get('files'):
        raise ValueError('Archive manifest empty or inconsistent')
    path=published/'source_archive_index.json'
    index=load(path,{'schema_version':'bdbv-pdf-release-index-v1','archived':{},'releases':[]})
    download_url=f'https://github.com/{repository}/releases/download/{tag}/original_sitreps.zip'
    for rec in meta['files']:
        no=rec['report_number'];sha=rec['source_sha256'];key=f'{no:03d}:{sha}'
        if not SHA.fullmatch(sha):raise ValueError('Manifest SHA invalid')
        prior=index['archived'].get(key)
        if prior and prior.get('release_tag')!=tag:
            raise ValueError(f'Source {key} already archived in another immutable release')
        index['archived'][key]={'report_number':no,'report_date':rec['report_date'],
            'source_sha256':sha,'archive_member':rec['archive_member'],'pdf_bytes':rec['pdf_bytes'],
            'source_url':rec['source_url'],'release_tag':tag,'download_url':download_url}
    if tag not in [r.get('tag') for r in index['releases']]:
        index['releases'].append({'tag':tag,'download_url':download_url,
            'source_count':meta['source_count'],'created_at':meta.get('created_at')})
    index['generated_at']=datetime.now(timezone.utc).isoformat()
    index['archived_documents']=len(index['archived'])
    write_json(path,index)
    print(json.dumps({'tag':tag,'archived_documents':index['archived_documents'],'url':download_url}))
    return index


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['build','finalize'])
    p.add_argument('--registry',type=Path,default=ROOT/'state'/'registry.json')
    p.add_argument('--published',type=Path,default=ROOT/'published')
    p.add_argument('--out',type=Path,default=ROOT/'work'/'source_archive')
    p.add_argument('--manifest',type=Path)
    p.add_argument('--offline',type=Path)
    p.add_argument('--pause',type=float,default=1.0)
    p.add_argument('--tag')
    p.add_argument('--repository')
    args=p.parse_args()
    if args.command=='build':build(args.registry,args.published,args.out,args.pause,args.offline)
    else:finalize(args.published,args.manifest or args.out/'archive_manifest.json',args.tag,args.repository)
