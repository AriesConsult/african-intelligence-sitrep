#!/usr/bin/env python3
"""Build longitudinal *candidate* signals, never verified incident counts.

Groups lexical topic/event labels by date and geographic mention while retaining
sources. Repeated passages are detected by exact fragment SHA256, not assumed to
be independent occurrences. Outputs are review-only inputs for editorial work.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from run_pipeline import write_json

ROOT=Path(__file__).resolve().parent


def compile_signals(published:Path):
    nidx=json.loads((published/'narrative_index.json').read_text(encoding='utf-8'))
    trends=defaultdict(lambda:{'reports':set(),'candidates':0})
    clusters=defaultdict(lambda:{'reports':set(),'dates':set(),'candidates':0,'examples':[]})
    exact=defaultdict(lambda:{'reports':set(),'dates':set(),'topics':set(),'examples':[]})
    failures=[];all_blocks=0;processed=0
    for r in nidx.get('reports',[]):
        try:
            rel=r['snapshot_path']
            if not rel.startswith('narrative_candidates/') or '..' in rel:
                raise ValueError('unsafe narrative path')
            snap=json.loads((published/rel).read_text(encoding='utf-8'))
            if (snap['source_sha256']!=r['source_sha256'] or
                snap['report_number']!=r['report_number'] or
                snap['candidates_count']!=len(snap['candidates'])):
                raise ValueError('narrative identity/count mismatch')
            no=snap['report_number'];date=snap['date'];sha=snap['source_sha256']
            processed+=1
            for c in snap['candidates']:
                if c.get('review_status')!='REVIEW_REQUIRED':
                    raise ValueError('unreviewed candidate unexpectedly approved')
                all_blocks+=1
                cite={'report_number':no,'date':date,'page':c['page'],
                      'candidate_id':c['candidate_id'],'source_sha256':sha}
                topics=c.get('topic_tags',[]) or ['unclassified']
                events=c.get('event_type_candidates',[]) or ['unspecified']
                places=c.get('province_mentions',[]) or ['geography_not_explicit']
                for topic in topics:
                    v=trends[(date,topic)];v['reports'].add(no);v['candidates']+=1
                for ev in events:
                    if ev=='unspecified':continue
                    for place in places:
                        z=clusters[(ev,place)]
                        z['reports'].add(no);z['dates'].add(date);z['candidates']+=1
                        z['examples'].append((date,cite,c.get('excerpt','')[:200]))
                fragment=c['source_text_sha256'];k=exact[fragment]
                k['reports'].add(no);k['dates'].add(date);k['topics'].update(topics)
                k['examples'].append((date,cite))
        except (OSError,ValueError,KeyError,TypeError) as e:
            failures.append({'report_number':r.get('report_number'),'reason':str(e)[:130]})
    daily=[{'date':date,'topic':topic,'mentioning_reports':len(v['reports']),
            'candidate_blocks':v['candidates']} for (date,topic),v in sorted(trends.items())]
    groups=[]
    for (event,place),v in sorted(clusters.items()):
        examples=sorted(v['examples'],key=lambda x:x[0],reverse=True)
        groups.append({'event_type_candidate':event,'province_mention':place,
            'first_report_date':min(v['dates']),'last_report_date':max(v['dates']),
            'distinct_reporting_sitreps':len(v['reports']),
            'candidate_passages':v['candidates'],
            'recent_examples':[{'source':cite,'excerpt':excerpt} for _,cite,excerpt in examples[:3]],
            'review_status':'UNVERIFIED_THEME_CLUSTER',
            'caution':'May combine unrelated events; no incident identity or causal claim is asserted.'})
    repeated=[]
    for hash_value,v in exact.items():
        if len(v['reports'])<2:continue
        repeated.append({'source_text_sha256':hash_value,
            'distinct_sitreps':len(v['reports']),'first_date':min(v['dates']),
            'last_date':max(v['dates']),'topic_candidates':sorted(v['topics']),
            'example_source':sorted(v['examples'],key=lambda x:x[0])[-1][1]})
    repeated.sort(key=lambda r:(-r['distinct_sitreps'],r['source_text_sha256']))
    if failures or processed!=len(nidx.get('reports',[])):
        raise ValueError('Narrative signal index incomplete: '+json.dumps(failures[:8]))
    out={'schema_version':'bdbv-narrative-signals-v1',
         'generated_at':datetime.now(timezone.utc).isoformat(),
         'reports_classified':processed,'candidate_blocks_checked':all_blocks,
         'daily_topic_mentions':daily,'event_type_province_clusters':groups,
         'exact_passages_repeated_across_sitreps':repeated,
         'review_status':'REVIEW_REQUIRED',
         'methodology':'Lexical grouping by tags and mentioned province; repeated exact source-text hashes are not independent incidents.',
         'interpretation_limit':'Counts measure source text coverage and mention frequency, NOT outbreak event incidence, response effectiveness, or causal effects.'}
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--published',type=Path,default=ROOT/'published')
    args=p.parse_args()
    out=compile_signals(args.published)
    write_json(args.published/'narrative_signal_index.json',out)
    print(json.dumps({'reports':out['reports_classified'],'blocks':out['candidate_blocks_checked'],
        'daily_topic_points':len(out['daily_topic_mentions']),
        'theme_clusters':len(out['event_type_province_clusters']),
        'repeated_exact_passages':len(out['exact_passages_repeated_across_sitreps'])}))


if __name__=='__main__':main()
