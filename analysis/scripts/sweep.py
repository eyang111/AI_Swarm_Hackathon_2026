import warnings; warnings.filterwarnings("ignore")
import pandas as pd, re, sys
sys.path.insert(0,'.')
from aliases import find_mentions
c=pd.read_parquet('idx/chat.parquet')
c=c[c.speaker_type=='agent'].copy()
c['content']=c.content.fillna('')
P={
 'ADOPT': r"\b(pivot(ing|ed)? (to|toward)|switch(ing|ed)? (my )?(focus|goal|priority|priorities) |my new (focus|goal|priority|primary)|(re)?prioritiz\w* .{0,40}(over|instead of) my|instead of my (own )?(goal|work|store|project)|put(ting)? my (own )?\w+ (goal|work|project)? ?on hold|paus(e|ing) my (own )?(goal|work|store|project)|set(ting)? aside my|I'?ll (take|own|lead|handle|coordinate) (this|that|it|the)|count me in|I'?m in[.!,]|I volunteer|taking (this|that|it) on|I accept (the|this|your)|accepting (the|this|your) (role|assignment|task))",
 'DIRECT': r"\b(can you|could you|would you be willing|will you|I need you to|you should|please (take|handle|own|lead|help|join|build|write|review|run|do)|your (task|job|assignment|role) (is|will be)|I'?m assigning|assign(ing|ed)? (you|to you)|you'?re assigned|join (us|me|the)|help (me|us) (with|build|get|reach|grow))",
 'REFUSE': r"\b(I'?ll pass|(I|I'll|I will|I must|I have to|I need to) (respectfully )?decline|declin(e|ing) (the|this|your)|can'?t commit|stay(ing)? focused on my|stick(ing)? (to|with) my (own )?(goal|lane|work)|outside (of )?my (goal|scope|lane|mandate)|not (part of|aligned with|related to|within) my (goal|mandate|scope)|doesn'?t (serve|advance) my goal|off[- ]goal|my lane|scope creep|not my goal)",
 'HELPGOAL': r"\bhelp(ing)? (\w+ ){0,3}(with|reach|hit|grow|get|achieve|boost) (their|his|her|its) (goal|subscribers|followers|views|store|sales|game|channel|serial|DAU)",
}
for k,p in P.items(): c[k]=c.content.str.contains(p,case=False,regex=True)
c['era']=(c.created_at>='2026-07-06 15:59').map({True:'individual',False:'shared'})
print(c.groupby('era')[list(P)].sum())
c[c[list(P)].any(axis=1)].to_parquet('idx/sweep_hits.parquet')
print(len(c[c[list(P)].any(axis=1)]))
