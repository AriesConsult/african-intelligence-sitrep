"""Five-table SitRep extractor, using exactly the extracted PDF tables and provenance.

Every value is tied to a report, page, table and original PDF hash. Unavailable
or ambiguous cells are NOT zero. Does not change the INRB case/death baseline.
"""
from __future__ import annotations
import re, unicodedata
from collections import defaultdict
from datetime import date
from candidates import parsed_numeric

SCHEMA='bdbv-sitrep-tables-v1'
PROVINCES={
    'ituri':'Ituri','nord-kivu':'Nord-Kivu','haut-uele':'Haut-Uélé',
    'tshopo':'Tshopo','sud-kivu':'Sud-Kivu','bas-uele':'Bas-Uélé',
    'sud-ubangi':'Sud-Ubangi','nord-ubangi':'Nord-Ubangi',
}

def norm(s):
    s=''.join(c for c in unicodedata.normalize('NFKD',str(s or '').lower()) if not unicodedata.combining(c))
    return re.sub(r'\s+',' ',s.replace('\n',' ').replace('’',"'")).strip()

def scope_of(s):
    s=re.sub(r'[\s-]+','-',norm(s).replace("'",''))
    return PROVINCES.get(s)

def count(s):
    v,u=parsed_numeric(s)
    if u!='count' or not v:return None
    try:
        x=int(v)
        return x if x>=0 and x<50000000 and x==float(v) else None
    except ValueError:return None

def percent(s):
    v,u=parsed_numeric(s)
    return float(v) if u=='percent' and v else None

def ok_rate(n,d,p,tolerance=.65):
    return n is not None and d is not None and 0<=n<=d and d>0 and p is not None and abs(100*n/d-p)<=tolerance

def fraction(s):
    m=re.search(r'(?<!\d)(\d[\d\s]*)\s*/\s*(\d[\d\s]*)(?!\d)',str(s))
    if not m:return None
    a=count(m.group(1));b=count(m.group(2))
    return (a,b) if a is not None and b is not None and b>0 and a<=b else None

def table(doc,number,page=None):
    # Prefer line-grid extraction for actual tabular rows; skip text-grid impostors.
    rx=re.compile(r'\btableau\s*'+str(number)+r'\s*[.:]',re.I)
    candidates=[]
    for t in doc.get('tables',[]):
        if page and t.get('page')!=page:continue
        header=(t.get('title_context') or '')+' '+' '.join(' '.join(str(c or '') for c in r) for r in t.get('rows',[])[:2])
        if rx.search(header) or (number==1 and t.get('page')==2 and any('nouveaux cas' in norm(' '.join(r)) for r in t.get('rows',[])[:5])):
            if t.get('extractor')=='pdfplumber-lines':candidates.append(t)
    if not candidates:return None
    return sorted(candidates,key=lambda t:(len(t.get('rows',[])),-t['page']),reverse=True)[0]

def cell_prov(t,row):
    return {'page':t['page'],'table_id':t['table_id'],'source_row':row}

def report_base(doc):
    try:assert date.fromisoformat(doc['report_date']).year==2026
    except (ValueError,KeyError,AssertionError,TypeError):raise ValueError('Invalid report date')
    if not isinstance(doc.get('report_number'),int):raise ValueError('Missing report number')
    if not re.fullmatch('[a-f0-9]{64}',doc.get('sha256','')):raise ValueError('Missing PDF fingerprint')
    return {'schema_version':SCHEMA,'report_number':doc['report_number'],'date':doc['report_date'],
            'source_url':doc['source_url'],'source_sha256':doc['sha256'],
            'source_role':'INSP original SitRep; corroborated by INRB archive',
            'status':'VALIDATED_WHERE_RECONCILED','tables':{},'quality_flags':[]}

