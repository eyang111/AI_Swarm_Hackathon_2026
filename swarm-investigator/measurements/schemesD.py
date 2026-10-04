import pickle,collections,datetime as dt,bisect,statistics as st
U,refs,burst=pickle.load(open('u.pkl','rb'))
N=len(U); ts=[r['ts'] for r in U]; L=[len(r['add'])+len(r['name']) for r in U]
def evaluate(view):
    ok=collections.Counter(); tot=collections.Counter()
    for i,j in refs:
        k='burst' if burst[i] else 'quiet'; tot[k]+=1
        if j in view(i): ok[k]+=1
    return {k:round(ok[k]/tot[k],3) for k in tot}
# index token -> list of save indices (ascending)
idx=collections.defaultdict(list)
for r in U:
    for t in r['dt']: idx[t].append(r['i'])
def build(minutes, routed_cap, per_tok=2):
    views={}; hsz=[]; hch=[]
    for s in range(0,N,100):
        core=range(s,min(N,s+100)); base=set(range(max(0,s-50),s))
        lo=bisect.bisect_left(ts,ts[s]-dt.timedelta(minutes=minutes))
        routed=[]
        for i in core:
            for t in U[i]['dt']:
                lst=idx[t]; p=bisect.bisect_left(lst,s)  # earlier than window start
                for j in lst[max(0,p-per_tok):p]:
                    if j>=lo and j not in base: routed.append(j)
        # keep most recent unique up to cap
        routed=sorted(set(routed),reverse=True)[:routed_cap]
        halo=base|set(routed); hsz.append(len(halo)); hch.append(sum(L[j] for j in halo))
        v=set(core)|halo
        for i in core: views[i]=v
    return views,hsz,hch
for minutes,cap in [(60,100),(24*60,150)]:
    views,hsz,hch=build(minutes,cap)
    print(f'D last50 + routed (lookback {minutes}m, cap {cap}):',evaluate(lambda i:views[i]),'halo median',st.median(hsz),'p90',sorted(hsz)[int(.9*len(hsz))],'halo chars median',st.median(hch))
core_ch=[sum(L[s:s+100]) for s in range(0,N,100)]
print('core chars median',st.median(core_ch),'p90',sorted(core_ch)[int(.9*len(core_ch))],'max',max(core_ch))
