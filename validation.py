"""Allowlist-only SitRep table validation. Never infer national rates from summed zones.

AUTO_VALIDATED means deterministic consistency checks passed; it is NOT a claim
that a human verified the source PDF. All other cells remain quarantined.
"""
from __future__ import annotations
import re
import unicodedata
from datetime import date
from candidates import parsed_numeric

SCHEMA = 'bdbv-sitrep-feed-v1'
PAIRS = [
    # Strict header synonyms, and required internal consistency of reported ratio.
    {'family':'contact_tracing','numerator':'contacts_seen','denominator':'contacts_to_follow',
     'rate':'contact_follow_up_rate','num':r'\b(?:contacts?\s+(?:vu[es]?|suivis?|visites?))\b',
     'den':r'\b(?:contacts?\s+(?:a\s+suivre|attendus?|recenses?|enregistres?))\b',
     'pct':r'\b(?:taux\s+de\s+suivi|pourcentage\s+(?:de\s+)?suivi)\b'},
    {'family':'alert_management','numerator':'alerts_investigated','denominator':'alerts_received',
     'rate':'alert_investigation_rate','num':r'\b(?:alertes?\s+(?:investiguees?|verifiees?))\b',
     'den':r'\b(?:alertes?\s+(?:recues?|signalees?|notifiees?))\b',
     'pct':r'\b(?:taux\s+d.?investigation|pourcentage\s+d.?investigation)\b'},
    {'family':'laboratory','numerator':'tests_positive','denominator':'tests_performed',
     'rate':'test_positivity_rate','num':r'\b(?:tests?\s+positifs?|echantillons?\s+positifs?)\b',
     'den':r'\b(?:tests?\s+(?:realises?|effectues?|analyses?)|echantillons?\s+testes?)\b',
     'pct':r'\b(?:taux\s+de\s+positivite|positivite\s*\(%?\))\b'},
]

def norm(value:object)->str:
    s=unicodedata.normalize('NFKD',str(value or '').lower())
    s=''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+',' ',s.replace('\n',' ')).strip()

def value(s:str,unit:str)->float|None:
    n,u=parsed_numeric(s if unit!='percent' or '%' in str(s) else str(s)+'%')
    if not n or u!=unit:return None
    try:return float(n)
    except: return None

def national_total_row(label:str)->bool:
    s=norm(label)
    return bool(re.fullmatch(r'(?:total|total\s+general|ensemble|national|rdc|r\.?d\.?c\.?|republique\s+democratique\s+du\s+congo)(?:\s*\(.*\))?',s))

def validate_document(doc:dict)->tuple[list[dict],list[dict]]:
    accepted=[];flags=[]
    try: dt=date.fromisoformat(doc.get('report_date') or '')
    except Exception:
        return [],[{'reason':'no_verifiable_cover_date','report_number':doc.get('report_number')}]
    if dt.year!=2026:
        return [],[{'reason':'wrong_year','report_number':doc.get('report_number')}]
    if not doc.get('sha256') or not doc.get('source_url'):
        return [],[{'reason':'missing_provenance'}]
    for t in doc.get('tables',[]):
        rawrows=t.get('rows',[])
        if len(rawrows)<2:continue
        families=t.get('indicator_families') or []
        # Treat multiple header rows defensively; only one unambiguous mapping allowed.
        for rule in PAIRS:
            if rule['family'] not in families:continue
            candidates=[]
            for header_idx in range(min(3,len(rawrows)-1)):
                headers=[norm(x) for x in rawrows[header_idx]]
                matches={k:[i for i,h in enumerate(headers) if re.search(rule[k],h)] for k in ('num','den','pct')}
                if all(len(matches[k])==1 for k in matches):
                    idx=[matches[k][0] for k in ('num','den','pct')]
                    if len(set(idx))==3 and min(idx)>0:candidates.append((header_idx,idx))
            if len(candidates)!=1:continue
            head,idx=candidates[0];totalrows=[r for r in rawrows[head+1:] if len(r)>max(idx) and r and national_total_row(str(r[0]))]
            if len(totalrows)!=1:
                flags.append({'reason':'total_row_ambiguous','page':t.get('page'),'table_id':t.get('table_id'),'family':rule['family']})
                continue
            row=totalrows[0]
            numerator=value(row[idx[0]],'count');denominator=value(row[idx[1]],'count');rate=value(row[idx[2]],'percent')
            if (numerator is None or denominator is None or rate is None or denominator<=0
                or numerator>denominator or denominator>50_000_000
                or abs(100*numerator/denominator-rate)>0.65):
                flags.append({'reason':'ratio_or_count_validation_failed','page':t.get('page'),'table_id':t.get('table_id'),'family':rule['family']})
                continue
            p=int(t.get('page') or 0)
            if p<1:continue
            for key,val,unit in [(rule['numerator'],numerator,'count'),(rule['denominator'],denominator,'count'),(rule['rate'],rate,'percent')]:
                accepted.append({
                    'metric_id':key,'value':int(val) if unit=='count' else round(val,2), 'unit':unit,
                    'date':dt.isoformat(),'report_number':int(doc['report_number']),
                    'scope':'DRC','reporting_window':'SitRep observation (not necessarily daily incidence)',
                    'evidence_status':'machine_validated', 'verification':'ratio_matched_within_0.65_percentage_points',
                    'source_url':doc['source_url'],'source_sha256':doc['sha256'],
                    'page':p,'table_id':t['table_id'],
                    'raw_row':row[:], 'table_context':t.get('title_context',''),
                })
    # Two tables should not publish contradictory values for same metric/date.
    bykey={};conflicts=set()
    for r in accepted:
        k=(r['metric_id'],r['date'],r['scope'])
        if k in bykey and bykey[k]['value']!=r['value']:conflicts.add(k)
        bykey.setdefault(k,r)
    if conflicts:
        flags.append({'reason':'conflicting_table_values','keys':[str(k) for k in sorted(conflicts)]})
    return [v for k,v in bykey.items() if k not in conflicts],flags
