#!/usr/bin/env python3
"""Provenance, completeness and validation audit for the BDBV SitRep archive.

This checks *ingestion*, not whether every published report exists or every PDF
layout has a recoverable table. Gaps are disclosed rather than silently filled.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPORT_RX=re.compile(r'^report_(\d{3})_([a-f0-9]{12})\.json$')


def load(path:Path):
    return json.loads(path.read_text(encoding='utf-8'))


def audit(queue:Path, index_path:Path, registry_path:Path, feed_path:Path, published:Path):
    reg=load(registry_path);idx=load(index_path);feed=load(feed_path)
    errs=[];seen=set();nums=set();queue_sha=set();queued=0
    for p in queue.glob('report_*.json'):
        m=REPORT_RX.fullmatch(p.name)
        if not m:
            errs.append({'reason':'malformed_queue_filename','file':p.name});continue
        try:
            d=load(p)
            no=int(m.group(1));sha=d.get('sha256','')
            if not re.fullmatch('[a-f0-9]{64}',sha or '') or not sha.startswith(m.group(2)) or d.get('report_number')!=no:
                errs.append({'reason':'queue_identity_mismatch','file':p.name});continue
            if not d.get('report_date') or not d.get('source_url') or not isinstance(d.get('tables'),list):
                errs.append({'reason':'queue_missing_provenance','file':p.name});continue
            key=f'{no:03d}:{sha}'
            if key in seen:errs.append({'reason':'duplicate_queue_identity','file':p.name})
            seen.add(key);nums.add(no);queue_sha.add(key);queued+=1
        except (OSError,ValueError,TypeError) as e:
            errs.append({'reason':'queue_unreadable','file':p.name,'detail':str(e)[:90]})
    registry_keys=set(reg.get('documents',{}))
    for k in sorted(registry_keys-queue_sha):
        errs.append({'reason':'registered_pdf_without_extraction_queue','key':k})
    for k in sorted(queue_sha-registry_keys):
        errs.append({'reason':'queue_unregistered','key':k})
    reports=idx.get('reports',[])
    valid_counts=Counter(int(r.get('tables_machine_validated',0)) for r in reports)
    status_counts=Counter(r.get('status','unknown') for r in reports)
    cover={i:sum(1 for r in reports if r.get('tables_machine_validated',0)>=i) for i in range(1,6)}
    table_scores={}
    for i in range(1,6):
        t=f'table_{i}'
        table_scores[t]={
            'records_with_rows':sum(r.get('rows_by_table',{}).get(t,0)>0 for r in reports),
            'status_unavailable_from_index':True,
        }
    missing_snapshots=[];indexed_ids=set()
    for r in reports:
        no=r.get('report_number');sha=r.get('sha256');indexed_ids.add((no,sha))
        rel=r.get('snapshot_path')
        if rel:
            snap=published/rel
            if not snap.is_file():missing_snapshots.append({'report':no,'path':rel,'reason':'snapshot_missing'})
            else:
                try:
                    sj=load(snap)
                    if sj.get('report_number')!=no or sj.get('source_sha256')!=sha:
                        missing_snapshots.append({'report':no,'path':rel,'reason':'snapshot_identity_mismatch'})
                except (ValueError,OSError):missing_snapshots.append({'report':no,'path':rel,'reason':'snapshot_unreadable'})
        elif r.get('tables_available',0)>0:
            missing_snapshots.append({'report':no,'reason':'nonempty_report_without_snapshot'})
    missing_from_index=sorted(nums-{n for n,s in indexed_ids})
    # Numbering gaps are NOT asserted to be unpublished reports.
    possible_gaps=sorted(set(range(1,max(nums)+1))-nums) if nums else []
    observations=feed.get('observations',[])
    obs_errors=[];seen_obs=set()
    for o in observations:
        identity=(o.get('date'),o.get('metric_id'),o.get('scope','DRC'))
        if identity in seen_obs:obs_errors.append({'reason':'duplicate_observation_key','key':identity})
        seen_obs.add(identity)
        if not o.get('source_sha256') or not o.get('source_url') or not o.get('page'):
            obs_errors.append({'reason':'observation_missing_primary_provenance','key':identity})
    audit_result={
      'schema_version':'bdbv-ingestion-audit-v1',
      'generated_at':datetime.now(timezone.utc).isoformat(),
      'assessment':'PARTIAL_VALIDATION' if valid_counts.get(5,0)<len(reports) else 'ALL_COLLECTED_REPORTS_VALIDATED',
      'collected':{'registry_documents':len(registry_keys),'queue_documents_verified':queued,
                   'unique_report_numbers':len(nums),'highest_report_number':max(nums) if nums else None,
                   'numbering_gaps_not_equivalent_to_missing_publications':possible_gaps},
      'tables':{'indexed_reports':len(reports),'validation_distribution':{str(k):v for k,v in sorted(valid_counts.items())},
                'reports_with_at_least_n_validated_tables':{str(k):v for k,v in cover.items()},
                'rows_recovered':table_scores,'status_distribution':dict(status_counts)},
      'feed':{'observations_declared':feed.get('observations_count'),
              'observations_verified':len(observations),'metrics':sorted({o.get('metric_id') for o in observations}),
              'issues':obs_errors},
      'source_consistency':{'queue_issues':errs,'indexed_without_queue':missing_from_index,
                            'snapshot_issues':missing_snapshots,
                            'pass':not errs and not missing_snapshots and not missing_from_index and not obs_errors},
      'limitations':['No claim that every integer in 1..max(report number) was published',
                     'A verified PDF identity does not establish numerical or narrative validity',
                     'Missing/ND data are not zero',
                     'Original PDF persistence must be checked separately; workflow artifacts expire'],
    }
    narrative_index=published/'narrative_index.json'
    if narrative_index.is_file():
        try:
            ni=load(narrative_index)
            reportset={(r.get('report_number'),r.get('source_sha256')) for r in ni.get('reports',[])}
            missing=[r.get('report_number') for r in reports
                     if (r.get('report_number'),r.get('sha256')) not in reportset]
            audit_result['narratives']={
                'status':'PARTIAL' if missing else 'ALL_CATALOGUED_REPORTS_CLASSIFIED',
                'reports_with_candidates':ni.get('reports_with_narrative_candidates',0),
                'candidate_blocks_for_review':ni.get('candidates_total',0),
                'unclassified_report_numbers':missing,
                'last_run_failures':ni.get('failures_this_run',[]),
                'all_candidates_require_review':True,
            }
        except (ValueError,TypeError,OSError) as e:
            audit_result['narratives']={'status':'INDEX_INVALID','error':str(e)[:120]}
    else:
        audit_result['narratives']={'status':'NOT_YET_RUN'}
    original_archive_path=published/'source_archive_index.json'
    if original_archive_path.is_file():
        try:
            source_archive=load(original_archive_path)
            mapped=source_archive.get('archived',{})
            latest_keys={f'{int(no):03d}:{sha}' for no,sha in reg.get('latest_by_report',{}).items()}
            unarchived=sorted(latest_keys-set(mapped))
            malformed=[key for key,item in mapped.items()
                if not isinstance(item,dict) or not key.endswith(':'+str(item.get('source_sha256','')))
                or not item.get('download_url') or not isinstance(item.get('pdf_bytes'),int)
                or item['pdf_bytes']<=0]
            audit_result['original_pdf_archives']={
                'status':'INVENTORY_INVALID' if malformed else
                          ('ALL_CATALOGUED_ORIGINALS_ARCHIVED' if not unarchived else 'PARTIAL'),
                'archived_document_hashes':len(mapped),
                'latest_report_hashes':len(latest_keys),
                'remaining_latest_hashes':len(unarchived),
                'unarchived_report_keys':unarchived,
                'malformed_archive_index_keys':malformed,
                'release_count':len(source_archive.get('releases',[])),
                'note':'Immutable GitHub Release inventory; archive asset checksums are in embedded manifests.'}
        except (TypeError,ValueError,OSError,KeyError) as e:
            audit_result['original_pdf_archives']={'status':'INDEX_UNREADABLE','reason':str(e)[:140]}
    else:
        audit_result['original_pdf_archives']={'status':'NOT_YET_ARCHIVED'}
    return audit_result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--queue',type=Path,default=ROOT/'review_queue')
    p.add_argument('--published',type=Path,default=ROOT/'published')
    p.add_argument('--registry',type=Path,default=ROOT/'state'/'registry.json')
    p.add_argument('--feed',type=Path,default=ROOT/'published/feed.json')
    a=p.parse_args()
    result=audit(a.queue,a.published/'table_index.json',a.registry,a.feed,a.published)
    output=a.published/'ingestion_audit.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'verified_queues':result['collected']['queue_documents_verified'],
       'index_reports':result['tables']['indexed_reports'],
       'numerical_validation':result['tables']['validation_distribution'],
       'audit_pass':result['source_consistency']['pass'],
       'errors':sum(len(v) for k,v in result['source_consistency'].items() if isinstance(v,list))},indent=2))
    if not result['source_consistency']['pass']:
        raise SystemExit('BLOCKED: source identity, snapshot, or feed-provenance audit failed')
