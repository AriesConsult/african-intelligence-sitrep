#!/usr/bin/env python3
"""Audit INRB PDF holdings against our registry; never silently ingest leads."""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
import requests,pymupdf

REPO='INRB-UMIE/BDBV2026-Data'
RX=re.compile(r'^data/insp_sitrep/raw/SitRep_MVE_(\d+)[-_].*\.pdf$',re.I)

def run(registry_path,commit,out):
 if not re.fullmatch(r'[a-f0-9]{40}',commit):raise ValueError('Pin INRB to full commit SHA')
 reg=json.loads(registry_path.read_text(encoding='utf-8'))
 ours={}
 for d in reg['documents'].values():ours.setdefault(d['report_number'],[]).append({'source_sha256':d['sha256'],'report_date':d.get('report_date')})
 url=f'https://api.github.com/repos/{REPO}/git/trees/{commit}?recursive=1'
 r=requests.get(url,timeout=90,headers={'Accept':'application/vnd.github+json'});r.raise_for_status()
 tree=r.json()
 if tree.get('truncated'):raise RuntimeError('INRB tree truncated')
 entries=[]
 for item in tree['tree']:
  match=RX.match(item['path']) if item['type']=='blob' else None
  if match:entries.append({'number':int(match.group(1)),'path':item['path'],'git_blob_sha':item['sha'],'git_blob_size':item.get('size')})
 by_num={}
 for item in entries:by_num.setdefault(item['number'],[]).append(item)
 new_nums=sorted(set(by_num)-set(ours))
 evidence=[]
 for n in new_nums:
  for item in by_num[n]:
   origin=f'https://raw.githubusercontent.com/{REPO}/{commit}/{item["path"]}'
   state={'report_number':n,'source_url':origin,'inrb_path':item['path'],'status':'SOURCE_LEAD_UNVERIFIED'}
   try:
    resp=requests.get(origin,timeout=120);resp.raise_for_status();raw=resp.content
    # INRB stores large PDFs with Git LFS. raw.githubusercontent.com returns
    # the pointer, not the PDF. Retrieve the pinned revision through GitHub media.
    if raw.startswith(b'version https://git-lfs.github.com/spec/v1'):
     media=f'https://media.githubusercontent.com/media/{REPO}/{commit}/{item["path"]}'
     resp=requests.get(media,timeout=180);resp.raise_for_status();raw=resp.content
     state['retrieval_url']=media
    if len(raw)>35000000 or not raw.startswith(b'%PDF-'):raise ValueError('invalid PDF signature/size, or unresolved LFS pointer')
    with pymupdf.open(stream=raw,filetype='pdf') as doc:
     if doc.is_encrypted or doc.page_count<1:raise ValueError('encrypted/empty PDF')
     cover=doc[0].get_text(sort=True)
     epidemic=bool(re.search(r'17\s*(?:eme|ème|e)|MVE.?17|MVE.?BDBV|Bundibugyo',cover,re.I))
     numbers={int(x) for x in re.findall(r'SitRep\s*(?:MVE\s*)?N?\s*[°ºo.]?\s*(\d{1,3})',cover,re.I)}
     state.update({'source_pdf_sha256':hashlib.sha256(raw).hexdigest(),'pdf_bytes':len(raw),
       'pdf_pages':doc.page_count,'cover_excerpt':cover[:1100],
       'cover_epidemic_identity':epidemic,'cover_report_numbers':sorted(numbers),
       'status':'SOURCE_LEAD_COVER_CONFIRMED_REQUIRES_HUMAN_ACCEPTANCE' if epidemic and n in numbers else 'SOURCE_LEAD_COVER_INCONCLUSIVE'})
   except Exception as exc:state.update({'status':'SOURCE_LEAD_DOWNLOAD_OR_PDF_ERROR','error':str(exc)[:190]})
   evidence.append(state)
 crosswalk=[]
 for n in sorted(set(ours)|set(by_num)):
  crosswalk.append({'report_number':n,'ours':ours.get(n,[]),'inrb_pdf_files':by_num.get(n,[]),
    'presence':'BOTH' if n in ours and n in by_num else 'INRB_ONLY' if n in by_num else 'AFRICAN_INTELLIGENCE_ONLY'})
 result={'schema_version':'bdbv-inrb-source-crosswalk-v1','inrb_commit':commit,
  'our_documents':len(reg['documents']),'our_report_numbers':len(ours),
  'inrb_pdf_files':len(entries),'inrb_report_numbers':len(by_num),
  'inrb_only_report_numbers':new_nums,'our_only_report_numbers':sorted(set(ours)-set(by_num)),
  'inrb_only_source_evidence':evidence,'crosswalk':crosswalk,
  'policy':'NO_INRB_ONLY_REPORT_AUTOMATICALLY_IMPORTED_OR_APPROVED'}
 out.mkdir(parents=True,exist_ok=True)
 (out/'inrb_source_crosswalk.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k!='crosswalk'},indent=2,ensure_ascii=False)[:6500])
 if any(x['status']=='SOURCE_LEAD_DOWNLOAD_OR_PDF_ERROR' for x in evidence):raise SystemExit(1)
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--registry',type=Path,default=Path('state/registry.json'))
 p.add_argument('--inrb-commit',required=True)
 p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();run(a.registry,a.inrb_commit,a.out)