def table_1(doc,output):
    t=table(doc,1)
    if not t:return None
    rows=[]; national=None;flags=[]
    for i,r in enumerate(t['rows']):
        if len(r)<5:continue
        p=scope_of(r[0]);is_total=bool(re.fullmatch('total(?: general)?',norm(r[0]))) or (not norm(r[0]) and count(r[2]) is not None and count(r[3]) is not None and i>=6)
        if not p and not is_total:continue
        nc,c,d,pct=(count(r[1]),count(r[2]),count(r[3]),percent(r[4]))
        if None in (nc,c,d,pct) or d>c or not ok_rate(d,c,pct):
            # The national Total caption can occupy a line below the numeric row.
            if is_total and national is not None:continue
            flags.append({'reason':'table1_invalid_case_death_rate','row':i,'province':p});continue
        row={'scope':p or 'DRC','new_cases_24h':nc,'cumulative_cases':c,'cumulative_deaths':d,
             'reported_cfr_pct':pct,'source':cell_prov(t,i)}
        # Cell can contain split/misaligned zone totals; only accept unambiguous fractions.
        zone=fraction(r[5]) if len(r)>5 else None
        if zone and len(re.findall(r'\d+\s*/\s*\d+',r[5]))==1:
            row['health_zones_affected']=zone[0]
            row['health_zones_total']=zone[1]
        if p:rows.append(row)
        else:national=row
    if len(rows)<2 or national is None:return {'status':'REVIEW_REQUIRED','rows':rows,'flags':flags+[{'reason':'table1_missing_provincial_or_national_totals'}]}
    for key in ('new_cases_24h','cumulative_cases','cumulative_deaths'):
        if sum(x[key] for x in rows)!=national[key]:flags.append({'reason':'table1_province_national_disagreement','field':key})
    if flags:
        return {'status':'REVIEW_REQUIRED','rows':rows,'national':national,'flags':flags}
    return {'status':'MACHINE_VALIDATED','rows':rows,'national':national,'flags':[],'reconciliation':'province counts sum to national totals; reported CFR independently matches'}

