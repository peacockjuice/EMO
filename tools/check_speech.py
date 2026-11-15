"""Validate current speech geometry and rhythm."""
from pathlib import Path
import runpy,json,math
P=Path(__file__).resolve().parents[1]
bank=(P/"emotions.bin").read_bytes();static=(P/"preview/faces.bin").read_bytes()
current=runpy.run_path(str(P/"emotion_sequences.py"))["SEQUENCES"]
layouts=json.loads((P/"preview/layouts.json").read_text())
metrics={}
for name,n,dy in (("talk_calm",1,0),("talk_fast",1,0),("talk_excited",7,4)):
 seq=current[name];first=bank[seq[0][0]*1024:(seq[0][0]+1)*1024]
 assert first==static[(n-1)*1024:n*1024],name+": wrong starting pose"
 assert len({i for i,ms in seq})>=5
 assert seq[0][0]==seq[-1][0]
 scale,tx,ty=layouts["Rosto-%02d"%n]
 x0,y0=math.floor(44*scale+tx),math.floor(33*scale+ty)
 x1,y1=math.ceil(85*scale+tx),math.ceil((57+dy)*scale+ty)
 for index,ms in seq:
  assert index>=0 and 80<=ms<=1200
  data=bank[index*1024:(index+1)*1024];assert len(data)==1024
  for y in range(64):
   for x in range(128):
    if x0<=x<x1 and y0<=y<y1:continue
    offset=x+y//8*128;mask=1<<(y%8)
    assert (data[offset]&mask)==(first[offset]&mask),(name,"changed outside mouth",x,y)
 resting=seq[0][0];active=[ms for i,ms in seq if i!=resting]
 total=sum(ms for _,ms in seq);rest=sum(ms for i,ms in seq if i==resting)
 metrics[name]={"cycle_ms":total,"rest_ms":rest,"rest_fraction":rest/total,"active_mean_ms":sum(active)/len(active)}
# Speaking speed is about active poses, not the total loop including pauses.
assert metrics["talk_fast"]["active_mean_ms"]<metrics["talk_calm"]["active_mean_ms"]<metrics["talk_excited"]["active_mean_ms"]
assert metrics["talk_fast"]["rest_fraction"]<.4
assert metrics["talk_calm"]["rest_fraction"]>.5
(P/"preview/speech-metrics.json").write_text(json.dumps(metrics,indent=2))
print("PASS: source poses, all non-mouth pixels stable, active timing and pause balance")
