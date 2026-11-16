"""Small shared update format. Updater modules and credentials are USB-only."""
import hashlib
REQUIRED=('bmo.py','emotions.py','behaviour.py','showcase.py','emotion_sequences.py','emotions.bin','ssd1306.py','index.html','VERSION')
MAX_BODY=384*1024
MAX_MANIFEST=8192

def allowed(name):
    if name in REQUIRED: return True
    return (isinstance(name,str) and name.startswith('emo_') and name.endswith('.py')
            and len(name)<=48 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789_.' for c in name)
            and name.count('.')==1)

def validate(manifest, body_size, header_size):
    if not isinstance(manifest,dict) or manifest.get('format')!=1: raise ValueError('format')
    files=manifest.get('files')
    if not isinstance(files,list) or not 9<=len(files)<=20: raise ValueError('file count')
    names=set();total=0
    for item in files:
        name=item.get('name');size=item.get('size');digest=item.get('sha256')
        if not allowed(name) or name in names: raise ValueError('file name')
        if type(size)!=int or not 0<size<=192*1024: raise ValueError('file size')
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest): raise ValueError('digest')
        names.add(name);total+=size
    if not set(REQUIRED).issubset(names): raise ValueError('incomplete release')
    if total+4+header_size!=body_size or body_size>MAX_BODY: raise ValueError('body size')
    return files

def mac(key,data):
    # RFC 2104 HMAC-SHA256; MicroPython has hashlib but no stdlib hmac.
    if len(key)>64:key=hashlib.sha256(key).digest()
    key=key+b'\0'*(64-len(key))
    inner=hashlib.sha256(bytes(x^0x36 for x in key)+data).digest()
    return hashlib.sha256(bytes(x^0x5c for x in key)+inner).digest()

def equal(a,b):
    if len(a)!=len(b):return False
    value=0
    for x,y in zip(a,b):value|=x^y
    return value==0
