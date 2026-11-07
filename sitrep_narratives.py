"""Traceable, review-only extraction of operational narrative from official SitReps.

Rule-based classifications are candidate tags, NOT AI interpretations or
published findings. Full source text stays in a short-retention audit artifact;
the public repository gets only compact evidence pointers and short excerpts.
"""
from __future__ import annotations
import hashlib, io, re, unicodedata
from collections import Counter
from typing import Any
import pymupdf

SCHEMA='bdbv-sitrep-narratives-v1'

TOPICS={
 'surveillance_and_alerts':r'\b(?:surveillance|alertes?|investigu|notif(?:ie|i[eé])|susp(?:ect|icion))\b',
 'contact_tracing':r'\b(?:contacts?|suivi\s+des\s+contacts)\b',
 'laboratory':r'\b(?:laboratoires?|reactifs?|echantillons?|prelevements?|positivite|PCR)\b',
 'treatment_capacity':r'\b(?:CTE|CT/CTE|isolement|hospitalis|ambulances?|lits?|malades?|patients?|admissions?)\b',
 'vaccination':r'\b(?:vaccin|vaccination|Ervebo|doses?|MAPI|PEV)\b',
 'ipc_and_burials':r'\b(?:PCI|EDS|decontamin|inhum|enterrement|swab|hygiene|WASH)\b',
 'border_screening':r'\b(?:PoE|PoC|voyageurs?|screening|poste\s+de\s+controle)\b',
 'service_continuity':r'\b(?:continuite|services?\s+essentiels?|fermeture|greve|triage|soins?\s+curatifs?)\b',
 'community_engagement':r'\b(?:CREC|RECO|resistance|sensibilis|communautaire|causeries?|mobilis)\b',
 'psychosocial_support':r'\b(?:psychosocial|psycholog|SMSPS|orphelins?|enfants?\s+separes?)\b',
 'logistics_and_supplies':r'\b(?:stocks?|rupture|intrants?|logistique|carburant|matelas|approvisionn|reactifs?)\b',
 'security':r'\b(?:insecurite|securit|grenade|incendi|attaque|menace|agression)\b',
}
EVENT_TYPES={
 'security_incident':r'\b(?:grenade|incendie|incendi|attaque|ins[eé]curit[eé]|menac|agress)\w*',
 'service_disruption':r'\b(?:gr[eè]ve|ferm[eé]|fermeture|suspendu|non fonctionnel|paralys|panne|non op[eé]rationnel)\w*',
 'resource_constraint':r'\b(?:manqu|insuffisan|rupture|pr[eé]-rupture|d[eé]ficit|stock critique|besoin)\w*',
 'activity_or_delivery':r'\b(?:r[eé]ceptionn|livr[eé]|dot[eé]|form[eé]|d[eé]ploy[eé]|r[eé]habilit|appui|r[eé]alis[eé])\w*',
}
PROVINCES={
 'Ituri':r'\bituri\b', 'Nord-Kivu':r'\bnord[\s-]kivu\b',
 'Sud-Kivu':r'\bsud[\s-]kivu\b','Haut-Uélé':r'\bhaut[\s-]uele\b',
 'Bas-Uélé':r'\bbas[\s-]uele\b','Tshopo':r'\btshopo\b',
 'Sud-Ubangi':r'\bsud[\s-]ubangi\b','Nord-Ubangi':r'\bnord[\s-]ubangi\b',
}

def normalize(s:str)->str:
    s=''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if not unicodedata.combining(c))
    return re.sub(r'\s+',' ',s.replace('’',"'")).strip()


def clean(s:str)->str:
    s=s.replace('\uf0b7',' ').replace('\u2022',' ')
    s=re.sub(r'(?<=\w)-\s*\n\s*(?=\w)','',s)
    return re.sub(r'\s+',' ',s).strip()


def is_narrative(s:str,page:int)->bool:
    """Exclude table fragments, signatures, boilerplate and numeric-only text."""
    if page<=2:return False  # Cover and dense epidemiological tables
    if len(s)<90 or len(s.split())<16:return False
    n=normalize(s)
    if n.startswith(('tableau ','figure ','indicateurs ', 'province ', 'ministere ', 'task force ')):
        return False
    if '@' in s or 'www.' in n:return False
    letters=sum(c.isalpha() for c in s)
    if letters/len(s)<0.53:return False
    if len(re.findall(r'\d',s))>letters*.48:return False
    return True


def narrative_from_pdf(raw:bytes,*,report_number:int,date:str,source_url:str,expected_sha:str|None=None)->dict[str,Any]:
    sha=hashlib.sha256(raw).hexdigest()
    if expected_sha and sha!=expected_sha:raise ValueError('Source SHA256 mismatch; do not classify revised PDF')
    if not raw.startswith(b'%PDF-'):raise ValueError('Not a PDF')
    doc=pymupdf.open(stream=raw,filetype='pdf')
    if doc.is_encrypted or len(doc)<1:raise ValueError('Encrypted or empty PDF')
    cover=normalize(doc[0].get_text())
    if not re.search(r'(?:17\s*e|17eme|mve.?bdbv|bundibugyo|mve.?17)',cover):
        raise ValueError('Cover does not identify this epidemic')
    if str(report_number) not in cover:raise ValueError('Reported SitRep number not located on cover')
    records=[];blocks_seen=0;status=Counter();topics_total=Counter()
    for pi,page in enumerate(doc):
        for bi,block in enumerate(page.get_text('blocks',sort=True)):
            if len(block)<5 or block[6]!=0:continue
            raw_text=block[4]
            fragment=clean(raw_text)
            if not is_narrative(fragment,pi+1):continue
            blocks_seen+=1
            n=normalize(fragment)
            topics=sorted(k for k,rx in TOPICS.items() if re.search(rx,n,re.I))
            events=sorted(k for k,rx in EVENT_TYPES.items() if re.search(rx,n,re.I))
            provinces=sorted(k for k,rx in PROVINCES.items() if re.search(rx,n,re.I))
            # Do not treat a keyword as a verified event, and never infer causation.
            if not topics and not events:continue
            for topic in topics:topics_total[topic]+=1
            for ev in events:status[ev]+=1
            block_sha=hashlib.sha256(fragment.encode('utf-8')).hexdigest()
            records.append({
              'candidate_id':f'{report_number:03d}-p{pi+1:02d}-b{bi:03d}-{block_sha[:10]}',
              'page':pi+1,'block_index':bi,'source_text_sha256':block_sha,
              'excerpt':fragment[:340]+('…' if len(fragment)>340 else ''),
              'excerpt_truncated':len(fragment)>340,
              'topic_tags':topics,'event_type_candidates':events,
              'province_mentions':provinces,
              'geographic_status':'mentions_only_unverified',
              'classification_method':'lexical_rules_v1',
              'review_status':'REVIEW_REQUIRED',
            })
    return {'schema_version':SCHEMA,'report_number':report_number,'date':date,
            'source_url':source_url,'source_sha256':sha,'pages':len(doc),
            'pymupdf_version':pymupdf.VersionBind,
            'narrative_blocks_examined':blocks_seen,'candidates_count':len(records),
            'topics_counts':dict(topics_total),'event_type_counts':dict(status),
            'candidates':records,
            'status':'CANDIDATE_EXTRACTION_REVIEW_REQUIRED',
            'interpretation_policy':'Lexical categories and place names are leads, not verified findings; original PDF required for context.',
           }
