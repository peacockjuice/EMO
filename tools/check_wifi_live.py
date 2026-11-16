"""Live authenticated update regression. Stages a crashing test app, then checks automatic recovery."""
import sys,json,tempfile,shutil,urllib.request,urllib.error,urllib.parse,hashlib,hmac,time
from pathlib import Path
from wifi_update import Client,DEFAULT_KEY,ROOT,bundle,await_trial
from ota_protocol import REQUIRED
client=Client(sys.argv[1] if len(sys.argv)>1 else 'http://192.168.1.43:8080',DEFAULT_KEY.read_bytes())
results=[]
before=client.call('/ota/status')['status']
assert not before['pending'] and not before['trial']
assert before['active']==bundle(ROOT)[1], 'Deploy current source first'
try:Client(client.url,b'x'*32).call('/ota/status')
except urllib.error.HTTPError as error:assert error.code==403
else:raise AssertionError('wrong key accepted')
results.append({'name':'wrong key rejected','status':'passed'});print('PASS wrong key',flush=True)
challenge=json.load(client.opener.open(client.url+'/ota/challenge',timeout=8))
nonce=challenge['nonce'];digest=hashlib.sha256(b'').hexdigest()
signature=hmac.new(client.key,('POST\n/ota/status\n'+nonce+'\n'+digest).encode(),hashlib.sha256).hexdigest()
request=urllib.request.Request(client.url+'/ota/status',data=b'',method='POST',headers={'X-EMO-Nonce':nonce,'X-EMO-SHA256':digest,'X-EMO-Signature':signature})
with client.opener.open(request,timeout=8) as response:
 raw=response.read();assert hmac.compare_digest(response.headers['X-EMO-Reply'],hmac.new(client.key,nonce.encode()+b'\n'+raw,hashlib.sha256).hexdigest())
try:client.opener.open(request,timeout=8)
except urllib.error.HTTPError as error:assert error.code==403
else:raise AssertionError('replay accepted')
results.append({'name':'replay rejected','status':'passed'});print('PASS replay',flush=True)
with tempfile.TemporaryDirectory() as directory:
 target=Path(directory)
 for name in REQUIRED:shutil.copyfile(ROOT/name,target/name)
 (target/'bmo.py').write_text("raise RuntimeError('intentional OTA recovery probe')\n")
 body,release=bundle(target)
 assert client.call('/ota/upload',body)['staged']==release
 client.call('/ota/reboot');print('Staged crashing app over Wi-Fi',flush=True)
 try:await_trial(client,release)
 except RuntimeError:pass
 else:raise AssertionError('broken release was confirmed')
 after=client.call('/ota/status')['status']
 assert after['active']==before['active'] and not after['trial'] and not after['pending'] and after['last_result']=='rolled_back_unconfirmed'
 results.append({'name':'network upload crash rolls back to confirmed app','status':'passed'})
 print('PASS automatic rollback',flush=True)
first=after['frames'];time.sleep(3)
after=client.call('/ota/status')['status'];assert after['frames']>first
with client.opener.open('http://'+urllib.parse.urlsplit(client.url).hostname+'/',timeout=8) as r:assert r.read()==(ROOT/'index.html').read_bytes()
results.append({'name':'recovered app advances frames and serves matching panel','status':'passed'})
(ROOT/'preview/wifi-live-tests.json').write_text(json.dumps({'transport':'real LAN HTTP with HMAC','tests':results,'confirmed_release':before['active'],'final_status':after},indent=2)+'\n')
print('PASS panel and advancing frames',flush=True)
