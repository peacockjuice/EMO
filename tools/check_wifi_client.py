"""Client recovery and legacy uploader guard; no board or private credentials."""
import sys,json,tempfile,runpy,types,io,contextlib
from pathlib import Path
from unittest.mock import patch
import wifi_update as update

release='release'
def state(**changes):
 value=dict(active='old',running=release,pending=release,trial=True,last_result='trial',frames=2,boot_ms=12000)
 value.update(changes);return value
confirmed=state(active=release,pending=None,trial=False,last_result='confirmed',frames=5)
class Client:
 def __init__(self,events):self.events=list(events);self.calls=[]
 def call(self,path,body=b''):
  self.calls.append(path)
  expected,value=self.events.pop(0);assert path==expected,(path,expected)
  if isinstance(value,Exception):raise value
  return {'status':value}

with patch.object(update.time,'sleep',lambda _:None):
 client=Client([('/ota/status',state()),('/ota/status',state(frames=4)),('/ota/confirm',TimeoutError('lost reply')),('/ota/status',confirmed)])
 assert update.await_trial(client,release)==confirmed and not client.events
 # Same manifest in both slots must not hide a rejected trial.
 client=Client([('/ota/status',dict(confirmed,last_result='rolled_back_unconfirmed'))])
 try:update.await_trial(client,release)
 except RuntimeError:pass
 else:raise AssertionError('same-release rollback reported success')
 client=Client([('/ota/reboot',ConnectionResetError()),('/ota/status',state()),('/ota/status',state(frames=4)),('/ota/confirm',confirmed)])
 assert update.reboot_and_wait(client,release)==confirmed and not client.events
 with patch.object(update.time,'monotonic',side_effect=[0,81]):
  try:update.await_trial(Client([]),release)
  except TimeoutError as error:assert 'Result unknown' in str(error)
  else:raise AssertionError('timeout not raised')

with tempfile.TemporaryDirectory() as directory:
 key=Path(directory)/'test.key';key.write_bytes(b'x'*32)
 actual=update.bundle(update.ROOT)[1]
 client=Client([('/ota/status',state(active=actual,running=actual,pending=None,trial=False))])
 with patch.object(sys,'argv',['wifi_update.py','upload','--key-file',str(key)]),patch.object(update,'Client',return_value=client),contextlib.redirect_stdout(io.StringIO()):
  update.main()
 assert client.calls==['/ota/status']

# The legacy uploader must reject before its first write, and still reset.
import mp,os,subprocess
calls=[]
def execute(fd,code):
 calls.append(code);assert 'os.listdir' in code
 return json.dumps(['.ota_state.json'])
with patch.object(sys,'argv',['upload_release.py','test-port','bmo.py']),patch.object(mp,'opn',return_value=123),patch.object(mp,'raw'),patch.object(mp,'ex',side_effect=execute),patch.object(os,'close'),patch.object(subprocess,'run',return_value=types.SimpleNamespace(stdout='',stderr='',returncode=0)) as reset,patch.object(Path,'write_text'),contextlib.redirect_stdout(io.StringIO()):
 try:runpy.run_path(str(update.ROOT/'tools/upload_release.py'),run_name='__main__')
 except RuntimeError as error:assert 'partial USB upload refused' in str(error)
 else:raise AssertionError('legacy uploader bypassed OTA guard')
 assert reset.call_count==1 and len(calls)==1
print('PASS: lost confirmation/reboot replies, same-release rollback, uncertain timeout, no-op upload and legacy USB guard')
