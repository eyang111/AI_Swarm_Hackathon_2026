exec(open('load.py').read())
import re, datetime as dt, bisect
TOK=re.compile(r'\b(?=[A-Za-z0-9_\-]*\d)(?=[A-Za-z0-9_\-]*[A-Za-z])[A-Za-z0-9_\-]{4,}\b|\b[A-Z][a-z]+(?:[A-Z][a-z0-9]+){2,}\b|\b[A-Za-z]+(?:-[A-Za-z0-9]+){1,}\b')
# dedupe exact copies first (reader sees one per distinct text)
seen=set(); U=[]
for r in revs:
    if r['h'] in seen: continue
    seen.add(r['h']); U.append(r)
for i,r in enumerate(U):
    r['i']=i; r['ts']=dt.datetime.fromisoformat(r['time'].replace('Z','+00:00'))
    r['toks']=set(TOK.findall(r['name']+'\n'+r['add']))
df=collections.Counter(t for r in U for t in r['toks'])
for r in U: r['dt']={t for t in r['toks'] if 2<=df[t]<=50}
# nearest earlier save sharing token
last={}; refs=[]
for r in U:
    near=None
    for t in r['dt']:
        if t in last:
            j=last[t]
            if near is None or j>near: near=j
    if near is not None: refs.append((r['i'],near))
    for t in r['dt']: last[t]=r['i']
# burst marking: saves in a 10-min span with >=100 distinct saves
ts=[r['ts'] for r in U]
burst=[False]*len(U)
for i,t in enumerate(ts):
    lo=bisect.bisect_left(ts,t-dt.timedelta(minutes=5)); hi=bisect.bisect_right(ts,t+dt.timedelta(minutes=5))
    burst[i]= hi-lo>=100
print('distinct saves',len(U),'in bursts',sum(burst),'refs',len(refs),'burst refs',sum(burst[i] for i,_ in refs))
import pickle; pickle.dump((U,refs,burst),open('u.pkl','wb'))
