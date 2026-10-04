# usage: memgrep.py AGENT START END REGEX [ctx] [maxhits]
import duckdb,re,sys
a,s,e,rx=sys.argv[1:5]; ctx=int(sys.argv[5]) if len(sys.argv)>5 else 250; mx=int(sys.argv[6]) if len(sys.argv)>6 else 2
con=duckdb.connect()
rows=con.execute("select created_at,id,len,content from 'idx/memories.parquet' where agent=? and created_at between ? and ? order by created_at",[a,s,e]).fetchall()
print(len(rows),'memory rows')
R=re.compile(rx,re.I)
for c,i,l,t in rows:
    ms=list(R.finditer(t))
    if not ms: continue
    print(c[:19],i[:8],'len',l,'hits',len(ms))
    for m in ms[:mx]:
        print('   …',t[max(0,m.start()-ctx):m.end()+ctx].replace('\n',' '))
