#!/usr/bin/env python3
"""Batch-discover + extract 2026 INSP SitReps, but NEVER publish unreviewed data."""
from __future__ import annotations
import argparse
import json
import hashlib
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from discovery import discover_all,session,get
from extraction import extract_pdf
from candidates import write_csv

# In INRB/GitHub LFS, raw.githubusercontent URLs may return an LFS pointer.
GITHUB_LFS = 'https://media.githubusercontent.com/media/INRB-UMIE/BDBV2026-Data/main/'


def pdf_download(s,source):
    url=source['url']
    urls=[url]
    prefix='https://raw.githubusercontent.com/INRB-UMIE/BDBV2026-Data/main/'
    if url.startswith(prefix): urls.append(GITHUB_LFS+url[len(prefix):])
    errors=[]
    for candidate in urls:
        try:
            r=get(s,candidate,timeout=65)
            if len(r.content)>35_000_000:raise ValueError('PDF exceeds 35MB safety cap')
            if r.content.startswith(b'%PDF-'):return r.content,candidate
            errors.append(f'Not a PDF at {candidate[:90]}')
        except Exception as e:errors.append(str(e)[:150])
    raise RuntimeError('; '.join(errors))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',default='output')
    parser.add_argument('--limit',type=int,default=8,help='most recent reports to inspect (default 8; 0 = all)')
    parser.add_argument('--pause',type=float,default=1.25,help='delay between downloads; be considerate of source servers')
    parser.add_argument('--offline-dir',type=Path,help='read local PDF files instead of network (for tests)')
    args=parser.parse_args(argv)
    out=Path(args.out);pdf_dir=out/'source_pdfs';ex_dir=out/'unverified_extractions';
    pdf_dir.mkdir(parents=True,exist_ok=True);ex_dir.mkdir(parents=True,exist_ok=True)
    s=session();errors=[];results=[];extracted=[]
    if args.offline_dir:
        sources=[{'number':0,'sources':[{'url':str(p),'basename':p.name,'provider':'local-test'}]}
                 for p in sorted(args.offline_dir.glob('*.pdf'))]
    else:
        sources,errors=discover_all(s)
    if args.limit>0:sources=sources[:args.limit]
    for i,item in enumerate(sources):
        number=item['number'];successful=False
        for source in item['sources']:
            url=source['url']
            try:
                if args.offline_dir:raw=Path(url).read_bytes();actual='local:'+Path(url).name
                else:raw,actual=pdf_download(s,source)
                record=extract_pdf(raw,url=actual,expected_number=number or None)
                number=record['report_number'] or number
                sha=record['sha256'][:12]
                stem=f'SitRep_{int(number):03d}_2026_{sha}'
                (pdf_dir/(stem+'.pdf')).write_bytes(raw)
                (ex_dir/(stem+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
                extracted.append(record)
                results.append({'report_number':number,'provider':source['provider'],
                                'source_url':actual,'sha256':record['sha256'],
                                'tables':len(record['tables']),'pages':record['n_pages'],
                                'status':'unverified','published':False})
                successful=True;print(f'SitRep {number}: {record["n_pages"]} pages, {len(record["tables"])} candidate tables; quarantined for review')
                break
            except Exception as e:errors.append(f'SitRep {number} ({source["provider"]}): {str(e)[:200]}')
        if not successful:print(f'SitRep {number} was not extracted',file=sys.stderr)
        if not args.offline_dir:time.sleep(max(0,args.pause))
    candidate_count=write_csv(out/'unverified_table_cells.csv',extracted)
    index={'generated_at':datetime.now(timezone.utc).isoformat(),
           'publication_status':'NOT_PUBLISHED',
           'purpose':'QA review only; do not expose as dashboard statistics',
           'processed':results,'errors':errors,'discovered_count':len(sources),
           'unverified_numeric_candidates':candidate_count}
    (out/'review_manifest.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'processed':len(results),'errors':len(errors),'quarantine_dir':str(ex_dir)},indent=2))
    if not results:sys.exit(2)

if __name__=='__main__':main()
