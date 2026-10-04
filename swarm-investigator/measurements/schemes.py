import pickle,collections,datetime as dt,bisect,statistics as st
U,refs,burst=pickle.load(open('u.pkl','rb'))
N=len(U); ts=[r['ts'] for r in U]
def evaluate(view):  # view(i) -> set of indices visible (core+halo) to reader of save i
    ok=collections.Counter(); tot=collections.Counter()
    for i,j in refs:
        k='burst' if burst[i] else 'quiet'; tot[k]+=1
        if j in view(i): ok[k]+=1
    return {k:round(ok[k]/tot[k],3) for k in tot}
# A: count windows
win=[i//100 for i in range(N)]
def viewA(i):
    s=win[i]*100; return set(range(max(0,s-50),min(N,s+100)))
print('A count 100+50:',evaluate(viewA))
# B: halo = max(50 saves, all saves in previous 15 min), cap 400
def viewB(i, minutes=15, cap=400):
    s=win[i]*100; lo=bisect.bisect_left(ts,ts[s]-dt.timedelta(minutes=minutes))
    lo=max(min(lo,s-50),s-cap,0); return set(range(lo,min(N,s+100)))
print('B time-floor 15min cap400:',evaluate(viewB))
hs=[min(400,max(50,win[s]*0+ (s-bisect.bisect_left(ts,ts[s]-dt.timedelta(minutes=15))))) for s in range(0,N,100)]
print('  B halo sizes median/p90/max',st.median(hs),sorted(hs)[int(.9*len(hs))],max(hs))
# C: burst segments clustered by shared tokens / page
par=list(range(N))
def f(x):
    while par[x]!=x: par[x]=par[par[x]]; x=par[x]
    return x
def u(a,b): par[f(a)]=f(b)
# segments
segs=[];cur=[]
for i in range(N):
    if burst[i]: cur.append(i)
    elif cur: segs.append(cur);cur=[]
if cur: segs.append(cur)
for seg in segs:
    lastt={}; lastp={}
    for i in seg:
        for t in U[i]['dt']:
            if t in lastt: u(i,lastt[t])
            lastt[t]=i
        p=U[i]['name']
        if p in lastp: u(i,lastp[p])
        lastp[p]=i
# windows: quiet = count windows over quiet saves; burst = per component chunks of 100
wid=[None]*N; members=collections.defaultdict(list)
q=[i for i in range(N) if not burst[i]]
for n,i in enumerate(q): wid[i]=('q',n//100); members[wid[i]].append(i)
comp=collections.defaultdict(list)
for seg_n,seg in enumerate(segs):
    for i in seg: comp[(seg_n,f(i))].append(i)
sizes=sorted(len(v) for v in comp.values())
print('burst components',len(comp),'largest',sizes[-5:],'singletons',sum(1 for s in sizes if s==1))
for key,v in comp.items():
    for n in range(0,len(v),100):
        for i in v[n:n+100]: wid[i]=('b',key,n//100); members[wid[i]].append(i)
cache={}
def viewC(i):
    w=wid[i]
    if w in cache: return cache[w]
    core=members[w]; s=min(core)
    halo=set(range(max(0,s-50),s))  # last 50 global
    if w[0]=='b':
        key=w[1]; v=comp[key]; k=w[2]*100
        halo|=set(v[max(0,k-50):k])  # previous 50 of same cluster
    cache[w]=set(core)|halo; return cache[w]
print('C burst clusters:',evaluate(viewC))
nwin=len(members); print('windows A',max(win)+1,'C',nwin, 'C window sizes median',st.median(len(m) for m in members.values()))
