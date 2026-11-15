from pathlib import Path
import runpy
P=Path(__file__).resolve().parents[1];bank=(P/"emotions.bin").read_bytes()
seq=runpy.run_path(str(P/"emotion_sequences.py"))["SEQUENCES"]
old=(P/"backups/before-syllables/emotions.bin").read_bytes();oldseq=runpy.run_path(str(P/"backups/before-syllables/emotion_sequences.py"))["SEQUENCES"]
assert bank[:len(old)]==old
assert all(seq[key]==value for key,value in oldseq.items())
vowels=set()
for key in ("talk_bobo","talk_bebe","talk_baba","talk_bibi"):
 steps=seq[key];assert len(steps)==2
 assert steps[0][0]!=steps[1][0]
 assert steps[0][1]==90
 assert 120<=steps[1][1]<=230
 vowels.add(steps[1][0])
 ref=bank[steps[0][0]*1024:(steps[0][0]+1)*1024]
 for i,ms in steps:
  assert 80<=ms<=500
  frame=bank[i*1024:(i+1)*1024];assert len(frame)==1024
  for y in range(64):
   for x in range(128):
    if 30<=x<100 and 33<=y<60:continue
    offset=x+y//8*128;mask=1<<(y%8)
    assert (frame[offset]&mask)==(ref[offset]&mask),(key,x,y)
assert len(vowels)==4
print("PASS: four distinct vowels, continuous two-pose loops without rest frames, lip closure, stable non-mouth pixels, old animations unchanged")
