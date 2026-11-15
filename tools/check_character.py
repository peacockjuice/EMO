import sys, time, asyncio, random, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
time.ticks_add=lambda a,b:(a+b)%(1<<30)
time.ticks_diff=lambda a,b:((a-b+(1<<29))%(1<<30))-(1<<29)
import behaviour as B
from emotion_sequences import SEQUENCES
from types import SimpleNamespace
state={};sys.modules['bmo']=SimpleNamespace(S=state)
class Stop(Exception):pass
async def check():
 for key,(_,steps,end) in B.SCENES.items():
  expected=[a for a,n in steps for _ in range(n)]
  assert all(a in SEQUENCES and n>0 for a,n in steps)
  assert end in SEQUENCES
  for cancel in range(len(expected)+2):
   played=[]
   async def play(o,a):
    if len(played)==cancel:raise Stop()
    played.append(a)
   try:await B.manual(None,key,play)
   except Stop:pass
   assert played==(expected+[end,end])[:cancel]
   assert state['phase']==('hold' if cancel>=len(expected) else 'scene')
 for seed in range(40):
  c=B.Character((1<<30)-10000,random.Random(seed));now=(1<<30)-10000
  last=None;last_sleep=None;feelings=set()
  for _ in range(3600):
   old=c.feeling;k=c.next(now);feelings.add(c.feeling)
   if c.feeling!=old:assert c.feeling in B.NEXT[old]
   if k in B.SCENES:
    assert k!='scene_grumpy' and k!=last
    if k=='scene_drowsy':
     if last_sleep is not None:assert time.ticks_diff(now,last_sleep)>=300000
     last_sleep=now
    last=k
   now=time.ticks_add(now,1000)
  assert len(feelings)==4
asyncio.run(check())
print('PASS: every scene step cancellation and hold; 40 simulated hours including clock wrap, moods, cooldown and no repeat')
