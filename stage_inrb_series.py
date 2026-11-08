#!/usr/bin/env python3
"""Stage pinned INRB SitRep CSV observations with original values and provenance.

ALL records are unverified comparison candidates, never approved epidemiological data.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,io,json,re
from collections import Counter
from datetime import date
from pathlib import Path
import requests
REPO='INRB-UMIE/BDBV2026-Data'
PREFIX='data/insp_sitrep/processed/'
RX=re.compile(r'^'+PREFIX+r'insp_sitrep__(.+)__daily\.csv$')

def decode_value(raw):
 s=(raw or '').strip()
 if not s or s.upper() in ('ND','NA','N/A','NR','NULL'):
  return None,'NOT_REPORTED' if s.upper()=='ND' else 'MISSING_OR_NOT_APPLICABLE'
 cleaned=s.replace(' ','').replace('\u202f','').replace('\u00a0','')
 if re.fullmatch(r'-?\d+',cleaned):return int(cleaned),'NUMERIC_UNVERIFIED'
 if re.fullmatch(r'-?\d+[,.]\d+',cleaned):return float(cleaned.replace(',','.')),'NUMERIC_UNVERIFIED'
 return None,'UNPARSEABLE'

def candidate_policy(metric):
 if metric in ('national_cumulative_confirmed_cases','national_cumulative_confirmed_deaths'):
  return 'INRB_DIRECT_BANNER_TRANSCRIPTION_PENDING_PDF_QA'
 if metric in ('cumulative_confirmed_cases','cumulative_suspected_cases','cumulative_suspected_deaths','national_cumulative_suspected_cases','national_cumulative_suspected_deaths'):
  return 'INRB_POTENTIALLY_CARRIED_FORWARD_OR_DERIVED_PENDING_PDF_QA'
 return 'INRB_CURATED_VALUE_SOURCE_MODE_UNKNOWN_PENDING_PDF_QA'

def stage(registry_path,commit,out,session=None,paths=None):
 if not re.fullmatch(r'[a-f0-9]{40}',commit):raise ValueError('Pin upstream commit SHA')
 ses=session or requests.Session()
 reg=json.loads(registry_path.read_text(encoding='utf-8'))
 by_date={}
 for d in reg['documents'].values():
  by_date.setdefault(d.get('report_date'),[]).append({'report_number':d['report_number'],'source_pdf_sha256':d['sha256']})
 if paths is None:
  response=ses.get(f'https://api.github.com/repos/{REPO}/git/trees/{commit}?recursive=1',timeout=90)
  response.raise_for_status();tree=response.json()
  if tree.get('truncated'):raise ValueError('INRB tree truncated')
  paths=[f['path'] for f in tree['tree'] if f.get('type')=='blob' and RX.match(f['path'])]
 paths=sorted(paths)
 if not paths:raise ValueError('No INRB SitRep daily files')
 out.mkdir(parents=True,exist_ok=True)
 source_dir=out/'source_csv';source_dir.mkdir(exist_ok=True)
 summaries=[];totals=Counter();exceptions=[]
 with gzip.open(out/'inrb_observation_candidates.jsonl.gz','wt',encoding='utf-8',compresslevel=6) as fh:
  for path in paths:
   m=RX.match(path)
   if not m:raise ValueError('Unexpected upstream file: '+path)
   metric=m.group(1)
   url=f'https://raw.githubusercontent.com/{REPO}/{commit}/{path}'
   response=ses.get(url,timeout=120);response.raise_for_status()
   raw=response.content;sha=hashlib.sha256(raw).hexdigest()
   (source_dir/Path(path).name).write_bytes(raw)
   csv_rows=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
   if not csv_rows.fieldnames or not {'nom','date',metric}.issubset(csv_rows.fieldnames):
    raise ValueError('Unexpected INRB CSV columns: '+path+' '+repr(csv_rows.fieldnames))
   counts=Counter();dates=set();geographies=set();duplicates=set();seen=set()
   for lineno,row in enumerate(csv_rows,2):
    day=row['date'];name=row['nom'];raw_value=row[metric]
    try:date.fromisoformat(day)
    except (ValueError,TypeError):raise ValueError(f'Invalid date {path}:{lineno}')
    value,code=decode_value(raw_value)
    extra={k:v for k,v in row.items() if k not in ('nom','date',metric)}
    key=(name,day,tuple(sorted(extra.items())))
    if key in seen:duplicates.add(str(key))
    seen.add(key);dates.add(day);geographies.add(name)
    counts[code]+=1;counts['rows']+=1
    fh.write(json.dumps({'inrb_commit':commit,'inrb_csv_path':path,
     'inrb_csv_sha256':sha,'inrb_csv_row_number':lineno,
     'metric_id':metric,'geography_raw':name,'date_raw':day,
     'extra_columns_raw':extra,'value_raw':raw_value,'value_parsed':value,
     'value_status':code,'candidate_provenance_class':candidate_policy(metric),
     'date_matched_registry_sources':by_date.get(day,[]),
     'pdf_cell_confirmed':False,'approved_for_analysis':False},ensure_ascii=False,separators=(',',':'))+'\n')
   if duplicates:exceptions.append({'metric':metric,'problem':'duplicate_source_keys','examples':sorted(duplicates)[:8]})
   totals.update(counts)
   summaries.append({'metric_id':metric,'csv_path':path,'source_csv_sha256':sha,
    'rows':counts['rows'],'numeric_values':counts['NUMERIC_UNVERIFIED'],
    'ND_values':counts['NOT_REPORTED'],'other_missing':counts['MISSING_OR_NOT_APPLICABLE'],
    'unparseable':counts['UNPARSEABLE'],'unique_geo_labels':len(geographies),
    'first_date':min(dates) if dates else None,'last_date':max(dates) if dates else None,
    'duplicate_keys':len(duplicates),'transcription_policy':candidate_policy(metric)})
 result={'schema_version':'bdbv-inrb-staged-series-v1','status':'INRB_SERIES_STAGED_NOT_PDF_VERIFIED',
 'inrb_commit':commit,'source_repository':REPO,'metric_files':len(summaries),
 'counts':dict(totals),'datasets':summaries,'exceptions':exceptions,
 'provenance_notice':'Date matches do not prove the value came from that PDF; INRB data may be carried forward, derived, revised or sourced separately.',
 'approved_observations':0}
 (out/'inrb_staging_summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k!='datasets'},ensure_ascii=False,indent=2))
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--registry',type=Path,default=Path('state/registry.json'))
 p.add_argument('--inrb-commit',required=True)
 p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();stage(a.registry,a.inrb_commit,a.out)
