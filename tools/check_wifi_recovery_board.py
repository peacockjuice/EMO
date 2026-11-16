"""USB-driven boot recovery tests; does NOT prove Wi-Fi transport."""
import sys,os,time,json,hashlib
from pathlib import Path
import mp
from bootstrap_wifi import put
from wifi_update import ROOT
port=sys.argv[1]
results=[]
def connect():
 fd=mp.opn(port);mp.raw(fd);return fd
def reset(fd):
 mp.wr(fd,b'import machine;machine.reset()\x04');os.close(fd)
for name,code,delay,expected in [
 ('integrity',b"raise RuntimeError('probe')\n",6,'rejected_integrity'),
 ('startup_crash',b"raise RuntimeError('probe')\n",7,'rolled_back_unconfirmed'),
 ('watchdog_hang',b'while True: pass\n',68,'rolled_back_unconfirmed')]:
 fd=connect()
 state=json.loads(mp.ex(fd,"import ota_boot,json;print(json.dumps(ota_boot._state))"))
 assert state['active']=='/' and not state.get('pending'), 'Test requires original root baseline'
 manifest=json.loads(mp.ex(fd,"f=open('/ota_manifest.json');print(f.read());f.close()"))
 for item in manifest['files']:
  if item['name']=='bmo.py':item['size']=len(code);item['sha256']=hashlib.sha256(code).hexdigest()
 raw=json.dumps(manifest,separators=(',',':')).encode();test_id=hashlib.sha256(raw).hexdigest()
 copy="""import os,ota_boot
try:os.mkdir('/ota_a')
except OSError:pass
for name in %r:
 src=open('/'+name,'rb');dst=open('/ota_a/'+name,'wb')
 while True:
  chunk=src.read(1024)
  if not chunk:break
  dst.write(chunk)
 src.close();dst.close()
"""%[x['name'] for x in manifest['files'] if x['name']!='bmo.py']
 mp.ex(fd,copy)
 put(fd,'/ota_a/bmo.py',code)
 put(fd,'/ota_a/ota_manifest.json',raw)
 if name=='integrity':mp.ex(fd,"f=open('/ota_a/bmo.py','ab');f.write(b'# corrupt');f.close()")
 mp.ex(fd,"ota_boot.stage('/ota_a',%r)"%test_id)
 reset(fd);print('Started '+name,flush=True);time.sleep(delay)
 fd=connect()
 try:
  result=json.loads(mp.ex(fd,"import ota_boot,json;print(json.dumps(ota_boot.status()))"))
  assert result['last_result']==expected and result['active']==state['active_id'] and not result['pending'],result
  results.append({'name':name,'status':'passed','result':result})
  print('PASS '+name,flush=True)
 finally:reset(fd)
 time.sleep(4)
(ROOT/'preview/wifi-recovery-board.json').write_text(json.dumps({'transport':'USB-triggered; Wi-Fi transport not tested','tests':results},indent=2)+'\n')