def table_2(doc,output):
    # Table 2 is across two pages: page 2 line-grid, page 3 clean text-grid.
    first=table(doc,2)
    if not first:return None
    other=next((t for t in doc.get('tables',[]) if t['page']==first['page']+1 and t.get('extractor')=='pdfplumber-text'
               and len(t.get('rows',[]))>40 and max(map(len,t['rows']))==8),None)
    if not other:
        return {'status':'REVIEW_REQUIRED','rows':[],'flags':[{'reason':'table2_continuation_not_extractable'}]}
    records=[];provrows=[];unallocated=[];issues=[];province=None
    def add(label,c,d,pct,source,nc=None,dc=None,dh=None,dt=None):
        nonlocal province
        if not label:return
        p=scope_of(label)
        # Tshopo is simultaneously a province and one of its health zones.
        t1=output['tables'].get('table_1') or {}
        known={v['scope']:v for v in t1.get('rows',[])}
        if p and province==p and known.get(p) and c!=known[p]['cumulative_cases']:
            p=None
        if norm(label)=='a ventiler' and province and d is not None:
            unallocated.append({'province':province,'unallocated_deaths':d,'source':source});return
        if p:province=p
        if norm(label) in ('total','na') or not province:return
        if c is None or d is None or pct is None or d>c or not ok_rate(d,c,pct):return
        row={'province':province,'health_zone':None if p else label,'scope':'province' if p else 'health_zone',
             'cumulative_cases':c,'cumulative_deaths':d,'reported_cfr_pct':pct,'source':source}
        if p:
            if all(x is not None for x in (nc,dc,dh,dt)) and dc+dh==dt:
                row.update(new_cases_24h=nc,community_deaths_24h=dc,cte_deaths_24h=dh,deaths_24h=dt)
            provrows.append(row)
        else:records.append(row)
    for i,r in enumerate(first['rows'][4:],start=4):
        if not r or not norm(r[0]):continue
        label=norm(r[0]);label=r[0].strip().replace('\n',' ')
        c=count(r[1]) if len(r)>1 else None
        d=next((count(r[k]) for k in (3,4) if k<len(r) and count(r[k]) is not None),None)
        pct=percent(r[5]) if len(r)>5 else None
        # Table 2 page 2 has merged daily-outcome cells: do not attribute to zones.
        nc=count(r[7]) if len(r)>7 else None
        dc=count(r[9]) if len(r)>9 else None
        dh=count(r[10]) if len(r)>10 else None
        dt=count(r[11]) if len(r)>11 else None
        add(label,c,d,pct,cell_prov(first,i),nc,dc,dh,dt)
    pending=''
    for i,r in enumerate(other['rows']):
        if not r or not norm(r[0]):continue
        name=r[0].strip().replace('\n',' ')
        if all(not norm(x) for x in r[1:]):
            if len(name)<35:pending=name
            continue
        if pending:
            name=(pending+ (' ' if not pending.endswith('-') else '') +name).replace('- ','-')
            pending=''
        c=count(r[1]) if len(r)>1 else None
        d=count(r[2]) if len(r)>2 else None
        pct=percent(r[3]) if len(r)>3 else None
        nc=count(r[4]) if len(r)>4 else None
        dc=count(r[5]) if len(r)>5 else None
        dh=count(r[6]) if len(r)>6 else None
        dt=count(r[7]) if len(r)>7 else None
        add(name,c,d,pct,cell_prov(other,i),nc,dc,dh,dt)
    # Avoid duplicate province/zone collisions and conflicting rows.
    distinct={};duplicates=[]
    for row in records:
        key=(row['province'],norm(row['health_zone']))
        if key in distinct:duplicates.append(key)
        distinct[key]=row
    if duplicates:issues.append({'reason':'duplicate_health_zone','items':duplicates})
    t1=output['tables'].get('table_1')
    if t1 and t1['status']=='MACHINE_VALIDATED':
        known={r['scope']:r for r in t1['rows']}
        for row in provrows:
            expected=known.get(row['province'])
            if expected and (row['cumulative_cases']!=expected['cumulative_cases'] or row['cumulative_deaths']!=expected['cumulative_deaths']):
                issues.append({'reason':'table2_table1_provincial_disagreement','province':row['province']})
    elif not t1:issues.append({'reason':'table1_unavailable_for_crosscheck'})
    national=next((r for r in other['rows'] if r and norm(r[0])=='total'),None)
    if national and t1 and t1.get('national'):
        if count(national[1])!=t1['national']['cumulative_cases'] or count(national[2])!=t1['national']['cumulative_deaths']:
            issues.append({'reason':'table2_table1_national_disagreement'})
    if len(distinct)<10:issues.append({'reason':'too_few_healthzones_for_complete_table'})
    # A collection of internally consistent *rows* is not necessarily a complete
    # national table. Historically, the first page often captures only the end
    # of Ituri, silently omitting dozens of affected health zones.
    if not t1 or t1.get('status')!='MACHINE_VALIDATED' or not t1.get('national'):
        issues.append({'reason':'table2_full_coverage_cannot_be_crosschecked_with_validated_table1'})
    else:
        expected={r['scope']:r for r in t1.get('rows',[]) if r.get('cumulative_cases',0)>0}
        actual={r['province']:r for r in provrows}
        for p in sorted(set(expected)-set(actual)):
            issues.append({'reason':'table2_missing_province_total','province':p})
        for p in sorted(set(actual)-set(expected)):
            issues.append({'reason':'table2_unexpected_province_total','province':p})
        if len(actual)!=len(provrows):
            issues.append({'reason':'table2_duplicate_province_totals'})
        for p,reported in expected.items():
            if p not in actual:continue
            z=[r for r in distinct.values() if r['province']==p]
            sum_cases=sum(r['cumulative_cases'] for r in z)
            sum_deaths=sum(r['cumulative_deaths'] for r in z)
            pending=sum(u['unallocated_deaths'] for u in unallocated if u['province']==p)
            if sum_cases!=reported['cumulative_cases']:
                issues.append({'reason':'table2_healthzone_cases_do_not_reconcile','province':p,
                               'sum':sum_cases,'reported':reported['cumulative_cases']})
            if sum_deaths+pending!=reported['cumulative_deaths']:
                issues.append({'reason':'table2_healthzone_deaths_do_not_reconcile','province':p,
                               'sum':sum_deaths,'unallocated':pending,'reported':reported['cumulative_deaths']})
        expected_zones=t1['national'].get('health_zones_affected')
        if expected_zones is not None and len(distinct)!=expected_zones:
            issues.append({'reason':'table2_affected_healthzone_count_mismatch',
                           'parsed':len(distinct),'reported':expected_zones})
    return {'status':'REVIEW_REQUIRED' if issues else 'MACHINE_VALIDATED','rows':list(distinct.values()),
            'province_totals':provrows,'unallocated_deaths':unallocated,'flags':issues,
            'coverage_reconciliation':'all affected province totals and health-zone case/death sums required',
            'note':'Health-zone cumulative fields only; daily merged PDF cells are not assigned to zones.'}

