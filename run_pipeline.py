#!/usr/bin/env python3
"""INSP/INRB SitRep -> bounded extraction -> machine-validated public JSON.

Outputs remain distinct: unverified cells in run artifacts, only whitelisted
numerator/denominator/rate observations can enter public feed. Never changes
INRB's national case/death source or the BDBV forecast calculations.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from discovery import discover_all, session
from ingest import pdf_download
from extraction import extract_pdf
from validation import validate_document, SCHEMA
from candidates import write_csv
from review_approved import read_approvals

ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'state'/'registry.json'
DEFAULT_FEED=ROOT/'published'/'feed.json'

def load_json(path:Path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return default

def write_json(path:Path,object):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(object,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    os.replace(temp,path)

def update_feed(old:dict, docs:list, registry:dict, time_utc:str, failures:list)->dict:
    observations=list(old.get('observations',[]))
    index={(r['date'],r['metric_id'],r.get('scope','DRC')):r for r in observations}
    conflicts=[]
    for doc in docs:
        for o in doc.get('approved',[]):
            key=(o['date'],o['metric_id'],o['scope'])
            prev=index.get(key)
            if prev and prev['value']!=o['value']:
                conflicts.append({'date':o['date'],'metric_id':o['metric_id'], 'reason':'new_value_for_existing_date_requires_review'})
                continue
            if not prev:index[key]=o
    observations=sorted(index.values(),key=lambda x:(x['date'],x['metric_id'],x['scope']))
    # Fail-safe: remote source failure never discards previously published observations.
    latest={}
    for o in observations:
        k=o['metric_id']
        if k not in latest or o['date']>latest[k]:latest[k]=o['date']
    return {
        'schema_version':SCHEMA,'generated_at':time_utc,
        'source_priority':['INSP official SitReps (original PDF)','INRB-UMIE/BDBV2026-Data PDF archive'],
        'source_catalogue':'https://insp.cd/sitrep/',
        'source_repository':'https://github.com/INRB-UMIE/BDBV2026-Data',
        'validation_policy':'Machine-validated only when national numerator, denominator and printed percentage agree within 0.65 percentage points; not human audited.',
        'publication_status':'VALIDATED_OBSERVATIONS' if observations else 'NO_APPROVED_OBSERVATIONS',
        'documents_catalogued':len(registry.get('documents',{})),
        'pending_review_count':sum(1 for r in registry.get('documents',{}).values() if r.get('status')=='REVIEW_REQUIRED'),
        'observations_count':len(observations),
        'latest_by_metric':latest,'observations':observations,
        'validation_conflicts':conflicts[-50:],
        'source_failures_this_run':len(failures),
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--limit',type=int,default=12,help='latest N reports; 0 for complete backfill')
    p.add_argument('--offline-dir',type=Path)
    p.add_argument('--state',type=Path,default=DEFAULT_STATE)
    p.add_argument('--feed',type=Path,default=DEFAULT_FEED)
    p.add_argument('--work',type=Path,default=ROOT/'work')
    p.add_argument('--pause',type=float,default=1.0)
    args=p.parse_args(argv)
    args.work.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).isoformat()
    registry=load_json(args.state,{'schema_version':'bdbv-registry-v1','documents':{},'latest_by_report':{}})
    registry.setdefault('documents',{});registry.setdefault('latest_by_report',{})
    old=load_json(args.feed,{'observations':[]})
    session_obj=session(); failures=[]; docs=[]; reviewed=[];processed=0
    if args.offline_dir:
        # Number recognition same code path as online discovery.
        from discovery import number_from_string
        srcs=[{'number':number_from_string(f.name) or 0,'sources':[{'url':str(f),'provider':'offline-fixture','basename':f.name}]} for f in sorted(args.offline_dir.glob('*.pdf'))]
    else:
        srcs,errors=discover_all(session_obj)
        failures+=errors
    if args.limit>0:srcs=srcs[:args.limit]
    if not srcs and not args.offline_dir:
        print('No SitReps discovered; retaining prior JSON unchanged.',file=sys.stderr)
        return 2
    pdfdir=args.work/'source_pdfs';pdfdir.mkdir(parents=True,exist_ok=True)
    queuedir=ROOT/'review_queue';queuedir.mkdir(parents=True,exist_ok=True)
    for item in srcs:
        number=item['number']
        for source in item['sources']:
            try:
                if args.offline_dir:
                    raw=Path(source['url']).read_bytes();url='offline:'+Path(source['url']).name
                else:raw,url=pdf_download(session_obj,source)
                if len(raw)>35_000_000:raise ValueError('Over 35 MB')
                sha=hashlib.sha256(raw).hexdigest()
                key=f'{number:03d}:{sha}'
                if key in registry['documents']:
                    reviewed.append({'report_number':number,'status':'previously_catalogued','sha256':sha})
                    break
                record=extract_pdf(raw,url=url,expected_number=number or None)
                if not record.get('report_number') or not record.get('report_date'):
                    # Unidentifiable report remains review-only.
                    approved=[];flags=[{'reason':'report_date_or_number_unverifiable'}]
                else:approved,flags=validate_document(record)
                if args.offline_dir:
                    approved=[];flags.append({'reason':'offline_fixture_cannot_publish'})
                older=registry['latest_by_report'].get(str(record['report_number'] or number))
                if older and older!=sha:
                    flags.append({'reason':'changed_pdf_sha_requires_revision_review','old_sha':older,'new_sha':sha})
                    approved=[]  # don't auto-publish a revised report
                status='MACHINE_VALIDATED' if approved else 'REVIEW_REQUIRED'
                key=f'{(record["report_number"] or number):03d}:{sha}'
                registry['documents'][key]={
                    'report_number':record['report_number'],'report_date':record['report_date'],
                    'sha256':sha,'source_url':url,'provider':source['provider'],
                    'pages':record['n_pages'],'tables':len(record['tables']),
                    'checked_at':now,'status':status,'validation_flags':flags,
                }
                registry['latest_by_report'][str(record['report_number'] or number)]=sha
                record['approved']=approved
                docs.append(record)
                stamp=f'SitRep_{(record["report_number"] or number):03d}_{sha[:12]}'
                (pdfdir/(stamp+'.pdf')).write_bytes(raw)
                write_json(queuedir/f'report_{(record["report_number"] or number):03d}_{sha[:12]}.json',
                    {k:record[k] for k in ('report_number','report_date','source_url','sha256','tables')})
                # Full table extraction retained in workflow artifact, not public feed.
                (args.work/(stamp+'.tables.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
                reviewed.append({'report_number':number,'status':status,'sha256':sha,'approved_cells':len(approved),'flag_count':len(flags)})
                processed+=1
                print(f'Processed SitRep {number}: {len(record["tables"])} tables; machine-valid observations={len(approved)}',flush=True)
                break
            except Exception as e:
                failures.append({'report_number':number,'source':source['provider'],'error':str(e)[:400]})
        if not args.offline_dir:time.sleep(max(0,args.pause))
    candidate_count=write_csv(args.work/'unverified_table_cells.csv',docs)
    write_json(args.state,registry)
    manually_approved,review_errors=read_approvals(ROOT/'reviewed'/'approved_observations.csv',queuedir)
    if review_errors:failures.extend({'reason':'review_approval_invalid',**e} for e in review_errors)
    if manually_approved:docs.append({'approved':manually_approved})
    feed=update_feed(old,docs,registry,now,failures)
    write_json(args.feed,feed)
    write_json(args.work/'run_manifest.json',{'checked_at':now,'discovered_count':len(srcs),'new_extracted':processed,
        'unverified_cells':candidate_count,'reviewed':reviewed,'review_approvals':len(manually_approved),'failures':failures,
        'published_observations':feed['observations_count']})
    print(json.dumps({'new_reports':processed,'observations':feed['observations_count'],
                      'pending_review':feed['pending_review_count'],'source_errors':len(failures)}))
    # Nonzero if none were usable in an empty feed? Keep feed informative; source outage caught above.
    return 0

if __name__=='__main__':raise SystemExit(main())
