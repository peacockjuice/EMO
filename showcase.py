# Fast complete tour, using existing frames only. Aliases are not duplicate entries.
from emotion_sequences import SEQUENCES
from behaviour import SCENES
KEYS=tuple("rosto%02d"%i for i in range(1,31))+tuple(k for k in sorted(SEQUENCES) if not k.startswith("rosto"))+tuple(sorted(SCENES))
def timeline(key):
 if key in SCENES:
  source=[frame for mode,count in SCENES[key][1] for _ in range(count) for frame in SEQUENCES[mode]]
 else:
  source=SEQUENCES[key]
  duration=sum(t for _,t in source)
  source=source*max(1,(500+duration-1)//duration)
 # Ten 50ms samples keep even long scenes inside a 500ms preview budget.
 # Retain the endpoints; merge equal neighbours to avoid redundant I2C writes.
 total=sum(t for _,t in source);result=[]
 for sample in range(10):
  position=sample*(total-1)//9;elapsed=0
  for index,duration in source:
   elapsed+=duration
   if position<elapsed:break
  if result and result[-1][0]==index:
   result[-1]=(index,result[-1][1]+50)
  else:result.append((index,50))
 return result
async def run(o,play):
 import bmo
 bmo.S["feeling"]=None;bmo.S["scene"]=None;bmo.S["phase"]="demo"
 try:
  while True:
   for key in KEYS:
    frames=timeline(key)
    for inverted in (False,True):
     if bmo.S["ver"]!=bmo._v:raise bmo.Changed
     o.invert(inverted);bmo.S["invert"]=inverted;bmo.S["showing"]=key
     await play(o,frames)
 finally:
  # set_mood already restores desired inversion before acknowledging the command.
  if bmo.S["mood"]!="demo":o.invert(bmo.S["invert"])
