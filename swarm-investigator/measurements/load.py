import gzip,json,re,hashlib,unicodedata,collections
def added(r):
    lines=r['body'].split('\n')
    out=[]
    for h in r['hunks'] or []:
        if h['op'] in('insert','replace'): out+=lines[h['b0']:h['b1']]
    if not r['hunks'] and r['diff_base'] is None: out=lines
    return '\n'.join(out)
def norm(s): return re.sub(r'\s+',' ',unicodedata.normalize('NFC',s)).strip()
revs=[json.loads(l) for l in gzip.open('/mnt/project-files/dsewiki/raw/revisions.jsonl.gz')]
revs.sort(key=lambda r:(r['time'],r['rev_id']))
for r in revs:
    r['add']=added(r); r['h']=hashlib.sha1(norm(r['add']).encode()).hexdigest()
