"""Bounded notification HTTP transport, compiled separately to preserve Wi-Fi heap."""
import asyncio,time,json,hashlib
import emo_bb as state
from emo_bb import hexed,key,accept,challenge
from ota_protocol import mac,equal

def memory():
    import gc
    gc.collect()
    result={'heap':gc.mem_free()}
    try:
        import esp32
        heaps=esp32.idf_heap_info(esp32.HEAP_DATA)
        result['native_heap']=sum(h[1] for h in heaps)
        result['native_largest']=max(h[2] for h in heaps)
    except (ImportError,AttributeError):pass
    return result

async def reply(w,code,value,nonce=None):
    raw=json.dumps(value).encode()
    head='HTTP/1.0 %d Result\r\nContent-Type: application/json\r\nContent-Length: %d\r\nCache-Control: no-store\r\nConnection: close\r\n'%(code,len(raw))
    if nonce:head+='X-EMO-Reply: '+hexed(mac(key(),nonce.encode()+b'\n'+raw))+'\r\n'
    w.write(head+'\r\n');w.write(raw);await asyncio.wait_for(w.drain(),3)

async def handle(method,path,headers,r,w,version):
    import bmo
    if path=='/bb/challenge' and method=='GET':
        await reply(w,200,challenge());return
    if path!='/bb/state' or method!='POST':
        await reply(w,404,{'ok':False});return
    nonce=headers.get('x-emo-nonce','')
    if not state._nonce or nonce!=state._nonce or time.ticks_diff(time.ticks_ms(),state._nonce_at)>5000:
        await reply(w,401,{'ok':False});return
    try:
        if 'transfer-encoding' in headers:raise ValueError('encoding')
        size=int(headers.get('content-length','0'))
        if not 0<size<=1024:raise ValueError('size')
        raw=await asyncio.wait_for(r.readexactly(size),3)
        # Reading the body yields: another request may consume or replace this nonce.
        if nonce!=state._nonce or time.ticks_diff(time.ticks_ms(),state._nonce_at)>5000:
            await reply(w,401,{'ok':False});return
        digest=hexed(hashlib.sha256(raw).digest())
        signed=('POST\n/bb/state\n'+nonce+'\n'+digest).encode()
        if not equal(hexed(mac(key(),signed)).encode(),headers.get('x-emo-signature','').encode()):
            await reply(w,401,{'ok':False});return
        state._nonce=None
        try: result=accept(json.loads(raw),version)
        except (ValueError,TypeError,KeyError):
            await reply(w,409,{'ok':False,'error':'invalid_or_stale'},nonce);return
        metrics=memory()
        metrics.update({'ok':True,'status':result,'boot':state._boot,'epoch':state._epoch,'seq':state._seq,'frames':bmo.S.get('frames',0)})
        await reply(w,200,metrics,nonce)
    except (ValueError,TypeError):
        await reply(w,400,{'ok':False})

