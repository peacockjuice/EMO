from pathlib import Path
import json,runpy,math
P=Path(__file__).resolve().parents[1];bank=(P/"emotions.bin").read_bytes();oldbank=(P/"backups/before-behaviour-update/emotions.bin").read_bytes()
seq=runpy.run_path(str(P/"emotion_sequences.py"))["SEQUENCES"];old=runpy.run_path(str(P/"backups/before-behaviour-update/emotion_sequences.py"))["SEQUENCES"]
for name,steps in old.items():
 if name in ("rosto08","sleep","talk_excited"):continue
 assert [(oldbank[i*1024:(i+1)*1024],ms) for i,ms in steps]==[(bank[i*1024:(i+1)*1024],ms) for i,ms in seq[name]],name
# Only pupil interiors may change in discontent: eyelids and mouth stay fixed.
s,tx,ty=json.loads((P/"preview/layouts.json").read_text())["Rosto-08"]
boxes=[(math.floor(x0*s+tx),math.floor(16*s+ty),math.ceil(x1*s+tx),math.ceil(19*s+ty)) for x0,x1 in ((22,42),(70,90))]
first=seq["rosto08"][0][0];ref=bank[first*1024:(first+1)*1024]
assert len({i for i,ms in seq["rosto08"]})>=4
for i,ms in seq["rosto08"]:
 data=bank[i*1024:(i+1)*1024]
 for y in range(64):
  for x in range(128):
   if any(x0<=x<x1 and y0<=y<y1 for x0,y0,x1,y1 in boxes):continue
   mask=1<<(y%8);offset=x+y//8*128
   assert (data[offset]&mask)==(ref[offset]&mask),(x,y)
# Each sleeping stage adds one Z in an otherwise empty corner.
for count,(i,ms) in enumerate(seq["sleep"]):
 data=bank[i*1024:(i+1)*1024]
 for z in range(3):
  x,y=92+10*z,12-5*z
  assert bool(data[x+y//8*128]&(1<<(y%8)))==(z<count)
catalog=json.loads((P/"preview/catalog.json").read_text())
assert [(c["id"],c["number"]) for c in catalog[-3:]]==[("look",31),("wink",32),("sleep",33)]
print("PASS: moving pupils only, progressive Zs, 33 cards, all unrelated animations unchanged")
