#!/usr/bin/env python3
"""Conservative PDF-banner vs INRB transcription comparison.

Agreement of two transcriptions of the same PDF is concordance, not independent
verification of the outbreak metric. All comparison results stay review-only.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,io,json,re,unicodedata
from collections import Counter
from datetime import date,timedelta
from pathlib import Path
import requests

METRICS={
 'national_cumulative_confirmed_cases':'insp_sitrep__national_cumulative_confirmed_cases__daily.csv',
 'national_cumulative_confirmed_deaths':'insp_sitrep__national_cumulative_confirmed_deaths__daily.csv',
}

def norm(s):
 s=''.join(c for c in unicodedata.normalize('NFKD',str(s).lower()) if not unicodedata.combining(c))
 return re.sub(r'\s+',' ',s).strip()

def lines(page):
 out=[]
 for block in page['text_blocks']:
  for line in block.get('lines',[]):
   for span in line['spans']:
    s=norm(span['text']);x0,y0,x1,y1=span['bbox']
    if s:out.append({'text':s,'bbox':[x0,y0,x1,y1],'x':(x0+x1)/2,'y':(y0+y1)/2})
 return out

def banner_candidates(page,metric):
 """Return possible national-banner values with exact PDF page coordinates.

 Never select based on agreement with INRB; ambiguous values stay unresolved.
 """
 spans=lines(page)
 table_starts=[s['y'] for s in spans if re.match(r'^tableau\s+(?:[ivx]+|\d+)',s['text']) and s['y']>220]
 summary_end=min(table_starts)-5 if table_starts else 470
 numeric=[]
 for s in spans:
  txt=s['text'].strip(' *')
  m=re.match(r'^(\d[\d\s]{0,8})(?:\s*[·(*]|$)',txt)
  if m and len(re.sub(r'\D','',m.group(1)))<=6:
   digits=re.sub(r'\D','',m.group(1))
   if digits:numeric.append({**s,'value':int(digits)})
 is_deaths=metric.endswith('deaths')
 anchors=[]
 for s in spans:
  text=s['text']
  if s['y']>min(470,summary_end):continue
  if is_deaths:
   hit=('deces' in text and ('cumul' in text or len(text)<=26))
  else:
   hit=('cas confirm' in text or ('cas' in text and (len(text)<=22 or 'cumul' in text)))
  if not hit or (not is_deaths and 'suspect' in text):continue
  if len(text)>45:continue
  nearby=[t for t in spans if abs(t['x']-s['x'])<42 and abs(t['y']-s['y'])<48]
  context=' '.join(t['text'] for t in nearby)
  if is_deaths and not ('confirm' in context or 'cumul' in context):continue
  if not is_deaths and not ('confirm' in context or ('cumul' in context and 'suspect' not in context)):continue
  anchors.append(s)
 ranked=[]
 for a in anchors:
  for n in numeric:
   dx=abs(a['x']-n['x']);dy=abs(a['y']-n['y'])
   if dx>60 or dy>100 or dy<3 or n['y']>summary_end+8:continue
   score=round(dx/60+dy/100,4)
   ranked.append({'value':n['value'],'score':score,'label':a['text'],
      'label_bbox':a['bbox'],'value_bbox':n['bbox'],'value_raw':n['text']})
 ranked.sort(key=lambda c:c['score'])
 return ranked

def choose(candidates):
 if not candidates:return {'status':'NO_PDF_BANNER_CANDIDATE','pdf_value':None,'candidate_count':0}
 first=candidates[0]
 near={p['value'] for p in candidates if p['score']<=first['score']+0.13}
 if len(near)>1:return {'status':'AMBIGUOUS_PDF_BANNER_CANDIDATE','pdf_value':None,'candidate_count':len(candidates)}
 return {'status':'PDF_BANNER_CANDIDATE_REVIEW_REQUIRED','pdf_value':first['value'],
         'candidate_count':len(candidates),'pdf_label':first['label'],
         'pdf_label_bbox':first['label_bbox'],'pdf_value_bbox':first['value_bbox'],
         'pdf_raw_text':first['value_raw']}

def fetch_inrb_csv(commit,metric,timeout=60):
 if not re.fullmatch(r'[a-f0-9]{40}',commit):raise ValueError('Commit must be full SHA')
 url=f'https://raw.githubusercontent.com/INRB-UMIE/BDBV2026-Data/{commit}/data/insp_sitrep/processed/{METRICS[metric]}'
 response=requests.get(url,timeout=timeout);response.raise_for_status()
 raw=response.content
 rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
 dates={}
 for r in rows:
  if r.get('nom')=='DRC':
   day=r['date'];value=r[metric].strip()
   if day in dates:raise ValueError(f'Duplicate INRB national date {day}')
   dates[day]=value
 return {'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'values':dates,'rows':len(rows)}

def run(full_dir,registry_path,commit,out,inrb_inputs=None):
 reg=json.loads(Path(registry_path).read_text(encoding='utf-8'))
 audit=json.loads((full_dir/'page_extraction_audit.json').read_text(encoding='utf-8'))
 if audit.get('status')!='ALL_ARCHIVED_PDFS_EXTRACTED_FIDELITY_REVIEW_PENDING':raise ValueError('Source PDF verification not complete')
 curated=inrb_inputs or {m:fetch_inrb_csv(commit,m) for m in METRICS}
 ledger=[];counts=Counter()
 for rec in audit['records']:
  no,sha=rec['report_number'],rec['source_sha256'];key=f'{no:03d}:{sha}'
  if key not in reg['documents']:raise ValueError(f'Unregistered {key}')
  file=full_dir/rec['extraction_file']
  if hashlib.sha256(file.read_bytes()).hexdigest()!=rec['compressed_sha256']:raise ValueError(f'File checksum mismatch {key}')
  with gzip.open(file,'rt',encoding='utf-8') as fp:doc=json.load(fp)
  if doc['source_sha256']!=sha:raise ValueError(f'Source hash mismatch {key}')
  report_date=reg['documents'][key]['report_date'];page=doc['pages'][0]
  for metric in METRICS:
   matches=banner_candidates(page,metric);cand=choose(matches)
   inrb_value=curated[metric]['values'].get(report_date)
   parsed=int(inrb_value) if inrb_value and re.fullmatch(r'\d+',inrb_value) else None
   date_offset=None
   if parsed is None:outcome='INRB_DATE_UNAVAILABLE'
   elif cand['pdf_value'] is None:outcome=cand['status']
   elif cand['pdf_value']==parsed:outcome='AGREES_WITH_INRB_PENDING_SOURCE_VISUAL_QA'
   else:
    outcome='DIFFERENCE_REVIEW_REQUIRED'
    # A one-day offset is a discovery lead, NOT automatic date correction.
    for shift in (-1,1):
     alternate_day=(date.fromisoformat(report_date)+timedelta(days=shift)).isoformat()
     alternative=curated[metric]['values'].get(alternate_day)
     if alternative and re.fullmatch(r'\d+',alternative) and int(alternative)==cand['pdf_value']:
      date_offset=shift
      outcome='POSSIBLE_REPORTING_DATE_ALIGNMENT_REVIEW_REQUIRED'
      break
   counts[outcome]+=1
   ledger.append({'report_number':no,'report_date':report_date,'source_pdf_sha256':sha,
       'pdf_page':1,'metric_id':metric,'pdf_value_candidate':cand['pdf_value'],
       'raw_text':cand.get('pdf_raw_text'),'pdf_label':cand.get('pdf_label'),
       'pdf_label_bbox':cand.get('pdf_label_bbox'),'pdf_value_bbox':cand.get('pdf_value_bbox'),
       'candidate_count':cand['candidate_count'],'inrb_value':parsed,
       'inrb_csv_path':'data/insp_sitrep/processed/'+METRICS[metric],
       'inrb_csv_sha256':curated[metric]['sha256'],'inrb_commit':commit,
       'outcome':outcome,'possible_inrb_date_offset_days':date_offset,'approved_for_analysis':False})
 out.mkdir(parents=True,exist_ok=True)
 with (out/'national_banner_comparison.csv').open('w',newline='',encoding='utf-8') as fp:
  writer=csv.DictWriter(fp,fieldnames=list(ledger[0]));writer.writeheader()
  for row in ledger:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()})
 report={'schema_version':'bdbv-inrb-national-banner-reconciliation-v1','source_repository':'INRB-UMIE/BDBV2026-Data',
 'inrb_commit':commit,'documents':len(audit['records']),'observations_compared':len(ledger),
 'outcomes':dict(counts),'inrb_inputs':{k:{a:v for a,v in c.items() if a!='values'} for k,c in curated.items()},
 'records':ledger,'status':'REVIEW_ONLY_NOT_APPROVED',
 'caveats':['Both transcriptions may derive from the same INSP SitRep and thus are not epidemiologically independent.',
            'Coordinates and values are heuristic banner candidates; require visual source review before approval.',
            'Different source versions and date definitions can create legitimate mismatches.']}
 (out/'national_banner_comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--full-pages',type=Path,required=True)
 p.add_argument('--registry',type=Path,default=Path('state/registry.json'))
 p.add_argument('--inrb-commit',required=True)
 p.add_argument('--out',type=Path,required=True)
 a=p.parse_args()
 run(a.full_pages,a.registry,a.inrb_commit,a.out)
