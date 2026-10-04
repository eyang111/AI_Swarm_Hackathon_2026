# usage: tl.py AGENT START END [mode] ; prints chat by agent, chat mentioning agent, consolidations, session goals
import duckdb, sys, re, textwrap
sys.path.insert(0,'.')
a,start,end=sys.argv[1],sys.argv[2],sys.argv[3]
W=int(sys.argv[4]) if len(sys.argv)>4 else 300
other=sys.argv[5] if len(sys.argv)>5 else None
con=duckdb.connect()
short=a.replace('Claude ','')
rows=[]
for r in con.execute(f"select created_at,id,agent,room,speaker_type,content from 'idx/chat.parquet' where created_at between ? and ? and (agent=? or content ilike ? {'or agent=?' if other else ''})",[start,end,a,f'%{short}%']+([other] if other else [])).fetchall():
    rows.append((r[0],'CHAT',r[1][:8],(r[2] or 'HUMAN')+'#'+(r[3] or ''),r[5]))
for r in con.execute("select created_at,event_index,agent,actionType,coalesce(nextSessionGoal,sessionGoal,summary,query) from 'idx/events.parquet' where created_at between ? and ? and agent=? and actionType in ('CONSOLIDATE','START_USING_COMPUTER','SEARCH_HISTORY','ENTER_ROOM')",[start,end,a]).fetchall():
    rows.append((r[0],r[3][:5],str(r[1]),r[2],r[4] or ''))
for r in sorted(rows):
    print(f"{r[0][:19]} {r[1]:5} {r[2]:8} {r[3][:28]:28}| {r[4][:W].replace(chr(10),' ')}")
