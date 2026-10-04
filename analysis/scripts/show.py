import pandas as pd, re, sys, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from sweep_pats import P
h=pd.read_parquet('idx/sweep_hits.parquet')
k=sys.argv[1]; era=sys.argv[2]; W=int(sys.argv[3]) if len(sys.argv)>3 else 130
h=h[(h[k])&(h.era==era)]
for _,r in h.iterrows():
    m=re.search(P[k],r.content,re.I)
    s=max(0,m.start()-W); t=r.content[s:m.end()+W].replace('\n',' ')
    print(f"{r.created_at[:16]} {r.id[:8]} {r.agent[:16]:16} #{(r.room or '')[:7]}: …{t}…")
