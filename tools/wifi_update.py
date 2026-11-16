"""Authenticated LAN app updates. Credentials stay in a mode-0600 local file."""
import argparse,hashlib,hmac,json,struct,time,urllib.request,urllib.error,sys,ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ota_protocol import REQUIRED,validate,MAX_MANIFEST
DEFAULT_KEY=Path.home()/'.config/emo/update.key'

class Client:
    def __init__(self,url,key):
        self.url=url.rstrip('/');self.key=key
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def call(self,path,body=b''):
        challenge=json.load(self.opener.open(self.url+'/ota/challenge',timeout=8))
        nonce=challenge['nonce'];digest=hashlib.sha256(body).hexdigest()
        signature=hmac.new(self.key,('POST\n'+path+'\n'+nonce+'\n'+digest).encode(),hashlib.sha256).hexdigest()
        request=urllib.request.Request(self.url+path,data=body,method='POST',headers={
            'Content-Type':'application/octet-stream','X-EMO-Nonce':nonce,'X-EMO-SHA256':digest,'X-EMO-Signature':signature})
        with self.opener.open(request,timeout=100 if path=='/ota/upload' else 8) as response:
            raw=response.read(8192)
            expected=hmac.new(self.key,nonce.encode()+b'\n'+raw,hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected,response.headers.get('X-EMO-Reply','')):raise ValueError('Unauthenticated response')
        return json.loads(raw)

def bundle(directory):
    names=list(REQUIRED)+sorted(p.name for p in directory.glob('emo_*.py'))
    files=[];contents=[]
    for name in names:
        data=(directory/name).read_bytes()
        if name.endswith('.py'):ast.parse(data,filename=name)
        contents.append(data);files.append({'name':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    raw=json.dumps({'format':1,'files':files},separators=(',',':')).encode()
    if len(raw)>MAX_MANIFEST:raise ValueError('Manifest too large')
    body=struct.pack('>I',len(raw))+raw+b''.join(contents)
    validate(json.loads(raw),len(body),len(raw))
    return body,hashlib.sha256(raw).hexdigest()

def await_trial(client,release):
    deadline=time.monotonic()+80;observed=None
    while time.monotonic()<deadline:
        try:
            state=client.call('/ota/status')['status']
        except (OSError,ValueError):time.sleep(1);continue
        if state['running']==release:
            if not state['trial'] and not state['pending'] and state['active']==release:return state
            if state['trial']:
                if observed is None:observed=state['frames']
                if state['boot_ms']>=10000 and state['frames']>max(1,observed):
                    result=client.call('/ota/confirm',release.encode())['status']
                    if result['active']!=release or result['trial']:raise RuntimeError('Confirmation mismatch')
                    return result
        elif state['last_result'] in ('rolled_back_unconfirmed','rejected_integrity'):
            raise RuntimeError('Device rejected the new release and kept the previous version')
        time.sleep(1)
    raise TimeoutError('No healthy confirmation; device watchdog will revert unconfirmed trial')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('status','upload','rollback','cancel','resume'))
    parser.add_argument('--url',default='http://192.168.1.43:8080')
    parser.add_argument('--key-file',type=Path,default=DEFAULT_KEY)
    parser.add_argument('--source',type=Path,default=ROOT)
    args=parser.parse_args()
    key=args.key_file.read_bytes()
    if len(key)!=32:raise ValueError('Update key must contain 32 random bytes')
    client=Client(args.url,key)
    if args.command=='status':print(json.dumps(client.call('/ota/status'),indent=2));return
    if args.command=='cancel':print(json.dumps(client.call('/ota/cancel')));return
    if args.command=='upload':
        body,release=bundle(args.source)
        state=client.call('/ota/status')['status']
        if state['trial'] or state['pending']:raise RuntimeError('Pending update: use resume or cancel')
        result=client.call('/ota/upload',body)
        if result.get('staged')!=release:raise RuntimeError('Staging identity mismatch')
        print('Authenticated and staged',release,flush=True)
        client.call('/ota/reboot')
    elif args.command=='rollback':
        result=client.call('/ota/rollback');release=result['status']['pending']
    else:
        state=client.call('/ota/status')['status'];release=state['pending']
        if not release:raise RuntimeError('No pending update')
        if not state['trial']:client.call('/ota/reboot')
    result=await_trial(client,release)
    print('Confirmed healthy release',result['active'])

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError) as error:
        print('Update not confirmed: '+str(error),file=sys.stderr)
        sys.exit(1)
