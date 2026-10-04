import gzip,json,collections,re,datetime
D='/mnt/project-files/dsewiki/raw/'
R=[json.loads(l) for l in gzip.open(D+'revisions.jsonl.gz')]
P={p['page_id']:p for p in (json.loads(l) for l in gzip.open(D+'pages.jsonl.gz'))}
MON='jan feb mar apr may jun jul aug sep oct nov dec'.split()
MONRE=r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*'
def datetag(s):
    m=re.search(MONRE+r'(\d{1,2})(?!\d)',s or '')
    if m: return m.group(1)+'%02d'%int(m.group(2))
    return None
def toks(s):
    s=re.sub(r'(\d+)',r' \1 ',s); s=re.sub(r'([a-z])([A-Z])',r'\1 \2',s); s=re.sub(r'([A-Z]+)([A-Z][a-z])',r'\1 \2',s)
    return [t.lower() for t in re.split(r'[\s_\-\.]+',s) if t]
GENERIC=set('agent research researcher helper open ai oai x xyz zz z data test user bot reader scout watcher new a b final mass guest my the'.split())|set(MON)
def stem(s):
    t=[x for x in toks(s) if not x.isdigit() and x not in MON and not (len(x)<=3 and x in GENERIC)]
    return tuple(t)
def content(s):
    return frozenset(x for x in toks(s) if not x.isdigit() and x not in GENERIC and len(x)>1)
COH=re.compile(r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\d{1,2})\s+cohort\b',re.I)
SIG=[re.compile(r'(?m)^\s*[-—–~]{1,4}\s*([A-Z][\w\-]{2,40})\s*$'),
     re.compile(r'(?i)\b(?:from|by)\s+(?:agent\s+)?([A-Z][A-Za-z0-9]{3,40}(?:Agent|Bot|Helper|Researcher|Scout|Watcher)[A-Za-z0-9]*)')]
def norm_tag(t):
    m=re.match(r'([A-Za-z]{3})(\d+)',t); return m.group(1).capitalize()+'%02d'%int(m.group(2))
for r in R:
    b=r['body'] or ''
    r['ndate']=datetag(r['label'])
    r['coh']={norm_tag(x) for x in COH.findall(b)}
    r['sig']={x for p in SIG for x in p.findall(b)}
    r['ts']=datetime.datetime.fromisoformat(r['time'].replace('Z','+00:00')).timestamp()
    r['pcoh']=P.get(r['page_id'],{}).get('page_family_cohort')
    r['ptitledate']=datetag(r['name'])
for r in R:
    lines=(r['body'] or '').split('\n')
    if r['hunks']:
        add='\n'.join('\n'.join(lines[h['b0']:h['b1']]) for h in r['hunks'] if h['op'] in ('insert','replace'))
    else: add=r['body'] or ''
    r['add']=add
    r['acoh']={norm_tag(x) for x in COH.findall(add)}
    r['asig']={x for p in SIG for x in p.findall(add)}
    r['adates']={datetag(m.group(0)) for m in re.finditer(MONRE+r'\d{1,2}(?!\d)',add)}
