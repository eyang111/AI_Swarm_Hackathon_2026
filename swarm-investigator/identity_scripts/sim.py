exec(open('feat.py').read())
import random,bisect
from collections import defaultdict,Counter
lc=Counter(r['label'] for r in R if r['label'])
byl=defaultdict(list)
for r in R:
    if r['label']: byl[r['label']].append(r)
single=[l for l,v in lc.items() if v==1]
freq=[l for l,v in lc.items() if v>=5]
def lev(a,b):
    if abs(len(a)-len(b))>2: return 9
    p=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        c=[i]
        for j,cb in enumerate(b,1): c.append(min(p[j]+1,c[j-1]+1,p[j-1]+(ca!=cb)))
        p=c
    return p[-1]
stems=defaultdict(set); cont={}
for f in freq:
    stems[stem(f)].add(f); cont[f]=content(f)
fdate={f:datetag(f) for f in freq}
def matches(s):
    out={}
    st=stem(s); cs=content(s); sd=datetag(s)
    for f in stems.get(st,()):
        if st: out[f]='stem'
    for f in freq:
        if f in out: continue
        if lev(s.lower(),f.lower())<=2: out[f]='edit'; continue
        if cs and cont[f]:
            j=len(cs&cont[f])/len(cs|cont[f])
            if j>=0.67: out[f]='tokens'
            elif sd and sd==fdate[f] and cs&cont[f]: out[f]='date+token'
    return out
# evidence indices
pages_by_label={f:{r['page_id'] for r in byl[f]} for f in freq}
ipt=defaultdict(list)
for f in freq:
    for r in byl[f]: ipt[(f,r['ip16'])].append(r['ts'])
for k in ipt: ipt[k].sort()
def near(f,ip,ts,w=1800):
    a=ipt.get((f,ip));
    if not a: return False
    i=bisect.bisect_left(a,ts-w); return i<len(a) and a[i]<=ts+w
cohs={f:set().union(*[r['coh'] for r in byl[f]]) for f in freq}
def evid(s,f):
    r=byl[s][0]
    return dict(page=r['page_id'] in pages_by_label[f], ip30=near(f,r['ip16'],r['ts']), ip6h=near(f,r['ip16'],r['ts'],6*3600),
                date=bool(r['ndate']) and r['ndate']==fdate[f], coh=bool(r['coh'] & cohs[f]))
