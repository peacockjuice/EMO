"""One-time USB install. Does not read Wi-Fi credentials or erase flash."""
import sys,os,ast,json,hashlib,secrets,subprocess,base64
from pathlib import Path
import mp
from wifi_update import ROOT,DEFAULT_KEY,bundle

def put(fd,name,data):
    temp=name+'.new'
    mp.ex(fd,"f=open(%r,'wb')"%temp)
    for i in range(0,len(data),768):
        mp.ex(fd,"import binascii;f.write(binascii.a2b_base64(%r))"%base64.b64encode(data[i:i+768]).decode())
    mp.ex(fd,'f.close()')
    result=mp.ex(fd,"import hashlib,binascii\nh=hashlib.sha256()\nf=open(%r,'rb')\nwhile True:\n c=f.read(1024)\n if not c:break\n h.update(c)\nf.close()\nprint(binascii.hexlify(h.digest()).decode())"%temp).strip()
    if result!=hashlib.sha256(data).hexdigest():raise ValueError('USB verify failed: '+name)
    mp.ex(fd,"import os;os.rename(%r,%r);os.sync()"%(temp,name))

def main():
    port=sys.argv[1]
    DEFAULT_KEY.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if not DEFAULT_KEY.exists():
        fd=os.open(DEFAULT_KEY,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(secrets.token_bytes(32))
    os.chmod(DEFAULT_KEY,0o600);key=DEFAULT_KEY.read_bytes()
    if len(key)!=32:raise ValueError('Invalid local key')
    fd=mp.opn(port)
    try:
        mp.raw(fd)
        existing=json.loads(mp.ex(fd,"import os,json;print(json.dumps(os.listdir('/')))"))
        if '.ota_state.json' in existing or '.ota_key' in existing:
            raise RuntimeError('Updater already provisioned; use Wi-Fi client or deliberate USB recovery')
        if 'ap_cfg.py' not in existing:
            # Provision only from an explicit ignored local config; never read Wi-Fi
            # credentials back from the board or recover secrets from archived code.
            private=ROOT/'ap_cfg.py'
            if not private.is_file():raise RuntimeError('Provision ap_cfg.py privately before retry; see ap_cfg.example.py')
            ast.parse(private.read_bytes(),filename='ap_cfg.py')
            put(fd,'ap_cfg.py',private.read_bytes())
        for name in ['ota_protocol.py','ota_boot.py','ota_http.py']:
            put(fd,name,(ROOT/name).read_bytes());print('Verified',name,flush=True)
        body,release=bundle(ROOT);length=int.from_bytes(body[:4],'big');raw=body[4:4+length]
        for item in json.loads(raw)['files']:
            name=item['name'];put(fd,name,(ROOT/name).read_bytes());print('Verified',name,flush=True)
        put(fd,'ota_manifest.json',raw)
        put(fd,'.ota_key',key)
        state={'active':'/','active_id':release,'previous':None,'previous_id':None,'pending':None,'pending_id':None,'trial':False,'last_result':'usb_installed'}
        put(fd,'.ota_state.json',json.dumps(state).encode())
        put(fd,'main.py',(ROOT/'main.py').read_bytes())
        print('Installed authenticated Wi-Fi updater; key stored locally with mode 0600')
    finally:
        os.close(fd)
        subprocess.run([sys.executable,str(ROOT/'tools/ser.py'),port],stdout=subprocess.DEVNULL)

if __name__=='__main__':main()
