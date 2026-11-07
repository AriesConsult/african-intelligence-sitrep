"""Conservative extraction: archive original PDF + keep page-level table cells.

IMPORTANT: These are candidates. No table value is deemed approved or published.
"""
from __future__ import annotations
import hashlib
import io
import re
from datetime import date
from typing import Any
import pymupdf as fitz
import pdfplumber

REPORT_NUMBER = re.compile(r'SitRep\s*(?:N\s*[°ºo.]*)?\s*(\d{1,3})',re.I)
DATE = re.compile(r'(?:Date\s+de\s+rapportage|Date\s+du\s+rapport)\s*:?\s*(\d{1,2})\s*(janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre|/|\.|-|\d)', re.I)
SECTIONS = {
 'contact_tracing': re.compile(r'contact|suivi',re.I),
 'alert_management': re.compile(r'alerte|investigu|valid[eé]e|pr[eé]lev',re.I),
 'laboratory': re.compile(r'laboratoire|PCR|positivit[eé]|test[s]? r[eé]alis[eé]',re.I),
 'treatment_capacity': re.compile(r'CTE|lit[s]?|occupation|hospitalis',re.I),
 'vaccination': re.compile(r'vaccin|dose[s]?|immunis',re.I),
 'poe_screening': re.compile(r'point[s]? d.ent[rée]e|PoE|PoC|screening|voyageurs|contr[oô]le',re.I),
 'burials_ipc': re.compile(r'inhumation|enterrement|IPC|pr[eé]vention.*infection',re.I),
}


def classify_table(header: str) -> list[str]:
    return [name for name,rx in SECTIONS.items() if rx.search(header)]


def serializable_table(t: list[list[Any]]) -> list[list[str]]:
    return [[str(x).strip().replace('\x00','') if x is not None else '' for x in row] for row in t]


def extract_pdf(raw:bytes,*,url:str,expected_number:int | None=None)->dict:
    if not raw.startswith(b'%PDF-'):raise ValueError('Downloaded content is not a PDF')
    sha=hashlib.sha256(raw).hexdigest()
    doc=fitz.open(stream=raw,filetype='pdf')
    if doc.is_encrypted or len(doc)<1:raise ValueError('Encrypted or empty PDF')
    first=doc[0].get_text(sort=True)
    first_clean=' '.join(first.split())
    raw_title_date=re.search(r'(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](2026)(?!\d)',first_clean)
    report_date=(f'{raw_title_date.group(3)}-{int(raw_title_date.group(2)):02d}-{int(raw_title_date.group(1)):02d}' if raw_title_date else None)
    if report_date:
        try: date.fromisoformat(report_date)
        except ValueError: report_date=None
    if not report_date:
        french_months={'janvier':1,'fevrier':2,'mars':3,'avril':4,'mai':5,'juin':6,'juillet':7,'aout':8,'septembre':9,'octobre':10,'novembre':11,'decembre':12}
        import unicodedata
        clean=''.join(c for c in unicodedata.normalize('NFKD',first_clean.lower()) if not unicodedata.combining(c))
        dm=re.search(r'(?<!\d)(\d{1,2})\s+(janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre)\s+2026',clean)
        if dm:
            try:report_date=date(2026,french_months[dm.group(2)],int(dm.group(1))).isoformat()
            except ValueError:pass
    # The official 2025 16th Ebola epidemic has a similar SitRep title.
    # Do not accept unless 2026/17th-epidemic identity is present in the cover.
    if not re.search(r'2026',first_clean) or not re.search(r'(?:17\s*(?:ème|e|eme)|MVE.?BDBV|Bundibugyo|MVE.?17)',first_clean,re.I):
        raise ValueError('Cover does not verify a 2026 17th-epidemic SitRep')
    nm=REPORT_NUMBER.search(first_clean)
    report_no=int(nm.group(1)) if nm else None
    if report_no is not None and expected_number and report_no!=expected_number:
        raise ValueError(f'Filename/report-number mismatch: {expected_number} != {report_no}')
    pages=[];tables=[]
    with pdfplumber.open(io.BytesIO(raw)) as pdoc:
        for idx,page in enumerate(pdoc.pages):
            text=doc[idx].get_text(sort=True)
            pages.append({'page':idx+1,'text':text})
            methods=[{'vertical_strategy':'lines','horizontal_strategy':'lines','intersection_tolerance':4},
                     {'vertical_strategy':'text','horizontal_strategy':'text','text_tolerance':3}]
            seen=set()
            for method_index,settings in enumerate(methods):
                try:found=page.find_tables(table_settings=settings)
                except Exception:found=[]
                # Most SitReps are digitally generated; OCR is not performed.
                for t in found:
                    rows=serializable_table(t.extract() or [])
                    if len(rows)<2 or max((len(x) for x in rows),default=0)<2:continue
                    fingerprint=hashlib.sha256(repr(rows).encode('utf-8')).hexdigest()[:12]
                    if fingerprint in seen:continue
                    seen.add(fingerprint)
                    y0=max(0,t.bbox[1]-110)
                    try:nearby=page.crop((0,y0,page.width,t.bbox[1])).extract_text() or ''
                    except Exception:nearby=''
                    title_candidates=re.findall(r'Tableau\s*(?:n[°ºo]\s*)?\d+[^\n]{0,170}', nearby, re.I)
                    title=title_candidates[-1].strip() if title_candidates else nearby.strip()[-160:]
                    signature=' '.join([' '.join(row) for row in rows[:4]])+' '+title
                    tables.append({'page':idx+1,'table_id':f'p{idx+1}-t{len(tables)+1}',
                                   'extractor': 'pdfplumber-lines' if method_index==0 else 'pdfplumber-text',
                                   'bbox': [round(float(v),1) for v in t.bbox],
                                   'title_context':title,
                                   'indicator_families': classify_table(signature),
                                   'rows':rows,
                                   'review_status':'unverified'})
    return {'schema_version':'sitrep-extract-0.1','report_number':report_no or expected_number,
            'source_url':url,'sha256':sha,'bytes':len(raw),'n_pages':len(doc),'report_date':report_date,
            'cover_excerpt':first_clean[:2000], 'tables':tables, 'pages':pages,
            'extract_status':'unverified','publication_status':'NOT_PUBLISHED'}
