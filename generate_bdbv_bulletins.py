#!/usr/bin/env python3
"""Generate bilingual deterministic SitRep-derived bulletins and dashboard extracts.

No AI text. Frozen qualified historical CSV is the retrospective evidence
baseline. New GitHub INRB source candidates are labelled provisional and
never silently treated as verified historical observations.
"""
import argparse, csv, datetime as dt, gzip, hashlib, html, json, re
from collections import defaultdict, Counter
from pathlib import Path

FROZEN='c00b8843e6ebae8f0cd846bc43cb564a3893bfd9'
NATIONAL={'national_cumulative_confirmed_cases':'cases','national_cumulative_confirmed_deaths':'deaths'}
CONTACTS=['contacts_seen','new_contacts_listed','new_contacts_isolated','cumulative_contacts_traced','cumulative_contacts_isolated']
ALLOWED={'A_PDF_VERBATIM_CONCORDANT','B_DUAL_TRANSCRIPTION_CONCORDANCE','C_PINNED_CURATED_INRB_ONLY'}
SCANS={'2026-05-21','2026-05-22','2026-05-23'}

def parse_date(s):
    try:
        v=dt.date.fromisoformat(s)
        return v if v>=dt.date(2026,5,1) else None
    except (TypeError,ValueError):return None

def read_evidence(accepted,stage=None):
    obs=[];commit=None
    with Path(accepted).open(newline='',encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r['curated_revision_commit']!=FROZEN:raise ValueError('Unexpected historical source revision')
            if r['acceptance_tier'] not in ALLOWED or r.get('curated_value_eligible_for_qualified_descriptive_use')!='TRUE':continue
            if not parse_date(r['date']) or not str(r['curated_value']).isdigit():continue
            obs.append(dict(day=r['date'],metric=r['metric_id'],geo=r['geography_raw'],value=int(r['curated_value']),kind='historical_qualified'))
    historic=max((r['day'] for r in obs if r['metric']==list(NATIONAL)[0] and r['geo']=='DRC'),default=None)
    if not historic:raise ValueError('No historical national case records')
    if stage:
        summary=json.loads((Path(stage)/'inrb_staging_summary.json').read_text())
        commit=summary['inrb_commit']
        with gzip.open(Path(stage)/'inrb_observation_candidates.jsonl.gz','rt',encoding='utf-8') as f:
            key_seen=set()
            for line in f:
                r=json.loads(line);day=r.get('date_raw')
                if not parse_date(day) or day<=historic or day in SCANS:continue
                if r['metric_id'] not in NATIONAL and r['metric_id'] not in CONTACTS:continue
                if r.get('value_status')!='NUMERIC_UNVERIFIED' or type(r.get('value_parsed')) is not int:continue
                key=(day,r['metric_id'],r['geography_raw'])
                if key in key_seen:continue
                key_seen.add(key)
                obs.append(dict(day=day,metric=r['metric_id'],geo=r['geography_raw'],value=r['value_parsed'],kind='new_inrb_unverified'))
    return obs,commit

def aggregate(rows):
    day_national=defaultdict(dict);contact=defaultdict(lambda:defaultdict(dict))
    for r in rows:
        if r['metric'] in NATIONAL and r['geo']=='DRC':
            x=day_national[r['day']]
            if r['metric'] in x and x[r['metric']]['value']!=r['value']:x[r['metric']]=None
            elif r['metric'] not in x:x[r['metric']]=r
        if r['metric'] in CONTACTS and r['geo'] not in ('DRC','NA','Sans Fiche',''):
            x=contact[r['day']][r['metric']]
            if r['geo'] in x and x[r['geo']] is not None and x[r['geo']]['value']!=r['value']:x[r['geo']]=None
            elif r['geo'] not in x:x[r['geo']]=r
    nat={}
    for day,items in day_national.items():
        if not all(items.get(k) is not None for k in NATIONAL):continue
        c=items['national_cumulative_confirmed_cases']['value']
        d=items['national_cumulative_confirmed_deaths']['value']
        if c>=d:nat[day]=dict(cases=c,deaths=d,source='new_inrb_unverified' if any(items[k]['kind']=='new_inrb_unverified' for k in NATIONAL) else 'historical_qualified')
    contacts={}
    for day,metrics in contact.items():
        contacts[day]={k:dict(reported_sum=sum(x['value'] for x in v.values() if x is not None) if any(x is not None for x in v.values()) else None,
            health_zones_with_numeric_reports=sum(x is not None for x in v.values()),total_source_zones=len(v)) for k,v in metrics.items()}
    return nat,contacts

def periods(dates):
    start=dt.date.fromisoformat(dates[0]);finish=dt.date.fromisoformat(dates[-1])
    for day in dates:yield 'daily',day,day
    current=start-dt.timedelta(days=start.weekday())
    while current<=finish:
        yield 'weekly',current.isoformat(),(current+dt.timedelta(days=6)).isoformat()
        current+=dt.timedelta(days=7)
    current=start.replace(day=1)
    while current<=finish:
        nxt=current.replace(year=current.year+1,month=1) if current.month==12 else current.replace(month=current.month+1)
        yield 'monthly',current.isoformat(),(nxt-dt.timedelta(days=1)).isoformat()
        current=nxt


def load_table4(published):
    """Use original hash-pinned SitRep Table 4, never obsolete May-only CSVs."""
    result={}
    if not published:return result
    root=Path(published);index=root/'table_index.json'
    if not index.is_file():return result
    for ref in json.loads(index.read_text(encoding='utf-8')).get('reports',[]):
        rel=ref.get('snapshot_path') or ''
        if not rel.startswith('tables/') or '..' in rel:continue
        try:
            snap=json.loads((root/rel).read_text(encoding='utf-8'))
            if snap.get('source_sha256')!=ref.get('sha256') or snap.get('date')!=ref.get('date'):continue
            t4=snap.get('tables',{}).get('table_4',{})
            if t4.get('status')!='MACHINE_VALIDATED':continue
            national=t4.get('national')
            if not isinstance(national,dict):continue
            seen=national.get('contacts_seen');to_follow=national.get('contacts_to_follow')
            if not all(type(x) is int and x>=0 for x in (seen,to_follow)) or seen>to_follow:continue
            calc=round(100*seen/to_follow,1) if to_follow else None
            declared=national.get('contact_follow_up_rate')
            if declared is not None and (calc is None or abs(float(declared)-calc)>0.15):continue
            provinces=[]
            for p in t4.get('rows',[]):
                ps,pt=p.get('contacts_seen'),p.get('contacts_to_follow')
                if type(ps) is not int or type(pt) is not int or ps<0 or pt<0 or ps>pt:continue
                provinces.append({'province':p['scope'],'contacts_seen':ps,'contacts_to_follow':pt,
                    'follow_up_pct':round(100*ps/pt,1) if pt else None,'source':p.get('source')})
            result[snap['date']]={'national':{'contacts_seen':seen,'contacts_to_follow':to_follow,
               'follow_up_pct':calc},'provinces':provinces,'reporting_gaps':t4.get('reporting_gaps',[]),
               'source_report':snap['report_number'],'source_url':snap.get('source_url'),
               'source_sha256':snap['source_sha256'],'source_page':national.get('source',{}).get('page'),
               'status':'MACHINE_VALIDATED','source_table':'table_4'}
        except (ValueError,KeyError,TypeError,OSError,ZeroDivisionError):continue
    return result

TOPIC_NAMES={
 'surveillance_and_alerts':('Surveillance and alerts','Surveillance et alertes'),
 'contact_tracing':('Contact tracing operations','Recherche et suivi des contacts'),
 'border_screening':('Points of entry','Points d’entrée'),
 'laboratory':('Laboratory','Laboratoire'),
 'vaccination':('Vaccination','Vaccination'),
 'treatment_capacity':('Clinical care','Prise en charge'),
 'ipc_and_burials':('Infection prevention and safe burials','Prévention des infections et inhumations'),
 'community_engagement':('Community engagement','Engagement communautaire'),
 'logistics_and_supplies':('Logistics','Logistique'),
 'service_continuity':('Service continuity','Continuité des services'),
 'security':('Security','Sécurité')
}
def short_excerpt(text,maximum_words=19):
    """Source text, not generated interpretation; truncate to a short attributable fragment."""
    words=re.sub(r'\s+',' ',str(text)).strip().split(' ')
    if len(words)<5:return ''
    return ' '.join(words[:maximum_words])+('…' if len(words)>maximum_words else '')

def load_narratives(published):
    if not published:return []
    root=Path(published);idx=root/'narrative_index.json'
    if not idx.exists():return []
    out=[]
    for ref in json.loads(idx.read_text(encoding='utf-8')).get('reports',[]):
        rel=ref.get('snapshot_path') or ''
        if not rel.startswith('narrative_candidates/') or '..' in rel:continue
        try:
            snap=json.loads((root/rel).read_text(encoding='utf-8'))
            if snap.get('source_sha256')!=ref.get('source_sha256') or snap.get('date')!=ref.get('date'):continue
            out.append(snap)
        except (OSError,ValueError,TypeError):continue
    return out

def period_narratives(narratives,start,end,max_reports=3,max_items=8):
    """Sample dated, page-linked, unverified source-text excerpts without claiming events."""
    reports=sorted((s for s in narratives if start<=s.get('date','')<=end),
                   key=lambda x:(x['date'],x['report_number']),reverse=True)[:max_reports]
    found=[];used=set();used_passages=set()
    for snap in reports:
        for topic in TOPIC_NAMES:
            if topic in used:continue
            candidates=[c for c in snap.get('candidates',[]) if topic in c.get('topic_tags',[])
                  and c.get('review_status')=='REVIEW_REQUIRED'
                  and not c.get('excerpt_truncated')
                  and len(c.get('excerpt','').split())>=8]
            candidates=sorted(candidates,key=lambda c:(
                bool(c.get('event_type_candidates')),len(c.get('excerpt',''))),reverse=True)
            # A source paragraph can match several rule-based topics. Publish it once
            # rather than implying that repeated classification is separate evidence.
            for c in candidates:
                excerpt=short_excerpt(c['excerpt'])
                passage_key=re.sub(r'\\s+',' ',excerpt).strip().casefold()
                if not passage_key or passage_key in used_passages:continue
                found.append({'topic':topic,'excerpt':excerpt,'date':snap['date'],
                   'report':snap['report_number'],'page':c['page'],
                   'source_url':snap.get('source_url'),'candidate_id':c['candidate_id'],
                   'status':'REVIEW_REQUIRED','language':'fr_original'})
                used.add(topic);used_passages.add(passage_key)
                break
            if len(found)>=max_items:return found
    return found

def source_digest_html(r,lang):
    fr=lang=='fr';items=r.get('narrative',[])
    heading='Extraits du SitRep par thème (vérification en attente)' if fr else 'SitRep source-text digest by theme (verification pending)'
    if not items:
        return '<h2>'+heading+'</h2><p>'+('Aucun extrait complet sélectionnable pour cette période.' if fr else 'No complete source-text excerpts selected for this period.')+'</p>'
    chunks=[]
    for item in items:
        t=TOPIC_NAMES.get(item['topic'],(item['topic'],item['topic']))[int(fr)]
        src=html.escape(str(item.get('source_url') or ''),quote=True)
        label=('SitRep'+' '+str(item['report'])+', p. '+str(item['page']))
        link='<a href="'+src+'" rel="noopener noreferrer" target="_blank">'+html.escape(label)+'</a>' if src.startswith('https://') else html.escape(label)
        chunks.append('<li><strong>'+html.escape(t)+'</strong>: <span lang="fr">'+html.escape(item['excerpt'])+'</span> <small>('+link+' · '+item['date']+')</small></li>')
    note=('Ces extraits courts reproduisent la langue originale des rapports. Leur classement par thème est automatique, sans validation du sens, de la complétude ou des changements.'
       if fr else 'Short passages remain in their original French. Topic assignment is rule-based and not yet verified for meaning, completeness or change over time.')
    return '<section><h2>'+heading+'</h2><p>'+html.escape(note)+'</p><ul class="source-digest">'+''.join(chunks)+'</ul></section>'


# Reported source data, never invented incidence. All original SitRep tables
# are covered when the corresponding table has passed machine reconciliation.
TABLE_NAMES={
 'table_1':('Epidemic overview','Situation épidémiologique'),
 'table_2':('Health-zone case/death reports','Cas et décès par zone de santé'),
 'table_3':('Surveillance and alerts','Surveillance et alertes'),
 'table_4':('Contact follow-up','Suivi des contacts'),
 'table_5':('PoE / PoC border monitoring','Surveillance aux points d’entrée et de contrôle')
}
PERCENT_FIELDS={'contact_follow_up_rate','reported_cfr_pct','reporting_completeness',
    'travellers_screened_pct','travellers_sensitized_pct','handwashing_pct',
    'poe_suspects_transferred_pct','poe_suspects_investigated_24h_pct',
    'poe_bodies_swabbed_pct'}
RATE_SUFFIXES=('_pct','_rate')
def load_original_table_snapshots(published):
    if not published:return {}
    root=Path(published);idx=root/'table_index.json'
    if not idx.is_file():return {}
    out={}
    for ref in json.loads(idx.read_text(encoding='utf-8')).get('reports',[]):
        rel=ref.get('snapshot_path') or ''
        if not rel.startswith('tables/') or '..' in rel:continue
        try:
            snap=json.loads((root/rel).read_text(encoding='utf-8'))
            if (snap.get('source_sha256')!=ref.get('sha256') or
                snap.get('date')!=ref.get('date') or
                snap.get('report_number')!=ref.get('report_number')):continue
            # Indexed latest revision per source report, no implicit reconciliation.
            out[snap['date']]=snap
        except (OSError,ValueError,TypeError,KeyError):continue
    return out

def numeric_fields(row):
    return {k:v for k,v in row.items() if k not in
        ('scope','source','province','health_zone','source_row','table_id') and
        type(v) in (int,float) and v>=0}

def annex_rows(tab,key):
    rows=[]
    if isinstance(tab.get('national'),dict):rows.append(('DRC',tab['national']))
    for row in tab.get('rows',[]):
        if not isinstance(row,dict):continue
        ident=row.get('health_zone') or row.get('scope') or row.get('province')
        if key=='table_2' and row.get('health_zone'):
            ident=(row.get('province') or '')+' / '+row['health_zone']
        if ident:rows.append((str(ident),row))
    if key=='table_2':
        for row in tab.get('province_totals',[]):
            if isinstance(row,dict) and row.get('province'):
                rows.append(('Province: '+row['province'],row))
    return rows

def numeric_annex_html(report,prior,lang):
    fr=lang=='fr'
    heading='Annexe numérique des cinq tableaux du SitRep' if fr else 'Numerical annex from all five SitRep tables'
    if not report:
        return '<section class="annex"><h2>'+heading+'</h2><p>'+(
          'Aucun SitRep original apparié à cette date.' if fr else
          'No original SitRep matched to this bulletin date.')+'</p></section>'
    prior=prior or {}
    start=['<section class="annex"><h2>'+heading+'</h2><p>'+
       ('Les tableaux non validés restent non publiés. Une variation reflète la différence entre deux observations publiées, pas nécessairement une incidence.' if fr else
       'Unvalidated source tables remain unpublished. A change compares two reported snapshots, not necessarily event-date incidence.')+
       ' SitRep '+str(report['report_number'])+' · '+html.escape(report['date'])+
       (' · Comparaison avec ' if fr else ' · Compared with ')+
       html.escape(prior.get('date') or '—')+'</p>']
    for key,names in TABLE_NAMES.items():
        tab=report.get('tables',{}).get(key) or {}
        status=tab.get('status','NOT_EXTRACTED')
        start.append('<details class="source-table" '+('open' if key in ('table_1','table_3','table_4','table_5') else '')+'><summary>Table '+str(tab.get('original_table_number',key[-1]))+' — '+html.escape(names[int(fr)])+' · '+html.escape(status)+'</summary>')
        if status!='MACHINE_VALIDATED':
            start.append('<p>'+('Non publié : extraction absente ou reconciliation requise' if fr else
                'Not published: extraction missing or source reconciliation pending')+'</p></details>')
            continue
        rows=annex_rows(tab,key)
        fields=sorted(set().union(*(numeric_fields(r).keys() for _,r in rows))) if rows else []
        if not fields:
            start.append('<p>'+('Aucune valeur numérique récupérée' if fr else 'No recovered numeric values')+'</p></details>')
            continue
        oldtab=prior.get('tables',{}).get(key) or {}
        oldrows=dict(annex_rows(oldtab,key)) if oldtab.get('status')=='MACHINE_VALIDATED' else {}
        start.append('<div class="annex-scroll"><table><thead><tr><th>'+
            ('Lieu' if fr else 'Geography')+'</th>'+
            ''.join('<th>'+html.escape(k.replace('_',' '))+'</th>' for k in fields)+
            '</tr></thead><tbody>')
        for place,row in rows:
            old=numeric_fields(oldrows.get(place,{}))
            nums=numeric_fields(row)
            start.append('<tr><th>'+html.escape(place)+((' <small>p. '+str(row['source']['page'])+'</small>') if isinstance(row.get('source'),dict) and row['source'].get('page') else '')+'</th>')
            for metric in fields:
                value=nums.get(metric)
                if value is None:start.append('<td>—</td>');continue
                v=f'{value:,.1f}' if isinstance(value,float) else f'{value:,}'
                # Escape numeric text first; trusted delta markup must not be escaped.
                cell=html.escape(v)
                prev=old.get(metric)
                if type(prev) in (int,float):
                    delta=value-prev
                    suffix=' pp' if metric in PERCENT_FIELDS or metric.endswith(RATE_SUFFIXES) else ''
                    change=('+' if delta>0 else '')+f'{delta:,.1f}' if suffix or isinstance(delta,float) else ('+' if delta>0 else '')+f'{delta:,}'
                    cell+=' <small>('+html.escape(change+suffix)+')</small>'
                start.append('<td>'+cell+'</td>')
            start.append('</tr>')
        start.append('</tbody></table></div>')
        missing=tab.get('reporting_gaps',[])
        if missing:
            names=', '.join(str(x.get('scope','')) for x in missing if isinstance(x,dict))
            start.append('<p>'+('Absence de rapportage : ' if fr else 'Reporting gaps: ')+html.escape(names)+'</p>')
        start.append('</details>')
    url=report.get('source_url') or ''
    if url.startswith('https://'):
        start.append('<p><a href="'+html.escape(url,quote=True)+'" rel="noopener" target="_blank">'+
           ('PDF original du SitRep' if fr else 'Original SitRep PDF')+'</a> · SHA-256: <code>'+report['source_sha256']+'</code></p>')
    start.append('</section>')
    return ''.join(start)

def render_html(r,lang):
    fr=lang=='fr'
    mode={'daily':('Daily','Quotidien'),'weekly':('Weekly','Hebdomadaire'),'monthly':('Monthly','Mensuel')}[r['frequency']][int(fr)]
    title='BDBV 2026 · '+mode+' · '+r['period_end']
    labels=(['Cas confirmés cumulés','Décès confirmés cumulés','Létalité brute','Traçage des contacts','Zones avec valeur numérique','Variation nette des cumuls (non-incidence)'] if fr
       else ['Cumulative confirmed cases','Cumulative confirmed deaths','Crude CFR','Contact tracing','Zones with numeric reporting','Net cumulative changes (not incidence)'])
    nums=lambda x:'—' if x is None else f'{x:,}'
    t4=r.get('table4') or {}
    n=t4.get('national') or {}
    if n:
        follow=n.get('follow_up_pct')
        fmt=lambda x: '—' if x is None else f'{x:,}'
        contact_rows='<tr><td>'+('Contacts à suivre' if fr else 'Contacts to follow')+'</td><td>'+fmt(n.get('contacts_to_follow'))+'</td><td>National</td></tr>'
        contact_rows+='<tr><td>'+('Contacts vus' if fr else 'Contacts seen')+'</td><td>'+fmt(n.get('contacts_seen'))+'</td><td>National</td></tr>'
        contact_rows+='<tr><td>'+('Suivi des contacts' if fr else 'Follow-up coverage')+'</td><td>'+('—' if follow is None else f'{follow:.1f}%')+'</td><td>National</td></tr>'
        for p in t4.get('provinces',[]):
            rate='—' if p['follow_up_pct'] is None else f"{p['follow_up_pct']:.1f}%"
            contact_rows+='<tr><td>'+html.escape(p['province'])+'</td><td>'+fmt(p['contacts_seen'])+' / '+fmt(p['contacts_to_follow'])+'</td><td>'+rate+'</td></tr>'
        if t4.get('reporting_gaps'):
            contact_rows+='<tr><td colspan=\"3\">'+('Lacunes de rapportage: ' if fr else 'Reporting gaps: ')+html.escape(', '.join(p['scope'] for p in t4['reporting_gaps']))+'</td></tr>'
    else:
        contact_rows='<tr><td colspan=\"3\">'+('Aucun tableau 4 validé pour la date de référence.' if fr else 'No machine-validated Table 4 for the reference date.')+'</td></tr>'
    delta='; '.join(k+': '+str(v) for k,v in r['changes'].items()) or '—'
    return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)} — African Intelligence</title><link rel="stylesheet" href="/assets/css/african-intelligence.css"><style>main{{max-width:920px;margin:24px auto;padding:0 18px;color:#244953}}header{{border-radius:15px;background:linear-gradient(115deg,#02475a,#097392);padding:28px;color:white}}header h1{{color:white}}.cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:18px 0}}.cards article{{border-radius:12px;background:#f0f7f8;padding:16px}}.cards strong{{display:block;color:#02475a;font-size:29px}}table{{width:100%;border-collapse:collapse}}.annex-scroll{{max-width:100%;overflow:auto}}.annex-scroll table{{min-width:760px;font-size:12px}}.annex-scroll td{{white-space:nowrap}}.source-table{{margin:12px 0;padding:8px;border:1px solid #dde9ec;border-radius:8px}}.source-table summary{{cursor:pointer;font-weight:700;color:#02516a}}td,th{{padding:10px;border-bottom:1px solid #dce9ec;text-align:left}}footer{{color:#627d85;font-size:12px;line-height:1.6;margin:20px 0}}@media(max-width:600px){{.cards{{grid-template-columns:1fr}}}}</style></head><body><main><p><a href="/bdvd2026/dashboard.php#bulletins">{"Retour au tableau de bord" if fr else "Back to dashboard"}</a></p><header><small>AFRICAN INTELLIGENCE · BDBV 2026</small><h1>{html.escape(title)}</h1><p>{"Synthèse automatisée sans analyse générée par IA" if fr else "Deterministic source digest without AI-generated interpretation"}</p></header><div class="cards"><article>{labels[0]}<strong>{nums(r['cases'])}</strong></article><article>{labels[1]}<strong>{nums(r['deaths'])}</strong></article><article>{labels[2]}<strong>{(r['deaths']/r['cases']*100):.1f}%</strong></article></div><p><strong>{"Date des données" if fr else "Source date"}:</strong> {r['source_date']} · {r['source_quality']}</p><p>{labels[5]}: {html.escape(delta)}</p><h2>{labels[3]}</h2><p>{(('Tableau 4 · SitRep ' if fr else 'Table 4 · SitRep ')+str(t4['source_report'])) if t4 else ''}</p><table><thead><tr><th>Indicator</th><th>Value</th><th>{labels[4]}</th></tr></thead><tbody>{contact_rows}</tbody></table>{source_digest_html(r,lang)}{numeric_annex_html(r.get('original_report'),r.get('prior_report'),lang)}<footer>INRB Git SHA: {r['source_commit']} · {"Les totaux ne couvrent que les zones qui ont déclaré une valeur; aucune donnée ND n'est convertie en zéro." if fr else "Zone sums include only numeric reporting; missing entries are not zero."} {"Différences des cumuls ≠ incidence réelle." if fr else "Differences in cumulative values are not event-date incidence."}</footer></main></body></html>'''

def build(accepted,output,stage=None,published=None):
    rows,commit=read_evidence(accepted,stage);nat,contacts=aggregate(rows)
    table4=load_table4(published);narratives=load_narratives(published)
    original_reports=load_original_table_snapshots(published)
    for date,record in table4.items():
        contacts.setdefault(date,{})['table4']=record
    if len(nat)<2:raise ValueError('Insufficient paired national source snapshots')
    dates=sorted(nat);output=Path(output)
    public=output/'bdvd2026';(public/'assets/data').mkdir(parents=True,exist_ok=True)
    items=[];weekly=[];counts=Counter()
    for freq,start,end in periods(dates):
        covered=[d for d in dates if start<=d<=end]
        if not covered:continue
        day=covered[-1];v=nat[day];previous=[d for d in dates if d<start];delta={}
        if previous and v['source']=='historical_qualified' and nat[previous[-1]]['source']=='historical_qualified':
            old=nat[previous[-1]]
            for metric in ('cases','deaths'):
                diff=v[metric]-old[metric]
                if diff>=0:delta[metric+' net cumulative change']=diff
        period_table4=table4.get(max((d for d in table4 if start<=d<=day),default=''))
        # For the full numerical annex, the latest original SitRep WITHIN the
        # relevant day/week/month; never carry another period's values forward.
        period_reports=[d for d in original_reports if start<=d<=day]
        original_day=max(period_reports) if period_reports else None
        current_original=original_reports.get(original_day)
        earlier_reports=[d for d in original_reports if original_day and d<start]
        previous_original=original_reports.get(max(earlier_reports)) if earlier_reports else None
        detail=dict(frequency=freq,period_start=start,period_end=end,source_date=day,cases=v['cases'],deaths=v['deaths'],
                    source_quality=v['source'],source_commit=commit if v['source']!='historical_qualified' else FROZEN,
                    contact=contacts.get(day,{}),table4=period_table4,
                    narrative=period_narratives(narratives,start,day,max_reports=2 if freq=='daily' else 4),
                    original_report=current_original,prior_report=previous_original,changes=delta)
        target=public/'bulletins'/freq;target.mkdir(parents=True,exist_ok=True)
        langs=[]
        for lang in ('en','fr'):
            target.joinpath(end+'-'+lang+'.html').write_text(render_html(detail,lang),encoding='utf-8')
            langs.append({'lang':lang,'url':'/bdvd2026/bulletins/'+freq+'/'+end+'-'+lang+'.html'})
        title={'daily':'Daily','weekly':'Weekly','monthly':'Monthly'}[freq]+' source bulletin · '+end
        items.append({'status':'published','frequency':freq,'period_end':end,'period_start':start,'source_date':day,
              'title':title,'summary':'Deterministic INRB GitHub source digest; provisional cumulative reporting, not onset-date incidence.',
              'languages':langs,'automation':'rule_based_unreviewed'})
        if freq=='weekly':weekly.append({'period_start':start,'period_end':end,'source_date':day,'cases':v['cases'],'deaths':v['deaths'],'changes':delta})
        counts[freq]+=1
    (public/'assets/data/bulletins_public.json').write_text(json.dumps({'schema_version':'ai-bdbv-published-bulletins-v1','publication_mode':'automated_unreviewed_no_ai','historical_git_commit':FROZEN,'new_git_commit':commit,'bulletins':items},ensure_ascii=False),encoding='utf-8')
    (public/'assets/data/weekly_national_public.json').write_text(json.dumps({'schema_version':'ai-bdbv-weekly-national-v1','weeks':weekly,
      'note':'Net cumulative differences, not epi onset incidence; revised or negative intervals suppressed.'},ensure_ascii=False),encoding='utf-8')
    (public/'assets/data/contact_tracing_public.json').write_text(json.dumps({'schema_version':'ai-bdbv-contacts-v1','historical_git_commit':FROZEN,'new_git_commit':commit,'table4_report_count':len(table4),
      'days':contacts,'note':'Sums of reporting zones only; missing is not zero; no denominator-based follow-up rate calculated.'},ensure_ascii=False),encoding='utf-8')
    summary={'schema_version':'ai-bdbv-bulletin-build-v1','edition_counts':dict(counts),'earliest':dates[0],'latest':dates[-1],
       'historical_commit':FROZEN,'new_commit':commit,'qualified_sources':True,
       'no_ai_generated_content':True,'not_event_date_incidence':True,'machine_validated_table4_dates':len(table4),'narrative_source_reports':len(narratives),'original_sitrep_table_reports':len(original_reports),
       'site_deployment_requires_explicit_configuration':True}
    (output/'BULLETIN_BUILD_REPORT.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--accepted',required=True);p.add_argument('--out',required=True);p.add_argument('--stage');p.add_argument('--published')
    a=p.parse_args();build(a.accepted,a.out,a.stage,a.published)
