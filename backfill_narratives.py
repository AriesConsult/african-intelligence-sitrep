#!/usr/bin/env python3
"""Download hash-verified SitRep originals and store review-only narrative leads.

No AI content is published. Original full text is retained only in workflow
artifacts (30 days by default); compact leads on the public GitHub branch.
"""
from __future__ import annotations
import argparse, hashlib, json, time
from datetime import datetime, timezone
from pathlib import Path
from discovery import session
from ingest import pdf_download
from run_pipeline import load_json, write_json
from sitrep_narratives import narrative_from_pdf

ROOT=Path(__file__).resolve().parent


def process(registry_path:Path,published:Path,work:Path,limit:int=12,pause:float=1.25,offline_dir:Path|None=None):
    registry=load_json(registry_path,{'documents':{},'latest_by_report':{}})
    docs=registry.get('documents',{}); latest=registry.get('latest_by_report',{})
    report_entries=[];failures=[];new=0;skipped=0
    session_obj=session()
    snapdir=published/'narrative_candidates';snapdir.mkdir(parents=True,exist_ok=True)
    work.mkdir(parents=True,exist_ok=True)
    targets=[]
    for no,sha in latest.items():
        try:num=int(no)
        except (TypeError,ValueError):continue
        key=f'{num:03d}:{sha}'
        r=docs.get(key)
        if not r:failures.append({'report_number':num,'reason':'latest_registry_identity_unavailable'});continue
        targets.append((num,sha,r))
    targets.sort(key=lambda x:x[0],reverse=True)
    # limit specifies which recent reports to check; 0 checks all archived reports.
    if limit>0:targets=targets[:limit]
    for num,sha,record in targets:
        filename=f'{num:03d}_{sha[:12]}.json';path=snapdir/filename
        if path.exists():
            try:
                existing=json.loads(path.read_text(encoding='utf-8'))
                if existing.get('source_sha256')==sha and existing.get('report_number')==num:
                    skipped+=1
                    report_entries.append({'report_number':num,'date':record.get('report_date'),
                         'source_sha256':sha,'status':'REVIEW_REQUIRED','candidates':existing.get('candidates_count',0),
                         'snapshot_path':f'narrative_candidates/{filename}'})
                    continue
            except (OSError,ValueError):pass
        try:
            if offline_dir:
                matches=sorted(offline_dir.glob(f'*{num}*.pdf'))
                if len(matches)!=1:raise ValueError('Offline fixture requires exactly one matching PDF')
                raw=matches[0].read_bytes()
                actual_url=record['source_url']
            else:
                raw,actual_url=pdf_download(session_obj,{'url':record['source_url'],'provider':record.get('provider','INSP-official')})
            if hashlib.sha256(raw).hexdigest()!=sha:
                raise ValueError('Downloaded PDF differs from registered SHA; revision requires review')
            classified=narrative_from_pdf(raw,report_number=num,date=record['report_date'],
                                           source_url=record['source_url'],expected_sha=sha)
            write_json(path,classified)
            new+=1
            report_entries.append({'report_number':num,'date':record.get('report_date'),
                'source_sha256':sha,'status':'REVIEW_REQUIRED','candidates':classified['candidates_count'],
                'snapshot_path':f'narrative_candidates/{filename}'})
            print(f'Narrative candidates SitRep {num}: {classified["candidates_count"]} blocks')
            # Full searchable page text is retained in the GitHub run artifact,
            # not committed to the public main branch.
            import pymupdf
            with pymupdf.open(stream=raw,filetype='pdf') as pdf:
                write_json(work/f'{num:03d}_{sha[:12]}.json',
                   {'report_number':num,'source_sha256':sha,'pages':[
                      {'page':i+1,'full_text':pg.get_text(sort=True)} for i,pg in enumerate(pdf)]})
        except Exception as e:
            failures.append({'report_number':num,'reason':str(e)[:200]})
        finally:
            if not offline_dir:time.sleep(max(0,pause))
    # Rebuild index from persisted candidates rather than only this incremental run.
    candidates=[];bad=[]
    for path in sorted(snapdir.glob('*.json')):
        try:
            j=json.loads(path.read_text(encoding='utf-8'))
            candidates.append({'report_number':j['report_number'],'date':j['date'],
                'source_sha256':j['source_sha256'],'candidate_count':j['candidates_count'],
                'snapshot_path':f'narrative_candidates/{path.name}',
                'status':j.get('status','REVIEW_REQUIRED')})
        except (ValueError,TypeError,KeyError,OSError) as e:bad.append({'file':path.name,'reason':str(e)[:120]})
    candidates.sort(key=lambda x:(x['date'],x['report_number']),reverse=True)
    index={'schema_version':'bdbv-narrative-index-v1','generated_at':datetime.now(timezone.utc).isoformat(),
           'reports_with_narrative_candidates':len(candidates),'registry_reports':len(targets) if limit==0 else len(latest),
           'candidates_total':sum(x['candidate_count'] for x in candidates),'reports':candidates,
           'new_processed_this_run':new,'cached_this_run':skipped,'failures_this_run':failures,
           'index_read_errors':bad,
           'publication_policy':'REVIEW_ONLY: lexical tags must not be treated as independently verified events or causal interpretations.'}
    write_json(published/'narrative_index.json',index)
    return {'new':new,'cached':skipped,'classified_reports_total':len(candidates),
            'candidate_blocks_total':index['candidates_total'],'failures':failures,'index_errors':bad}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--registry',type=Path,default=ROOT/'state/registry.json')
    p.add_argument('--published',type=Path,default=ROOT/'published')
    p.add_argument('--work',type=Path,default=ROOT/'work/narrative_full_text')
    p.add_argument('--limit',type=int,default=12)
    p.add_argument('--pause',type=float,default=1.25)
    p.add_argument('--offline-dir',type=Path)
    a=p.parse_args()
    print(json.dumps(process(a.registry,a.published,a.work,a.limit,a.pause,a.offline_dir),ensure_ascii=False,indent=2))
