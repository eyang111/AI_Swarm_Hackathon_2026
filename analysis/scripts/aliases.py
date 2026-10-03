import re, gzip, orjson
AV='av/'
agents={orjson.loads(l)['id']:orjson.loads(l)['name'] for l in gzip.open(AV+'agents.jsonl.gz','rb')}
def aliases(n):
    a={n}
    if n.startswith('Claude '): a.add(n[7:])
    if n=='Opus 4.5 (Claude Code)': a={'Opus 4.5 (Claude Code)','Claude Code'}
    if n.startswith('[Temporary]'): a={n,'Temporary Fine-tuned Leader'}
    if n=='Fine-Tuned Leader': a={n,'Fine-tuned Leader','Finetuned Leader'}
    if n.startswith('GPT-5.6 '): a.add(n.split()[-1]) if n.split()[-1] in('Sol','Terra','Luna') else None
    if n=='GPT-6 Astra': a.add('Astra')
    if n=='Muse Spark 1.3': a.add('Muse Spark')
    if n=='DeepSeek-V3.2': a|={'DeepSeek V3.2','DeepSeek-V3','V3.2'}
    if n=='DeepSeek-V4-Pro': a|={'DeepSeek V4','DeepSeek-V4','V4-Pro','V4 Pro'}
    return a
ALIAS={n:aliases(n) for n in agents.values()}
# build regex: longest first, word-boundary, avoid 'Opus 4.5' matching inside 'Opus 4.5 (Claude Code)' ok
pairs=sorted([(al,n) for n,als in ALIAS.items() for al in als],key=lambda x:-len(x[0]))
def find_mentions(text):
    found=set(); t=text
    for al,n in pairs:
        pat=r'(?<![\w.])'+re.escape(al)+r'(?![\w.]*\d)(?!\w)'
        if re.search(pat,t):
            found.add(n); t=re.sub(pat,' ',t)
    return found
