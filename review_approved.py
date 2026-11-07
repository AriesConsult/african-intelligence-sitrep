"""Manually approved observations can be published only if they match saved source cells.

The reviewer fills reviewed/approved_observations.csv. Candidate table cells remain
in review_queue/report_XXX_SHA.json with original page, table and SHA256.
"""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path
from candidates import parsed_numeric

HUMAN_METRICS={
    'contacts_seen','contacts_to_follow','contact_follow_up_rate',
    'alerts_received','alerts_investigated','alert_investigation_rate','alerts_validated',
    'tests_performed','tests_positive','test_positivity_rate',
    'cte_occupied_beds','cte_available_beds','cte_admissions',
    'vaccinations_administered','poe_travellers_screened',
    'safe_burials','community_deaths_reported',
}

def read_approvals(file:Path,queue:Path)->tuple[list[dict],list[dict]]:
    accepted=[];errors=[]
    if not file.is_file():return accepted,errors
    with file.open(encoding='utf-8-sig',newline='') as fh:
        reader=csv.DictReader(fh)
        for lineno,row in enumerate(reader,start=2):
            if not row or not any(row.values()):continue
            try:
                number=int(row['report_number']);sha=str(row['source_sha256']).lower();date=str(row['date'])
                if not (1<=number<=400 and len(sha)==64 and all(c in '0123456789abcdef' for c in sha)):
                    raise ValueError('invalid report or SHA')
                docpath=queue/f'report_{number:03d}_{sha[:12]}.json'
                doc=json.loads(docpath.read_text(encoding='utf-8'))
                if doc['sha256']!=sha or doc['report_date']!=date:raise ValueError('source identity mismatch')
                metric=str(row['metric_id']).strip();unit=str(row['unit']).strip()
                if metric not in HUMAN_METRICS or unit not in ('count','percent'):
                    raise ValueError('metric/unit not approved for publication')
                reviewer=str(row['reviewed_by'] or '').strip()
                if len(reviewer)<3:raise ValueError('named reviewer required')
                page=int(row['page']);tableid=str(row['table_id'])
                table=[t for t in doc['tables'] if int(t['page'])==page and t['table_id']==tableid]
                if len(table)!=1:raise ValueError('table not found in archived source')
                header_rows=table[0]['rows'][:3]
                found=[]
                for hr in header_rows:
                    for ci,h in enumerate(hr):
                        if h.strip()!=str(row['column_header']).strip():continue
                        for rr in table[0]['rows'][1:]:
                            if rr and rr[0].strip()==str(row['row_label']).strip() and ci<len(rr) and rr[ci].strip()==str(row['raw_value']).strip():
                                found.append(rr[ci])
                if not found:raise ValueError('raw cell cannot be reproduced from the original PDF extraction')
                raw_num,raw_unit=parsed_numeric(found[0] if unit!='percent' or '%' in found[0] else found[0]+'%')
                if not raw_num or raw_unit!=unit:raise ValueError('raw cell not numeric for declared unit')
                val=float(row['value']);raw_float=float(raw_num)
                if not math.isfinite(val) or val<0 or abs(val-raw_float)>0.01:
                    raise ValueError('review value differs from primary PDF cell')
                if (unit=='percent' and val>100) or (unit=='count' and (val>50_000_000 or not val.is_integer())):
                    raise ValueError('out-of-range value')
                if str(row['scope']).strip()!='DRC':
                    raise ValueError('only explicit national scope supported (never infer zone sums)')
                accepted.append({'metric_id':metric,'value':int(val) if unit=='count' else round(val,2),
                    'unit':unit,'scope':'DRC','date':date,'report_number':number,
                    'evidence_status':'human_verified',
                    'verification':'reviewer_checked_against_source_pdf_cell',
                    'reviewed_by':reviewer,'review_note':str(row.get('review_note',''))[:300],
                    'source_url':doc['source_url'],'source_sha256':sha,'page':page,'table_id':tableid,
                    'reporting_window':'See original SitRep; preserve metric definition and units',
                })
            except Exception as e:errors.append({'line':lineno,'reason':str(e)[:200]})
    return accepted,errors
