"""Public INSP / INRB SitRep document discovery (no credentials or page scraping tricks)."""
from __future__ import annotations
import html
import json
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from urllib.parse import unquote, quote, urlparse
import requests
from bs4 import BeautifulSoup

USER_AGENT = "African-Intelligence-SitRep-Metadata/0.1 (public-research; source attribution)"
GITHUB_API = 'https://api.github.com/repos/INRB-UMIE/BDBV2026-Data/git/trees/main?recursive=1'
GITHUB_BASE = 'https://raw.githubusercontent.com/INRB-UMIE/BDBV2026-Data/main/'
INSP_URLS = ('https://insp.cd/sitrep/', 'https://insp.cd/ebola/', 'https://insp.cd/ebola-17eme-epidemie/')
WP_API = 'https://insp.cd/wp-json/wp/v2/media'
PDF_URL = re.compile(r'https?://(?:www\.)?insp\.cd/(?:wp-content/uploads/2026/[^\s"\'<>\\]+?\.pdf)', re.I)
SITREP_NUMBER = re.compile(r'(?:sitrep)[^0-9]{0,30}(?P<number>\d{1,3})(?!\d)', re.I)

@dataclass
class Source:
    number: int
    url: str
    provider: str
    basename: str


def number_from_string(text: str) -> int | None:
    """Report number from filename or title; reject implausible identifications."""
    name = unquote(text.rsplit('/', 1)[-1])
    m = SITREP_NUMBER.search(name)
    return int(m.group('number')) if m and 1 <= int(m.group('number')) <= 400 else None


def session() -> requests.Session:
    s=requests.Session()
    s.headers.update({'User-Agent': USER_AGENT, 'Accept': 'application/json, text/html, application/pdf; q=0.9'})
    return s


def get(session: requests.Session, url: str, *, timeout: int = 30) -> requests.Response:
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r


def discover_github(s: requests.Session) -> list[Source]:
    response = get(s, GITHUB_API)
    tree = response.json()
    if tree.get('truncated'):
        raise RuntimeError('GitHub tree listing truncated: cannot certify document coverage')
    found = []
    for item in tree.get('tree', []):
        path = item.get('path','')
        if item.get('type') != 'blob' or not re.search(r'^data/insp_sitrep/raw/.+\.pdf$',path,re.I):
            continue
        no = number_from_string(path)
        if no is None: continue
        found.append(Source(no,GITHUB_BASE+quote(path,safe='/'),'INRB-GitHub',path.rsplit('/',1)[-1]))
    return found


def source_from_insp_url(url: str) -> Source | None:
    url = html.unescape(unquote(url)).replace('\\/','/')
    parsed = urlparse(url)
    # The INSP site hosts 2025/2026 Ebola reports; only target the 2026 archive.
    if parsed.hostname not in {'insp.cd','www.insp.cd'} or '/wp-content/uploads/2026/' not in parsed.path:
        return None
    if not parsed.path.lower().endswith('.pdf'):
        return None
    no=number_from_string(parsed.path)
    if no is None:return None
    return Source(no,url,'INSP-official',parsed.path.rsplit('/',1)[-1])


def extract_insp_links(page_html: str) -> list[Source]:
    text = html.unescape(page_html).replace('\\/','/')
    soup=BeautifulSoup(text,'html.parser')
    candidates = set(PDF_URL.findall(text))
    for tag in soup.select('[href], [src], [data-url]'):
        for k in ('href','src','data-url'):
            x=tag.get(k)
            if isinstance(x,str) and x.startswith('https://insp.cd/'):
                candidates.add(x)
    return [src for item in candidates if (src:=source_from_insp_url(item))]


def discover_insp(s:requests.Session,max_pages:int=5)->tuple[list[Source],list[str]]:
    found=[];errors=[]
    for url in INSP_URLS:
        try:found.extend(extract_insp_links(get(s,url,timeout=20).text))
        except Exception as e:errors.append(f'INSP listing inaccessible ({url}): {str(e)[:110]}')
    # WordPress media metadata provides direct PDF URLs even if landing pages embed via JS.
    for page in range(1,max_pages+1):
        try:
            r=get(s,WP_API,timeout=20) if False else s.get(WP_API,params={'search':'SitRep','per_page':100,'page':page},timeout=20)
            if r.status_code in (400,404):break
            r.raise_for_status(); items=r.json()
            if not isinstance(items,list):break
            for item in items:
                for u in (item.get('source_url',''),item.get('guid',{}).get('rendered','')):
                    if src:=source_from_insp_url(str(u)):found.append(src)
            if len(items)<100:break
        except Exception as e:
            errors.append(f'INSP WordPress media API inaccessible: {str(e)[:110]}');break
    found=list({(x.number,x.url):x for x in found}.values())
    return found,errors


def discover_all(s:requests.Session)->tuple[list[dict], list[str]]:
    errors=[]
    try:git=discover_github(s)
    except Exception as e:git=[];errors.append(f'GitHub catalogue inaccessible: {str(e)[:120]}')
    insp,errs=discover_insp(s);errors+=errs
    byno=defaultdict(list)
    for x in git+insp:byno[x.number].append(asdict(x))
    items=[]
    for number, sources in byno.items():
        sources.sort(key=lambda x: 0 if x['provider']=='INSP-official' else 1)
        items.append({'number':number,'sources':sources})
    items.sort(key=lambda x:x['number'],reverse=True)
    return items,errors
