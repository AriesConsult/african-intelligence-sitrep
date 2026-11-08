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

def render_html(r,lang):
    fr=lang=='fr'
    mode={'daily':('Daily','Quotidien'),'weekly':('Weekly','Hebdomadaire'),'monthly':('Monthly','Mensuel')}[r['frequency']][int(fr)]
    title='BDBV 2026 · '+mode+' · '+r['period_end']
    labels=(['Cas confirmés cumulés','Décès confirmés cumulés','Létalité brute','Traçage des contacts','Zones avec valeur numérique','Variation nette des cumuls (non-incidence)'] if fr
       else ['Cumulative confirmed cases','Cumulative confirmed deaths','Crude CFR','Contact tracing','Zones with numeric reporting','Net cumulative changes (not incidence)'])
    nums=lambda x:'—' if x is None else f'{x:,}'
    contact_rows=''.join('<tr><td>'+html.escape(k.replace('_',' ').capitalize())+'</td><td>'+nums(r['contact'].get(k,{}).get('reported_sum'))+'</td><td>'+str(r['contact'].get(k,{}).get('health_zones_with_numeric_reports',0))+'</td></tr>' for k in CONTACTS)
    delta='; '.join(k+': '+str(v) for k,v in r['changes'].items()) or '—'
    return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)} — African Intelligence</title><link rel="stylesheet" href="/assets/css/african-intelligence.css"><style>main{{max-width:920px;margin:24px auto;padding:0 18px;color:#244953}}header{{border-radius:15px;background:linear-gradient(115deg,#02475a,#097392);padding:28px;color:white}}header h1{{color:white}}.cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:18px 0}}.cards article{{border-radius:12px;background:#f0f7f8;padding:16px}}.cards strong{{display:block;color:#02475a;font-size:29px}}table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #dce9ec;text-align:left}}footer{{color:#627d85;font-size:12px;line-height:1.6;margin:20px 0}}@media(max-width:600px){{.cards{{grid-template-columns:1fr}}}}</style></head><body><main><p><a href="/bdvd2026/dashboard.php#bulletins">{"Retour au tableau de bord" if fr else "Back to dashboard"}</a></p><header><small>AFRICAN INTELLIGENCE · BDBV 2026</small><h1>{html.escape(title)}</h1><p>{"Synthèse automatisée sans analyse générée par IA" if fr else "Deterministic source digest without AI-generated interpretation"}</p></header><div class="cards"><article>{labels[0]}<strong>{nums(r['cases'])}</strong></article><article>{labels[1]}<strong>{nums(r['deaths'])}</strong></article><article>{labels[2]}<strong>{(r['deaths']/r['cases']*100):.1f}%</strong></article></div><p><strong>{"Date des données" if fr else "Source date"}:</strong> {r['source_date']} · {r['source_quality']}</p><p>{labels[5]}: {html.escape(delta)}</p><h2>{labels[3]}</h2><table><thead><tr><th>Indicator</th><th>Value</th><th>{labels[4]}</th></tr></thead><tbody>{contact_rows}</tbody></table><footer>INRB Git SHA: {r['source_commit']} · {"Les totaux ne couvrent que les zones qui ont déclaré une valeur; aucune donnée ND n'est convertie en zéro." if fr else "Zone sums include only numeric reporting; missing entries are not zero."} {"Différences des cumuls ≠ incidence réelle." if fr else "Differences in cumulative values are not event-date incidence."}</footer></main></body></html>'''

def build(accepted,output,stage=None):
    rows,commit=read_evidence(accepted,stage);nat,contacts=aggregate(rows)
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
        detail=dict(frequency=freq,period_start=start,period_end=end,source_date=day,cases=v['cases'],deaths=v['deaths'],
                    source_quality=v['source'],source_commit=commit if v['source']!='historical_qualified' else FROZEN,
                    contact=contacts.get(day,{}),changes=delta)
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
    (public/'assets/data/contact_tracing_public.json').write_text(json.dumps({'schema_version':'ai-bdbv-contacts-v1','historical_git_commit':FROZEN,'new_git_commit':commit,
      'days':contacts,'note':'Sums of reporting zones only; missing is not zero; no denominator-based follow-up rate calculated.'},ensure_ascii=False),encoding='utf-8')
    summary={'schema_version':'ai-bdbv-bulletin-build-v1','edition_counts':dict(counts),'earliest':dates[0],'latest':dates[-1],
       'historical_commit':FROZEN,'new_commit':commit,'qualified_sources':True,
       'no_ai_generated_content':True,'not_event_date_incidence':True,
       'site_deployment_requires_explicit_configuration':True}
    (output/'BULLETIN_BUILD_REPORT.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--accepted',required=True);p.add_argument('--out',required=True);p.add_argument('--stage')
    a=p.parse_args();build(a.accepted,a.out,a.stage)
