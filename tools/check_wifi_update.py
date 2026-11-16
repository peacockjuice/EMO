"""Offline failure-path checks. No board, credentials or network required."""
import sys,os,asyncio,time,tempfile,json,hashlib,hmac,struct,types
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
import ota_protocol as protocol,ota_boot as boot,ota_http as service
now=[0];time.ticks_ms=lambda:now[0];time.ticks_diff=lambda a,b:a-b
asyncio.sleep_ms=lambda ms:asyncio.sleep(ms/1000)
if not hasattr(os,'sync'):os.sync=lambda:None
for key in (b'',b'x'*32,b'y'*100):
 assert protocol.mac(key,b'payload')==hmac.new(key,b'payload',hashlib.sha256).digest()
assert protocol.equal(b'abc',b'abc') and not protocol.equal(b'abc',b'abd')
secret=b'k'*32;service.key=lambda:secret
service._nonce='nonce';service._nonce_at=0
sha=hashlib.sha256(b'').hexdigest()
headers={'x-emo-nonce':'nonce','x-emo-sha256':sha,'x-emo-signature':hmac.new(secret,('POST\n/ota/status\nnonce\n'+sha).encode(),hashlib.sha256).hexdigest()}
assert service.authenticate('/ota/confirm',headers) is None
assert service.authenticate('/ota/status',dict(headers,**{'x-emo-signature':'0'*64})) is None
assert service.authenticate('/ota/status',headers)=='nonce'
assert service.authenticate('/ota/status',headers) is None
service._nonce='nonce';now[0]=31000
assert service.authenticate('/ota/status',headers) is None
now[0]=0

class Reader:
 def __init__(self,data):self.data=data
 async def read(self,n):chunk=self.data[:min(n,71)];self.data=self.data[len(chunk):];return chunk

with tempfile.TemporaryDirectory() as temp:
 root=Path(temp);boot.STATE=str(root/'state.json');boot.path=lambda slot,name:str(root/slot.strip('/')/name)
 def clear(slot):
  assert slot in ('/ota_a','/ota_b') and slot!=boot._running
  target=root/slot.strip('/');target.mkdir(exist_ok=True)
  for f in target.iterdir():f.unlink()
 service.clear_slot=clear
 contents={name:('value '+name).encode() for name in protocol.REQUIRED}
 files=[{'name':n,'size':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in contents.items()]
 raw=json.dumps({'format':1,'files':files},separators=(',',':')).encode()
 body=struct.pack('>I',len(raw))+raw+b''.join(contents.values())
 release=hashlib.sha256(raw).hexdigest()
 initial={'active':'/','active_id':release,'previous':None,'previous_id':None,'pending':None,'pending_id':None,'trial':False}
 def reset():
  boot._state=dict(initial);boot._running='/';boot.save(boot._state)
 for name,data in contents.items():(root/name).write_bytes(data)
 (root/'ota_manifest.json').write_bytes(raw)
 reset()
 for bad in ('../bmo.py','wifi_cfg.py','ap_cfg.py','main.py','ota_boot.py','.ota_key','emo_../x.py'):
  bad_files=files+[{'name':bad,'size':1,'sha256':'0'*64}]
  try:protocol.validate({'format':1,'files':bad_files},len(body)+1,len(raw))
  except ValueError:pass
  else:raise AssertionError(bad)
 async def checks():
  # Truncation and tampering leave the running slot and boot journal untouched.
  for data in (body[:-7],body[:-1]+bytes([body[-1]^1])):
   try:await service.upload(Reader(data),len(body),hashlib.sha256(body).hexdigest())
   except ValueError:pass
   else:raise AssertionError('bad payload accepted')
   assert boot.read_state()==initial
   assert (root/'bmo.py').read_bytes()==contents['bmo.py']
  result=await service.upload(Reader(body),len(body),hashlib.sha256(body).hexdigest())
  assert result['staged']==release and boot._state['active']=='/'
  assert boot.prepare()=='/ota_a' and boot._state['trial']
  # A reset before confirmation always returns to the old version.
  assert boot.prepare()=='/' and not boot._state['pending']
  assert boot._state['last_result']=='rolled_back_unconfirmed'
  boot.stage('/ota_a',release)
  # Corruption after staging is rejected at boot, before import.
  (root/'ota_a'/'bmo.py').write_bytes(b'bad')
  assert boot.prepare()=='/' and boot._state['last_result']=='rejected_integrity'
  reset();await service.upload(Reader(body),len(body),hashlib.sha256(body).hexdigest());boot.prepare()
  sys.modules['bmo']=types.SimpleNamespace(S={'frames':4});boot._started=0;now[0]=9000
  try:boot.confirm(release)
  except ValueError:pass
  else:raise AssertionError('early confirmation')
  now[0]=12000;boot.confirm(release)
  assert boot._state['active']=='/ota_a' and boot._state['previous']=='/'
  assert boot.prepare()=='/ota_a' and not boot._state['trial']
  # Failed atomic state write must not acknowledge a transition in RAM.
  before=dict(boot._state);save=boot.save
  def fail(state):raise OSError('disk full')
  boot.save=fail
  try:boot.stage('/ota_b','next')
  except OSError:pass
  else:raise AssertionError('write failure ignored')
  assert boot._state==before;boot.save=save
  boot.rollback()
  assert boot._state['pending']=='/' and boot.prepare()=='/'
  boot.confirm(release)
  assert boot._state['active']=='/' and boot._state['previous']=='/ota_a'
  (root/'ota_a'/'bmo.py').write_bytes(b'corrupt previous')
  before=dict(boot._state)
  try:boot.rollback()
  except ValueError:pass
  else:raise AssertionError('corrupt previous accepted')
  assert boot._state==before
 asyncio.run(checks())
print('PASS: HMAC, wrong key/path, replay/expiry, file allowlist, truncation/tamper, boot integrity, rollback, health gate and atomic state failure')
