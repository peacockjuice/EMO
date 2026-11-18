"""OLED drawing, loaded after the small scene and font modules."""
import asyncio,time
import emo_bb as state
import emo_bb_view as scene
view=scene.view

def overlay(o,label,counts,offset,large=False):
    if not large:return
    from emo_font import text
    o.fill_rect(0,0,128,20,0)
    if counts is None:text(o,'BB ?',0,4,2)
    else:
        for x,symbol,n in zip((0,32,64,96),('>','?','!','*'),counts):
            text(o,symbol,x,8)
            text(o,str(n) if n<100 else '99+',x+8,4 if n<100 else 8,2 if n<100 else 1)
    if large:
        x=-offset if len(label)*24-4>128 else (128-(len(label)*24-4))//2
        text(o,label,x,32,4)

async def run(o):
    scene._connection=None
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
                    last_index=index
                if index is None: o.fill_rect(0,0,128,64,0)
                last_index=index
                overlay(o,label,counts,offset,index is None);o.show()
                bmo.S['frames']=bmo.S.get('frames',0)+1;previous=signature
            await asyncio.sleep_ms(40)
    raise bmo.Changed