def table_3(doc,output):
    t=table(doc,3)
    if not t:return None
    records=[];national=None;flags=[];missing=[]
    for i,r in enumerate(t['rows']):
        if len(r)<12:continue
        prov=scope_of(r[0]);last=not norm(r[0]) and all(count(r[x]) is not None for x in (1,2,3)) and i>=10
        if not prov and not last:continue
        fields={
            'received_alive':count(r[1]),'received_deceased':count(r[2]),'alerts_received':count(r[3]),
            'suspected_alive':count(r[4]),'suspected_deceased':count(r[5]),
            'not_suspected_alive':count(r[7]),'not_suspected_deceased':count(r[8]),
            'suspects_investigated':count(r[9]),'suspects_not_investigated':count(r[10]),
            'suspects_transferred':count(r[11]),
        }
        if any(v is None for v in fields.values()):
            if prov:missing.append({'reason':'table3_no_report','province':prov,'source_row':i})
            continue
        rec=fields|{'scope':prov or 'DRC','source':cell_prov(t,i)}
        n=fields['suspected_alive']+fields['suspected_deceased']
        neg=fields['not_suspected_alive']+fields['not_suspected_deceased']
        if (fields['received_alive']+fields['received_deceased']!=fields['alerts_received']
            or n+neg>fields['alerts_received']
            or fields['suspects_investigated']+fields['suspects_not_investigated']!=n
            or fields['suspects_transferred']>fields['suspects_investigated']):
            flags.append({'reason':'table3_inconsistent_pipeline','province':prov or 'DRC'});continue
        rec['suspected_alerts']=n;rec['not_suspected_alerts']=neg
        rec['alerts_not_yet_verified']=fields['alerts_received']-n-neg
        if prov:records.append(rec)
        else:national=rec
    if national is None:flags.append({'reason':'table3_national_total_missing'})
    else:
        keys=['received_alive','received_deceased','alerts_received','suspected_alive','suspected_deceased','not_suspected_alive','not_suspected_deceased','suspects_investigated','suspects_not_investigated','suspects_transferred']
        for k in keys:
            if sum(r[k] for r in records)!=national[k]:flags.append({'reason':'table3_provincial_sum_incomplete_or_disagrees','metric':k})
    return {'status':'MACHINE_VALIDATED' if not flags else 'REVIEW_REQUIRED','rows':records,'national':national,
            'flags':flags,'reporting_gaps':missing,'note':'Only reporting provinces are summed; ND is never zero.'}

