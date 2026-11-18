"""Measure BB import memory via USB; always reset back to the normal app."""
import argparse,json,os,subprocess,sys
from pathlib import Path
import mp
ROOT=Path(__file__).resolve().parents[1]
CODE="""import gc,esp32,network,json,sys,ota_boot

def probe(label):
 gc.collect()
 print(json.dumps({'stage':label,'heap_free':gc.mem_free(),'heap_alloc':gc.mem_alloc(),'native':esp32.idf_heap_info(esp32.HEAP_DATA),'connected':network.WLAN(network.STA_IF).isconnected(),'wifi_status':network.WLAN(network.STA_IF).status()}))
print(json.dumps({'release':ota_boot.status()['running']}))
probe('before_import')
for name in ('emo_bb','emo_bb_http','emo_bb_view','emo_font','emo_bb_display'):
 __import__(name)
 probe(name)
"""
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('port');p.add_argument('--report',type=Path,default=ROOT/'preview/bb-memory-after.json');args=p.parse_args()
 fd=mp.opn(args.port)
 try:
  mp.raw(fd);out=mp.ex(fd,CODE,t=20)
  rows=[json.loads(line) for line in out.splitlines() if line.startswith('{')]
  args.report.write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2),flush=True)
 finally:
  os.close(fd)
  subprocess.run([sys.executable,str(ROOT/'tools/ser.py'),args.port],stdout=subprocess.DEVNULL,check=True)
