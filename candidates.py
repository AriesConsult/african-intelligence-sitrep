"""Flatten extracted table candidates to audit-friendly CSV; no clinical claims or approval."""
from __future__ import annotations
import csv
import json
import re
from pathlib import Path

NUM = re.compile(r'^\s*(\d[\d.\s\u202f\u00a0,]*)(\s*%?)\s*$')

def parsed_numeric(raw:str) -> tuple[str,str]:
    """Conservative French/English table numbers; count cells must be integers."""
    s=str(raw).strip().replace('\u202f',' ').replace('\u00a0',' ')
    if s.upper() in ('','-','…','...','ND','NA','N/A'):return '',''
    m=NUM.fullmatch(s)
    if not m:return '',''
    v=m.group(1).strip();unit='percent' if s.strip().endswith('%') else 'count'
    if ',' in v and '.' in v:return '',''
    if unit=='percent':
        v=v.replace(' ','').replace(',','.')
        if not re.fullmatch(r'\d{1,3}(?:\.\d{1,2})?',v):return '',''
    else:
        if '.' in v or ',' in v:
            sep='.' if '.' in v else ','
            if not re.fullmatch(r'\d{1,3}(?:'+re.escape(sep)+r'\d{3})+',v.replace(' ','')):return '',''
            v=v.replace(sep,'')
        v=v.replace(' ','')
        if not v.isdigit():return '',''
    try:n=float(v)
    except ValueError:return '',''
    if n<0 or (unit=='percent' and n>100):return '',''
    return format(n,'.9g'),unit

def rows_from_extraction(doc:dict)->list[dict]:
    rows=[]
    for t in doc.get('tables',[]):
        cells=t.get('rows',[])
        if not cells:continue
        header=cells[0]
        for i,row in enumerate(cells[1:],start=2):
            if len(row)<2:continue
            label=str(row[0]).strip().replace('\n',' ')
            if not label or len(label)>240:continue
            # Preserve source row rather than reverse-engineer an unknown
            # table's indicator/denominator from heuristics.
            for c in range(1,len(row)):
                raw=str(row[c]).strip()
                value,unit=parsed_numeric(raw)
                if not value:continue
                rows.append({'report_number':doc.get('report_number'),
                             'source_sha256':doc.get('sha256'),
                             'source_url':doc.get('source_url'),
                             'page':t.get('page'),'table_id':t.get('table_id'),
                             'table_context':t.get('title_context',''),
                             'indicator_families':'|'.join(t.get('indicator_families',[])),
                             'row_label':label,'column_index':c+1,
                             'column_header':header[c] if c<len(header) else '',
                             'raw_value':raw,'candidate_numeric':value,'unit_hint':unit,
                             'full_source_row':json.dumps(row,ensure_ascii=False),
                             'validation_status':'REVIEW_REQUIRED'})
    return rows


def write_csv(output:Path,documents:list[dict])->int:
    rows=[r for d in documents for r in rows_from_extraction(d)]
    keys=['report_number','source_sha256','source_url','page','table_id','table_context',
          'indicator_families','row_label','column_index','column_header',
          'raw_value','candidate_numeric','unit_hint','full_source_row','validation_status']
    with output.open('w',encoding='utf-8',newline='') as fh:
        writer=csv.DictWriter(fh,fieldnames=keys);writer.writeheader();writer.writerows(rows)
    return len(rows)