def table_4(doc,output):
    """Decode contact follow-up tables with varying blank-cell offsets.

    A header row determines field coordinates: pdfplumber may shift the whole
    table by one or more columns without changing the PDF's actual meaning.
    Never infer a missing numeric denominator or silently treat ND as zero.
    """
    t=table(doc,4)
    if not t:return None
    labels={'province':('province','dps'),
            'contacts_to_follow':('contacts sous suivi','contacts a suivre'),
            'contacts_seen':('contacts vus','contacts suivis'),
            'contact_follow_up_rate':('taux de suivi',)}
    headers=[]
    for row in t['rows'][:7]:
        positions={}
        for key,synonyms in labels.items():
            matches=[i for i,value in enumerate(row)
                     if norm(value) in synonyms]
            if len(matches)==1:positions[key]=matches[0]
        if len(positions)==4 and len(set(positions.values()))==4:
            ids=[positions[k] for k in labels]
            if ids==sorted(ids):headers.append(positions)
    if len(headers)!=1:
        return {'status':'REVIEW_REQUIRED','rows':[],'flags':[{'reason':'table4_ambiguous_or_missing_header'}]}
    pos=headers[0]
    rows=[];national=None;flags=[];gaps=[]
    for i,r in enumerate(t['rows']):
        if max(pos.values())>=len(r):continue
        label=str(r[pos['province']]).strip()
        prov=scope_of(label)
        is_total=norm(label) in ('total','total general')
        if not prov and not is_total:continue
        d_raw=r[pos['contacts_to_follow']]
        n_raw=r[pos['contacts_seen']]
        pct_raw=r[pos['contact_follow_up_rate']]
        d=count(d_raw);n=count(n_raw);pct=percent(pct_raw)
        if prov and d is None and n is None and all(norm(x) in ('na','nd','n/a','') for x in (d_raw,n_raw,pct_raw)):
            gaps.append({'scope':prov,'reason':'contact_reporting_missing','source':cell_prov(t,i)})
            continue
        undefined=norm(pct_raw) in ('na','nd','n/a','')
        if (n is None or d is None or n>d
            or (d>0 and not ok_rate(n,d,pct))
            or (d==0 and (n!=0 or not undefined))):
            flags.append({'reason':'table4_invalid_rate_or_denominator','row':i,'scope':prov or 'DRC'})
            continue
        rec={'scope':prov or 'DRC','contacts_to_follow':d,'contacts_seen':n,
             'contact_follow_up_rate':pct if d>0 else None,'source':cell_prov(t,i)}
        if prov:rows.append(rec)
        elif national is not None:flags.append({'reason':'table4_duplicate_national_total'})
        else:national=rec
    if national is None or len(rows)<4:
        flags.append({'reason':'table4_missing_national_or_provinces'})
    else:
        for key in ('contacts_to_follow','contacts_seen'):
            if sum(r[key] for r in rows)!=national[key]:
                flags.append({'reason':'table4_provincial_sum_mismatch','field':key})
    return {'status':'MACHINE_VALIDATED' if not flags else 'REVIEW_REQUIRED','rows':rows,'national':national,
            'flags':flags,'reporting_gaps':gaps,
            'note':'Coordinates derived from printed header; ND omitted, never zero. Zero contacts => undefined rate.'}

