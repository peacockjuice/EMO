"""USB-installed supervisor. Atomic slot selection; watchdog-backed trial boot."""
import os,json,hashlib,binascii
STATE='/.ota_state.json'
_state=None
_wdt=None
_running='/'
_started=0

def path(slot,name):return slot.rstrip('/')+'/'+name

def read_state():
    with open(STATE) as f:return json.load(f)

def save(state):
    with open(STATE+'.new','w') as f:json.dump(state,f)
    os.sync();os.rename(STATE+'.new',STATE);os.sync()

def digest_file(name):
    h=hashlib.sha256()
    with open(name,'rb') as f:
        while True:
            block=f.read(1024)
            if not block:break
            h.update(block)
    return binascii.hexlify(h.digest()).decode()

def verify(slot):
    import ota_protocol
    with open(path(slot,'ota_manifest.json'),'rb') as f:raw=f.read(ota_protocol.MAX_MANIFEST+1)
    if len(raw)>ota_protocol.MAX_MANIFEST:raise ValueError('manifest too large')
    manifest=json.loads(raw)
    total=4+len(raw)+sum(i['size'] for i in manifest['files'])
    files=ota_protocol.validate(manifest,total,len(raw))
    for item in files:
        file=path(slot,item['name'])
        if os.stat(file)[6]!=item['size'] or digest_file(file)!=item['sha256']:raise ValueError('slot integrity')
    return hashlib.sha256(raw).digest()

def prepare():
    global _state,_running
    _state=read_state()
    if _state.get('trial'):
        # Last trial never confirmed (crash, watchdog, power loss or user reset).
        _state['pending']=None;_state['pending_id']=None;_state['trial']=False
        _state['last_result']='rolled_back_unconfirmed';save(_state)
    if _state.get('pending'):
        try:
            if binascii.hexlify(verify(_state['pending'])).decode()!=_state['pending_id']:raise ValueError('manifest identity')
        except Exception:
            _state['pending']=None;_state['pending_id']=None
            _state['last_result']='rejected_integrity';save(_state)
        else:
            _state['trial']=True;_state['last_result']='trial';save(_state)
    _running=_state['pending'] if _state.get('trial') else _state['active']
    return _running

def status():
    import time,sys
    app=sys.modules.get('bmo')
    frames=app.S.get('frames',0) if app else 0
    return {'active':_state['active_id'],'running':_state.get('pending_id') if _state.get('trial') else _state['active_id'],
            'pending':_state.get('pending_id'),'trial':_state.get('trial',False),'last_result':_state.get('last_result'),
            'frames':frames,'boot_ms':time.ticks_diff(time.ticks_ms(),_started)}

def commit(state):
    global _state
    save(state)
    _state=state

def stage(slot,release):
    if _state.get('pending'):raise ValueError('pending update')
    state=dict(_state)
    state['pending']=slot;state['pending_id']=release;state['trial']=False
    state['last_result']='staged';commit(state)

def confirm(release):
    if not _state.get('trial') or release!=_state.get('pending_id'):raise ValueError('not this trial')
    health=status()
    if health['frames']<2 or health['boot_ms']<10000:raise ValueError('not healthy yet')
    state=dict(_state)
    state['previous']=state['active'];state['previous_id']=state['active_id']
    state['active']=state['pending'];state['active_id']=release
    state['pending']=None;state['pending_id']=None;state['trial']=False
    state['last_result']='confirmed';commit(state)
    if _wdt:_wdt.feed()

def cancel():
    if _state.get('trial'):raise ValueError('trial active')
    state=dict(_state)
    state['pending']=None;state['pending_id']=None;state['last_result']='cancelled';commit(state)

def rollback():
    if _state.get('pending') or not _state.get('previous'):raise ValueError('rollback unavailable')
    if binascii.hexlify(verify(_state['previous'])).decode()!=_state['previous_id']:raise ValueError('previous integrity')
    stage(_state['previous'],_state['previous_id'])

def run():
    global _wdt,_started
    import machine,time,sys
    _started=time.ticks_ms()
    _wdt=machine.WDT(timeout=60000)
    try:
        slot=prepare()
        os.chdir(slot)
        if '/' not in sys.path:sys.path.append('/')
        # Empty path means current slot; configs and immutable updater stay at root.
        if sys.path[0]!='':sys.path.insert(0,'')
        import bmo
        bmo.run()
    except Exception as error:
        print('Application startup/runtime failure:',type(error).__name__)
    time.sleep_ms(300)
    machine.reset()
