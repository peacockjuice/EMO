"""Authenticated BB snapshots and one OLED compositor. No persistent packet writes."""
import time, os, binascii
from ota_protocol import mac

PURPOSE=b'emo.bb.notifications.v1'
_boot=binascii.hexlify(os.urandom(16)).decode()
_nonce=None
_nonce_at=0
_epoch=0
_seq=0
_snapshot=None
_received=0
_card_at=0
_key=None
FACES={'question':'rosto17','error':'rosto03','done':'wink','work':'look','wait':'rosto04','idle':'rosto04'}

def hexed(data): return binascii.hexlify(data).decode()
def key():
    global _key
    if _key is None:
        with open('/.ota_key','rb') as f: root=f.read(33)
        if len(root)!=32: raise ValueError('key configuration')
        _key=mac(root,PURPOSE)
    return _key

def reset_view():
    global _snapshot
    _snapshot=None

def status(now=None):
    if now is None: now=time.ticks_ms()
    if _snapshot is None:return 'waiting'
    if time.ticks_diff(now,_received)>_snapshot['ttl']*1000:return 'offline'
    return 'live' if _snapshot['source'] else 'unknown'

def challenge():
    global _nonce,_nonce_at
    now=time.ticks_ms()
    if _nonce is None or time.ticks_diff(now,_nonce_at)>5000:
        _nonce=hexed(os.urandom(16));_nonce_at=now
    return {'boot':_boot,'nonce':_nonce}

def validate(value):
    if not isinstance(value,dict) or set(value)!=set(('boot','epoch','seq','ttl','source','card','face','text','counts')):raise ValueError('fields')
    if value['boot']!=_boot:raise ValueError('boot')
    for name in ('epoch','seq'):
        if type(value[name])!=int or not 0<value[name]<9007199254740991:raise ValueError(name)
    if type(value['ttl'])!=int or not 10<=value['ttl']<=30:raise ValueError('ttl')
    if type(value['source'])!=bool:raise ValueError('source')
    for field,limit in (('card',96),('text',64)):
        if not isinstance(value[field],str) or not 0<len(value[field])<=limit:raise ValueError(field)
    if value['face'] not in FACES:raise ValueError('face')
    counts=value['counts']
    if not isinstance(counts,list) or len(counts)!=4 or any(type(n)!=int or not 0<=n<=99999 for n in counts):raise ValueError('counts')
    if any(ord(c)<32 for c in value['text']):raise ValueError('text')
    return value

def accept(value,expected_version):
    global _epoch,_seq,_snapshot,_received,_card_at
    import bmo
    value=validate(value)
    if value['epoch']<_epoch or (value['epoch']==_epoch and value['seq']<=_seq):raise ValueError('stale')
    _epoch,_seq=value['epoch'],value['seq']
    if bmo.S['mood']!='bb' or bmo.S['ver']!=expected_version:return 'mode_disabled'
    now=time.ticks_ms()
    if (_snapshot is None or status(now)!='live' or
        any(_snapshot[k]!=value[k] for k in ('card','face','text','source'))):_card_at=now
    _snapshot=value;_received=now
    return status(now)

# Keep each compilation unit small: ESP32-S2 shares RAM with Wi-Fi.
async def handle(*args):
    import gc
    gc.collect()
    import emo_bb_http
    gc.collect()
    await emo_bb_http.handle(*args)

async def run(o):
    import gc
    gc.collect()
    import emo_bb_view
    gc.collect()
    import emo_font
    gc.collect()
    import emo_bb_display
    gc.collect()
    await emo_bb_display.run(o)

def view(now):
    import emo_bb_display
    return emo_bb_display.view(now)

def overlay(*args):
    import emo_bb_display
    return emo_bb_display.overlay(*args)
