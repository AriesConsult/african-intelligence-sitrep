#!/usr/bin/env python3
"""Reanalyse archived PDF-table JSON without re-downloading original SitReps.

Writes one source-verified snapshot per report/revision, a small table index, and
ONLY accepted national operational metrics to the legacy One.com feed.
Published snapshots are secondary evidence; INRB case/death series is unchanged.
"""
from __future__ import annotations
import argparse, json, os, re
from pathlib import Path
from sitrep_tables import extract_five_tables, SCHEMA
from run_pipeline import load_json, write_json, update_feed

ROOT=Path(__file__).resolve().parent
SAFE_METRICS={
    'contacts_seen','contacts_to_follow','contact_follow_up_rate',
    'alerts_received','alerts_validated',
}

def obs(snapshot:dict):
    metadata={k:snapshot[k] for k in ('report_number','date','source_sha256','source_url')}
    items=[]
    for number,fields in ((3,{'alerts_received':'alerts_received','suspected_alerts':'alerts_validated'}),
                          (4,{'contacts_seen':'contacts_seen','contacts_to_follow':'contacts_to_follow',
                              'contact_follow_up_rate':'contact_follow_up_rate'})):
        t=snapshot['tables'].get(f'table_{number}')
        if not t or t.get('status')!='MACHINE_VALIDATED':continue
        national=t.get('national')
        if not national:continue
        for field,metric in fields.items():
            value=national.get(field)
            if value is None or metric not in SAFE_METRICS:continue
            items.append({'metric_id':metric,'value':value,'unit':'percent' if field.endswith('_rate') else 'count',
                         'date':metadata['date'],'report_number':metadata['report_number'],
                         'scope':'DRC','reporting_window':'As reported in the INSP SitRep for the stated date',
                         'evidence_status':'machine_validated','verification':'table_by_table_national_provincial_reconciliation',
                         'source_url':metadata['source_url'],'source_sha256':metadata['source_sha256'],
                         'page':national['source']['page'],'table_id':national['source']['table_id']})
    return items

def reprocess(queue:Path, published:Path, registry:Path,feed_path:Path):
    old=load_json(feed_path,{'observations':[]})
    reg=load_json(registry,{'documents':{},'latest_by_report':{}})
    docs=[];reports=[];errors=[];conflicts=[]
    snapdir=published/'tables';snapdir.mkdir(parents=True,exist_ok=True)
    for path in sorted(queue.glob('report_*.json')):
        try:
            d=json.loads(path.read_text(encoding='utf8'))
            snap=extract_five_tables(d)
            num=snap['report_number'];sha=snap['source_sha256'];key=f'{num:03d}:{sha}'
            rr=reg.get('documents',{}).get(key,{})
            is_revision=any(flag.get('reason')=='changed_pdf_sha_requires_revision_review' for flag in rr.get('validation_flags',[]))
            if is_revision:
                snap['status']='REVISION_REQUIRES_REVIEW'
                snap['quality_flags'].append({'reason':'source_pdf_revision_blocked_pending_manual_review'})
            if snap['tables_available']:
                write_json(snapdir/f'{num:03d}_{sha[:12]}.json',snap)
            # Don't overwrite published data with revised, contradictory PDFs.
            counts={name:len(t.get('rows',[])) for name,t in snap['tables'].items()}
            reports.append({'report_number':num,'date':snap['date'],'sha256':sha,'status':snap['status'],
                            'tables_available':snap['tables_available'],
                            'tables_machine_validated':snap['tables_machine_validated'],
                            'rows_by_table':counts,
                            'snapshot_path':f'tables/{num:03d}_{sha[:12]}.json',
                            'quality_flags_count':len(snap['quality_flags'])})
            if not is_revision:docs.append({'approved':obs(snap)})
        except (OSError,ValueError,TypeError,KeyError) as e:
            errors.append({'path':path.name,'message':str(e)[:200]})
    # The stable index is sufficient for dashboard freshness and navigation.
    reports.sort(key=lambda x:(x['date'],x['report_number'],x['sha256']),reverse=True)
    latest=[];seen=set()
    for r in reports:
        if r['report_number'] in seen:continue
        seen.add(r['report_number']);latest.append(r)
    idx={'schema_version':SCHEMA,'reports_processed':len(reports),'unique_reports':len(latest),
         'reports':latest,'extract_errors':errors,
         'source_repository':'https://github.com/INRB-UMIE/BDBV2026-Data',
         'methodology':'Parsed SitRep tables 1–5; validation status per table; unvalidated cells remain in review_queue.'}
    write_json(published/'table_index.json',idx)
    oldobs=list(old.get('observations',[]))
    # Re-run from checked archive for deterministic backfill. Never delete
    # human-approved observations already present in the feed.
    preserved=[o for o in oldobs if o.get('evidence_status')=='human_verified']
    feed=update_feed({'observations':preserved},docs,reg,old.get('generated_at') or '2026-11-07T00:00:00Z',[])
    feed['table_index_path']='published/table_index.json'
    feed['five_table_catalogue']={'reports_checked':len(reports),'reports_with_all_five_validated':sum(x['tables_machine_validated']==5 for x in reports),
                                  'latest_report':latest[0]['report_number'] if latest else None}
    # Existing validated metrics not from this reprocessor are retained unless
    # explicitly replaced; no silently dropped historical observations.
    produced={(o['date'],o['metric_id'],o['scope']) for o in feed['observations']}
    feed['observations'].extend(o for o in oldobs if (o.get('date'),o.get('metric_id'),o.get('scope','DRC')) not in produced)
    feed['observations'].sort(key=lambda o:(o.get('date',''),o.get('metric_id',''),o.get('scope','')))
    feed['observations_count']=len(feed['observations'])
    feed['publication_status']='VALIDATED_OBSERVATIONS' if feed['observations'] else 'NO_APPROVED_OBSERVATIONS'
    write_json(feed_path,feed)
    return {'checked':len(reports),'all_five':feed['five_table_catalogue']['reports_with_all_five_validated'],
            'observations':len(feed['observations']),'errors':len(errors)}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--queue',type=Path,default=ROOT/'review_queue')
    p.add_argument('--published',type=Path,default=ROOT/'published')
    p.add_argument('--registry',type=Path,default=ROOT/'state'/'registry.json')
    p.add_argument('--feed',type=Path,default=ROOT/'published'/'feed.json')
    args=p.parse_args();print(json.dumps(reprocess(args.queue,args.published,args.registry,args.feed),indent=2))