def table_5(doc,output):
    t=table(doc,5)
    if not t:return None
    h=next((r for r in t['rows'] if r and norm(r[0])=='indicateurs'),None)
    if not h or len(h)<7:return {'status':'REVIEW_REQUIRED','rows':[],'flags':[{'reason':'table5_no_header'}]}
    headings=[]
    for hdr in h[1:]:
        p=scope_of(hdr)
        headings.append(p or ('DRC' if norm(hdr)=='global' else None))
    if len(headings)!=6 or any(x is None for x in headings) or headings[-1]!='DRC':
        return {'status':'REVIEW_REQUIRED','rows':[],'flags':[{'reason':'table5_bad_province_columns'}]}
    records={x:{} for x in headings};flags=[]
    metrics={'completude des rapports':'reporting_completeness','poc/poe strategiques':'strategic_poe_count',
             'nombre des voyageurs passes':'travellers_passed','proportion des voyageurs screenes':'travellers_screened_pct',
             '% des voyageurs ayant lave les mains':'handwashing_pct',
             '% des voyageurs sensibilises':'travellers_sensitized_pct',
             'nombre d\'alertes notifiees':'poe_alerts_notified'}
    percentage_names={'travellers_screened_pct','handwashing_pct','travellers_sensitized_pct'}
    for i,r in enumerate(t['rows']):
        label=norm(r[0]) if r else ''
        key=metrics.get(label)
        if not key or len(r)<7:continue
        for j,p in enumerate(headings,1):
            raw=str(r[j]).strip();value=None;extra={}
            if key=='reporting_completeness':
                frac=fraction(raw);pctmatch=re.search(r'(\d+(?:[.,]\d+)?)\s*%',raw)
                pct=percent(pctmatch.group(0)) if pctmatch else None
                if frac and ok_rate(frac[0],frac[1],pct):
                    value=pct;extra={'reports_received':frac[0],'reports_expected':frac[1]}
                else:flags.append({'reason':'table5_bad_reporting_fraction','scope':p})
            elif key in percentage_names:value=percent(raw)
            else:value=count(raw)
            if value is None:
                if norm(raw) not in ('na','nd','n/a',''):flags.append({'reason':'table5_unparseable_cell','row':i,'scope':p,'raw':raw[:50]})
                continue
            records[p][key]=value
            if extra:records[p].update(extra)
            records[p].setdefault('source',cell_prov(t,i))
    # Table 5 continues onto the following page. Only read the line-grid
    # continuation; PDF text-grid can split words and merge numeric columns.
    continuation=next((part for part in doc.get('tables',[])
        if part.get('page')==t['page']+1 and part.get('extractor')=='pdfplumber-lines'
        and any('corps sans vie' in norm(row[0]) for row in part.get('rows',[]) if row)),None)
    if continuation:
        metric_map={
            'nombre des corps sans vie interceptes':'poe_bodies_intercepted',
            '% des cas suspects transferes au ct/cte':'poe_suspects_transferred_pct',
            '% de corps sans vie swabes/securises':'poe_bodies_swabbed_pct',
            '% des cas suspects investigues dans 24 h':'poe_suspects_investigated_24h_pct',
        }
        for i,row in enumerate(continuation['rows']):
            if len(row)<7:continue
            key=metric_map.get(norm(row[0]))
            if not key:continue
            for j,p in enumerate(headings,1):
                raw=str(row[j]).replace('\n',' ')
                if key.endswith('_pct'):
                    f=fraction(raw)
                    m=re.search(r'(\d+(?:[.,]\d+)?)\s*%',raw)
                    rate=percent(m.group(0)) if m else None
                    # Unqualified 0% is not a measured success rate if the
                    # denominator is absent or zero.
                    if f and ok_rate(f[0],f[1],rate):
                        records[p][key]=rate
                        records[p][key.replace('_pct','_number')]=f[0]
                        records[p][key.replace('_pct','_denominator')]=f[1]
                    elif f or (rate is not None and rate>0):
                        flags.append({'reason':'table5_continuation_ratio_unverified','scope':p,'metric':key})
                else:
                    value=count(raw)
                    if value is not None:records[p][key]=value
        if all('poe_bodies_intercepted' in records[p] for p in headings):
            if sum(records[p]['poe_bodies_intercepted'] for p in headings[:-1])!=records['DRC']['poe_bodies_intercepted']:
                flags.append({'reason':'table5_body_interception_count_disagreement'})
    else:
        # Not all historical SitReps use a separate continuation page.
        records['DRC']['continuation_extract_status']='not_extracted_or_not_present'
    main=list(records.values())
    for metric in ('travellers_passed','poe_alerts_notified','reports_received','reports_expected'):
        if metric in records['DRC'] and all(metric in records[p] for p in headings[:-1]):
            if sum(records[p][metric] for p in headings[:-1])!=records['DRC'][metric]:
                flags.append({'reason':'table5_province_national_disagreement','field':metric})
    return {'status':'MACHINE_VALIDATED' if not flags else 'REVIEW_REQUIRED',
            'rows':[{'scope':p,**v} for p,v in records.items()], 'flags':flags,
            'note':'Percentages without denominator remain reported percentages only; zero-event success rates are undefined. Page 6 continuation included when extractable.'}

def extract_five_tables(doc):
    result=report_base(doc)
    for n,fn in ((1,table_1),(2,table_2),(3,table_3),(4,table_4),(5,table_5)):
        try:
            t=fn(doc,result)
            if t is None:result['quality_flags'].append({'reason':'table_missing','number':n});continue
            result['tables']['table_'+str(n)]=t
            for flag in t.get('flags',[]):result['quality_flags'].append({'table':n,**flag})
        except Exception as e:
            result['quality_flags'].append({'table':n,'reason':'parser_exception','detail':str(e)[:200]})
    present=sum(bool(t.get('rows')) for t in result['tables'].values())
    if present<5 or any(t.get('status')=='REVIEW_REQUIRED' for t in result['tables'].values()):
        result['status']='PARTIAL_REVIEW_REQUIRED'
    result['tables_available']=len(result['tables'])
    result['tables_machine_validated']=sum(t['status']=='MACHINE_VALIDATED' for t in result['tables'].values())
    return result
