"""Short scene test by default. Explicit --mode soak/full enables the 30-minute soak."""
import os,sys,subprocess,json,time,argparse,urllib.request
from pathlib import Path
import mp
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument("port")
parser.add_argument("--mode",choices=("scenes","soak","full"),default="scenes")
parser.add_argument("--url",default="http://192.168.1.43")
args=parser.parse_args()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def request(path):
 return json.load(opener.open(args.url+path,timeout=5))
# Capture intent before stopping the running firmware. Never read Wi-Fi credentials.
previous=request("/state")
result={"mode":args.mode,"status":"failed"}
try:
 fd=mp.opn(args.port)
 try:
  mp.raw(fd);mp.wr(fd,b"\x04");boot=mp.rd(fd,4,b"raw REPL");mp.rd(fd,.3)
  assert b"raw REPL" in boot,"Soft reset failed"
  code="TEST_MODE=%r\n"%args.mode+(root/"tools/test_character_board.py").read_text()
  wrapped="try:\n exec(%r)\nexcept Exception as e:\n import sys\n sys.print_exception(e)\n print('FAIL: character board')"%code
  output=mp.ex(fd,wrapped,2100 if args.mode!="scenes" else 200)
  (root/("preview/character-"+args.mode+"-board.log")).write_text(output)
  print(output)
  assert "PASS: character board" in output
  result["status"]="passed"
 finally:os.close(fd)
finally:
 subprocess.run([sys.executable,str(root/"tools/ser.py"),args.port],stdout=subprocess.DEVNULL)
 # A manual scene restarts; its exact prior frame cannot be resumed after reset.
 restored=False
 for _ in range(20):
  try:
   request("/set?e="+previous["mood"])
   request("/invert?value="+("1" if previous["invert"] else "0"))
   restored=True;break
  except Exception:time.sleep(1)
 result["restored_previous_mode_and_invert"]=restored
 (root/("preview/character-"+args.mode+"-result.json")).write_text(json.dumps(result,indent=2)+"\n")
 if not restored:print("WARNING: could not restore prior mode/inversion")
