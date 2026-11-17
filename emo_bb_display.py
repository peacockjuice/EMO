"""OLED compositor loaded only when BB mode is selected."""
import asyncio,time
import emo_bb as state
from emo_bb import status,FACES

def view(now):
    connection=status(now)
    elapsed=max(0,time.ticks_diff(now,state._card_at))
    phase=elapsed%8000
    if connection!='live':
        label={'waiting':'ЖДЁТ BB','offline':'НЕТ СВЯЗИ С BB','unknown':'СТАТУС BB НЕИЗВЕСТЕН'}[connection]
        counts=None;face='rosto04'
    else:
        label=state._snapshot['text'][:36].upper()
        counts=state._snapshot['counts'];kind=state._snapshot['face']
        face=FACES[kind]
        if kind=='question':face='rosto22' if phase<1000 else 'talk_bobo'
        if kind=='done' and elapsed>=3000:face='rosto01'
    if phase<2000:return face,label,counts,0
    # 3x glyphs, 0.5s lead/tail; the complete line fits the sender's 8s slot.
    distance=max(0,len(label)*18-3-128)
    offset=min(distance,max(0,(phase-2500)*distance//5000))
    return None,label,counts,offset

def overlay(o,label,counts,offset,large=False):
    from emo_font import text
    o.fill_rect(0,0,128,8,0)
    if counts is None:text(o,'BB ?',0,0)
    else:
        for x,symbol,n in zip((0,32,64,96),('>','?','!','*'),counts):
            text(o,symbol+(str(n) if n<100 else '99+'),x,0)
    if large:
        x=-offset if len(label)*18-3>128 else (128-(len(label)*18-3))//2
        text(o,label,x,25,3)

async def run(o):
    import bmo
    from emotion_sequences import SEQUENCES
    previous=None;face_start=time.ticks_ms();last_face=None;last_index=None
    with open('emotions.bin','rb') as bank:
        while bmo.S['ver']==bmo._v:
            now=time.ticks_ms();face,label,counts,offset=view(now)
            identity=(state._snapshot['card'] if state._snapshot else '',face)
            if identity!=last_face:face_start=now;last_face=identity
            index=None
            if face is not None:
                seq=SEQUENCES[face];elapsed=max(0,time.ticks_diff(now,face_start))%sum(ms for i,ms in seq)
                for i,ms in seq:
                    index=i
                    if elapsed<ms:break
                    elapsed-=ms
            signature=(index,label,tuple(counts) if counts else None,offset)
            if signature!=previous:
                if index is not None and index!=last_index:
                    bank.seek(index*1024)
                    if bank.readinto(o.buffer)!=1024:raise ValueError('truncated BB frame')
                    o.scroll(0,4)
                    last_index=index
                if index is None: o.fill_rect(0,0,128,64,0)
                last_index=index
                overlay(o,label,counts,offset,index is None);o.show()
                bmo.S['frames']=bmo.S.get('frames',0)+1;previous=signature
            await asyncio.sleep_ms(40)
    raise bmo.Changed
