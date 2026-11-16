"""Stage, hash-check, then activate explicit files; always reset. Never touches Wi-Fi config."""
from pathlib import Path
import os,sys,base64,hashlib,subprocess,json
import mp
ROOT=Path(__file__).resolve().parents[1]
port=sys.argv[1];names=sys.argv[2:]
assert names and all(Path(n).name==n and n!="wifi_cfg.py" for n in names)
try:
 fd=mp.opn(port)
 try:
  mp.raw(fd)
  existing=json.loads(mp.ex(fd,"import os,json;print(json.dumps(os.listdir('/')))"))
  if '.ota_state.json' in existing or '.ota_key' in existing:
   raise RuntimeError('OTA board: partial USB upload refused. Use tools/wifi_update.py or deliberate USB recovery.')
  for name in names:
   data=(ROOT/name).read_bytes();temp=name+".new"
   mp.ex(fd,"import binascii,hashlib\nf=open(%r,'wb')"%temp)
   for offset in range(0,len(data),768):
    chunk=base64.b64encode(data[offset:offset+768]).decode()
    mp.ex(fd,"f.write(binascii.a2b_base64(%r))"%chunk)
   mp.ex(fd,"f.close()")
   digest=mp.ex(fd,"h=hashlib.sha256()\nf=open(%r,'rb')\nwhile True:\n c=f.read(1024)\n if not c: break\n h.update(c)\nf.close()\nprint(binascii.hexlify(h.digest()).decode())"%temp).strip()
   assert digest==hashlib.sha256(data).hexdigest(),name
   print("Verified",name,len(data),"bytes",flush=True)
  for name in names:mp.ex(fd,"import os;os.rename(%r,%r)"%(name+".new",name))
  print("Activated",len(names),"files",flush=True)
 finally:os.close(fd)
finally:
 r=subprocess.run([sys.executable,str(ROOT/"tools/ser.py"),port],capture_output=True,text=True)
 (ROOT/"preview/release-reset.log").write_text(r.stdout+r.stderr)
 print("Reset exit:",r.returncode,flush=True)
