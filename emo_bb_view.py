"""Attention phases, compiled separately to bound the ESP32 import peak."""
import time
import emo_bb as state
from emo_bb import status,FACES

# Connection warnings have their own clock: heartbeats must not restart reminders.
_connection=None
_connection_at=0

def view(now):
    global _connection,_connection_at
    connection=status(now)
    if connection!=_connection:_connection=connection;_connection_at=now
    elapsed=max(0,time.ticks_diff(now,state._card_at))
    phase=elapsed%8000
    if connection!='live':
        elapsed=max(0,time.ticks_diff(now,_connection_at))
        face='rosto16' if connection=='unknown' else 'rosto17'
        if connection=='waiting':
            if elapsed<30000:return 'rosto04','',None,0
            elapsed-=30000
        phase=elapsed%60000
        if phase>=8000:return face,'',None,0
        label='СТАТУС BB НЕИЗВЕСТЕН' if connection=='unknown' else 'НЕТ СВЯЗИ С BB'
        counts=None
    else:
        label=state._snapshot['text'][:36].upper()
        counts=state._snapshot['counts'];kind=state._snapshot['face']
        face=FACES[kind]
        if kind in ('work','wait','idle'):return face,'',None,0
        if kind=='question':face='rosto22' if phase<1000 else 'talk_bobo'
        if kind=='error':face='rosto17' if phase<1000 else 'rosto03'
        if kind=='done':
            # One notice per slot; a delayed heartbeat must not replay it forever.
            if elapsed>=8000:return 'rosto04','',None,0
            face='wink' if phase<1000 else 'rosto01'
    if phase<2000:return face,label,counts,0
    distance=max(0,len(label)*24-4-128)
    offset=min(distance,max(0,(phase-2500)*distance*1331//2500000))
    return None,label,counts,offset

