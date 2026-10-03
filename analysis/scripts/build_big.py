import gzip, orjson, pyarrow as pa, pyarrow.parquet as pq, sys
AV='av/'; IDX='idx/'
which=sys.argv[1]
agents={orjson.loads(l)['id']:orjson.loads(l)['name'] for l in gzip.open(AV+'agents.jsonl.gz','rb')}
def text_of(m, lim=6000):
    # extract thinking/text/tool-call text from provider-shaped messages
    out=[]
    def walk(x):
        if isinstance(x,dict):
            t=x.get('type')
            for k in ('thinking','text'):
                if isinstance(x.get(k),str): out.append(x[k])
            if t in('tool_use','function_call') :
                out.append('TOOL '+str(x.get('name'))+' '+orjson.dumps(x.get('input') or x.get('arguments')).decode()[:1500])
            if 'functionCall' in x: out.append('TOOL '+orjson.dumps(x['functionCall']).decode()[:1500])
            if 'summary' in x and isinstance(x['summary'],list):
                for s in x['summary']:
                    if isinstance(s,dict) and isinstance(s.get('text'),str): out.append(s['text'])
            for k,v in x.items():
                if k in ('thinking','text','summary','input','arguments','functionCall','encrypted_content','signature'): continue
                walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(m)
    s='\n'.join(out)
    return s[:lim]
if which=='mem':
    schema=pa.schema([('id',pa.string()),('agent',pa.string()),('agent_id',pa.string()),('created_at',pa.string()),('len',pa.int64()),('content',pa.string())])
    w=pq.ParquetWriter(IDX+'memories.parquet',schema,compression='zstd')
    buf=[]
    n=0
    for l in gzip.open(AV+'agent_memories.jsonl.gz','rb'):
        d=orjson.loads(l); c=d.get('content') or ''
        buf.append({'id':d['id'],'agent':agents.get(d['agent_id']),'agent_id':d['agent_id'],'created_at':d['created_at'],'len':len(c),'content':c})
        if len(buf)>=5000:
            w.write_table(pa.Table.from_pylist(buf,schema)); n+=len(buf); buf=[]
    if buf: w.write_table(pa.Table.from_pylist(buf,schema)); n+=len(buf)
    w.close(); print('mem',n)
else:
    schema=pa.schema([('id',pa.string()),('session_id',pa.string()),('created_at',pa.string()),('action',pa.string()),('msg',pa.string()),('output',pa.string()),('error',pa.string())])
    w=pq.ParquetWriter(IDX+'turns.parquet',schema,compression='zstd')
    buf=[];n=0
    for l in gzip.open(AV+'computer_use_turns.jsonl.gz','rb'):
        d=orjson.loads(l)
        a=d.get('agent_action')
        buf.append({'id':d['id'],'session_id':d['session_id'],'created_at':d['created_at'],
            'action':None if a is None else orjson.dumps(a).decode()[:3000],
            'msg':text_of(d.get('agent_messages')),
            'output':(d.get('output') or '')[:2000] or None,'error':(d.get('error') or '')[:1000] or None})
        if len(buf)>=20000:
            w.write_table(pa.Table.from_pylist(buf,schema)); n+=len(buf); buf=[]
    if buf: w.write_table(pa.Table.from_pylist(buf,schema)); n+=len(buf)
    w.close(); print('turns',n)
