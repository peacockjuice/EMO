"""LAN update service, port 8080. Shared-key authentication; key never crosses network."""
import asyncio,os,time,json,hashlib,binascii,struct
import ota_boot as boot
import ota_protocol as protocol
_nonce=None
_nonce_at=0
_busy=False
_server=None
_connections=0

def hexed(value):return binascii.hexlify(value).decode()
def key():
    with open('/.ota_key','rb') as f:value=f.read(33)
    if len(value)!=32:raise ValueError('key configuration')
    return value

async def line(r,limit,started):
    data=bytearray()
    while len(data)<=limit:
        if time.ticks_diff(time.ticks_ms(),started)>10000:raise ValueError('header deadline')
        c=await asyncio.wait_for(r.read(1),5)
        if not c:raise ValueError('closed headers')
        data.extend(c)
        if data[-2:]==b'\r\n':return bytes(data[:-2])
    raise ValueError('header too long')

async def request(r):
    started=time.ticks_ms()
    parts=(await line(r,128,started)).decode().split(' ')
    if len(parts)!=3:raise ValueError('request line')
    headers={};total=0
    for _ in range(20):
        raw=await line(r,256,started);total+=len(raw)
        if total>2048:raise ValueError('headers too large')
        if not raw:return parts[0],parts[1],headers
        name,value=raw.decode().split(':',1);name=name.lower().strip()
        if name in headers:raise ValueError('duplicate header')
        headers[name]=value.strip()
    raise ValueError('too many headers')

def challenge():
    global _nonce,_nonce_at
    now=time.ticks_ms()
    if _nonce is None or time.ticks_diff(now,_nonce_at)>30000:
        _nonce=hexed(os.urandom(24));_nonce_at=now
    return _nonce

def authenticate(path,headers):
    global _nonce
    nonce=headers.get('x-emo-nonce','');digest=headers.get('x-emo-sha256','')
    if not _nonce or nonce!=_nonce or time.ticks_diff(time.ticks_ms(),_nonce_at)>30000:return None
    if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):return None
    data=('POST\n'+path+'\n'+nonce+'\n'+digest).encode()
    expected=hexed(protocol.mac(key(),data))
    if not protocol.equal(expected.encode(),headers.get('x-emo-signature','').encode()):return None
    _nonce=None
    return nonce

async def respond(w,code,obj,nonce=None):
    body=json.dumps(obj).encode()
    header='HTTP/1.0 %d Result\r\nContent-Type: application/json\r\nContent-Length: %d\r\nCache-Control: no-store\r\nConnection: close\r\n'%(code,len(body))
    if nonce:header+='X-EMO-Reply: '+hexed(protocol.mac(key(),nonce.encode()+b'\n'+body))+'\r\n'
    w.write(header+'\r\n');w.write(body);await w.drain()

async def exact(r,n,body_hash,started):
    data=bytearray()
    while len(data)<n:
        if time.ticks_diff(time.ticks_ms(),started)>90000:raise ValueError('upload deadline')
        chunk=await asyncio.wait_for(r.read(min(1024,n-len(data))),5)
        if not chunk:raise ValueError('truncated body')
        data.extend(chunk);body_hash.update(chunk)
    return bytes(data)

def clear_slot(slot):
    if slot not in ('/ota_a','/ota_b') or slot==boot._running:raise ValueError('active slot')
    try:os.mkdir(slot)
    except OSError:pass
    for name in os.listdir(slot):os.remove(boot.path(slot,name))

async def upload(r,size,digest):
    if boot._state.get('pending'):raise ValueError('pending update')
    started=time.ticks_ms();body_hash=hashlib.sha256()
    n=struct.unpack('>I',await exact(r,4,body_hash,started))[0]
    if not 0<n<=protocol.MAX_MANIFEST:raise ValueError('manifest size')
    raw=await exact(r,n,body_hash,started);manifest=json.loads(raw)
    files=protocol.validate(manifest,size,n)
    slot='/ota_b' if boot._running=='/ota_a' else '/ota_a'
    clear_slot(slot)
    stats=os.statvfs('/')
    if stats[1]*stats[4]<size+65536:raise ValueError('insufficient space')
    try:
        for item in files:
            remaining=item['size'];h=hashlib.sha256()
            with open(boot.path(slot,item['name']),'wb') as f:
                while remaining:
                    chunk=await exact(r,min(1024,remaining),body_hash,started)
                    f.write(chunk);h.update(chunk);remaining-=len(chunk)
                    await asyncio.sleep_ms(0)
            if hexed(h.digest())!=item['sha256']:raise ValueError('file digest')
        if hexed(body_hash.digest())!=digest:raise ValueError('body digest')
        with open(boot.path(slot,'ota_manifest.json'),'wb') as f:f.write(raw)
        os.sync()
        release=hexed(hashlib.sha256(raw).digest())
        boot.stage(slot,release)
        return {'ok':True,'staged':release}
    except Exception:
        # No state switch occurs until the entire bundle has passed validation.
        raise

async def delayed_reset():
    await asyncio.sleep_ms(350)
    import machine
    machine.reset()

async def handle(r,w):
    global _busy,_connections
    if _connections>=2:
        w.close();return
    _connections+=1
    locked=False
    try:
        method,path,headers=await request(r)
        if 'transfer-encoding' in headers:raise ValueError('chunked not supported')
        size=int(headers.get('content-length','0'))
        if size<0 or size>protocol.MAX_BODY:raise ValueError('body size')
        if method=='GET' and path=='/ota/challenge' and size==0:
            await respond(w,200,{'nonce':challenge(),'protocol':1});return
        if method!='POST' or path not in ('/ota/upload','/ota/status','/ota/confirm','/ota/reboot','/ota/rollback','/ota/cancel'):
            await respond(w,404,{'ok':False,'error':'not found'});return
        if _busy:
            await respond(w,409,{'ok':False,'error':'busy'});return
        nonce=authenticate(path,headers)
        if nonce is None:
            await respond(w,403,{'ok':False,'error':'authentication'});return
        _busy=True;locked=True
        digest=headers['x-emo-sha256'];reset=False
        if path=='/ota/upload':result=await upload(r,size,digest)
        else:
            if size>256:raise ValueError('control body too large')
            h=hashlib.sha256();body=await exact(r,size,h,time.ticks_ms())
            if hexed(h.digest())!=digest:raise ValueError('body digest')
            if path=='/ota/confirm':boot.confirm(body.decode())
            elif path=='/ota/rollback':boot.rollback();reset=True
            elif path=='/ota/reboot':
                if not boot._state.get('pending') or boot._state.get('trial'):raise ValueError('no staged update')
                reset=True
            elif path=='/ota/cancel':
                boot.cancel()
            result={'ok':True,'status':boot.status()}
        await respond(w,200,result,nonce)
        if reset:asyncio.create_task(delayed_reset())
    except Exception as error:
        try:await respond(w,400,{'ok':False,'error':type(error).__name__})
        except Exception:pass
    finally:
        _connections-=1
        if locked:_busy=False
        w.close()
        try:await w.wait_closed()
        except Exception:pass

async def watchdog():
    while True:
        if boot._wdt and not boot._state.get('trial'):boot._wdt.feed()
        await asyncio.sleep(2)

async def start():
    global _server
    # Legacy raw-REPL hardware runners do not invoke the boot supervisor.
    if boot._state is None:return
    _server=await asyncio.start_server(handle,'0.0.0.0',8080)
    asyncio.create_task(watchdog())
