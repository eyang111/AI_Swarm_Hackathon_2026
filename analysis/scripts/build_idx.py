import gzip, orjson, pandas as pd
AV='av/'; IDX='idx/'
def load(f): return [orjson.loads(l) for l in gzip.open(AV+f,'rb')]
agents={a['id']:a['name'] for a in load('agents.jsonl.gz')}
rooms={r['id']:r['name'] for r in load('chat_rooms.jsonl.gz')}
# chat
rows=load('chat_messages.jsonl.gz')
df=pd.DataFrame(rows)
df['agent']=df.agent_speaker_id.map(agents)
df['room']=df.room_id.map(rooms)
df=df.sort_values('created_at')
df[['id','created_at','speaker_type','agent','agent_speaker_id','user_speaker_id','room','room_id','content','has_been_approved']].to_parquet(IDX+'chat.parquet')
print('chat',len(df))
# sessions
s=pd.DataFrame(load('computer_use_sessions.jsonl.gz')); s['agent']=s.agent_id.map(agents)
s.sort_values('created_at').to_parquet(IDX+'sessions.parquet'); print('sessions',len(s))
# events
keep=['actionType','speakerId','agentId','roomId','roomName','content','messageId','speakerName','speakerType','sessionGoal','shortDisplayedSessionGoal','nextSessionGoal','nextShortDisplayedSessionGoal','summary','query','answerToQuery','startDay','endDay','currentRooms','previousRoomName','computerUseSessionId','seconds','medium','recipient','messageContent','approval','adminComment','rationale','humanConstraints','endReason','endComment','oldName','newName','userId']
E=[];O=[]
with gzip.open(AV+'events.jsonl.gz','rb') as f:
    for l in f:
        d=orjson.loads(l); dd=d['data']
        r={'event_index':d['event_index'],'id':d['id'],'created_at':d['created_at']}
        for k in keep:
            v=dd.get(k)
            r[k]=None if v is None else (v if isinstance(v,str) else orjson.dumps(v).decode())
        E.append(r)
        o=dd.get('output')
        if o is not None:
            O.append({'event_index':d['event_index'],'output':o if isinstance(o,str) else orjson.dumps(o).decode()})
e=pd.DataFrame(E)
e['agent']=e.agentId.fillna(e.speakerId).map(agents)
e['room']=e.roomId.map(rooms)
e=e.sort_values('event_index')
e.to_parquet(IDX+'events.parquet'); print('events',len(e))
pd.DataFrame(O).to_parquet(IDX+'event_outputs.parquet',compression='zstd'); print('outputs',len(O))
