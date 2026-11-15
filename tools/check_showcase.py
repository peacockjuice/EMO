import sys,ast,asyncio,types
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
import showcase
from emotion_sequences import SEQUENCES
from behaviour import SCENES
assert len(showcase.KEYS)==46 and len(set(showcase.KEYS))==46
assert set(showcase.KEYS)==set(SEQUENCES)|set(SCENES)
for key in showcase.KEYS:
 frames=showcase.timeline(key)
 assert sum(d for _,d in frames)==500,key
 assert len(frames)<=10 and all(d>=50 for _,d in frames),key
class Changed(Exception):pass
class Display:
 def __init__(self):self.inverted=None
 def invert(self,v):self.inverted=v
source=ast.parse((P/'bmo.py').read_text())
ns={'S':{'mood':'auto','invert':True,'ver':0,'demo_restore':False},'MOODS':dict.fromkeys(['auto','demo','rosto01'])}
fn=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='set_mood')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'set_mood','exec'),ns)
b=types.SimpleNamespace(S=ns['S'],Changed=Changed,_v=0);sys.modules['bmo']=b
async def run():
 for cancel in (0,1,46,91,92,94):
  ns['set_mood']('auto');b.S['invert']=True
  ns['set_mood']('demo');b._v=b.S['ver'];display=Display();seen=[]
  async def play(o,frames):
   assert frames and all(0<=i<104 and d>=40 for i,d in frames)
   seen.append((b.S['showing'],b.S['invert']))
   if len(seen)>cancel:
    ns['set_mood']('rosto01');raise Changed()
  try:await showcase.run(display,play)
  except Changed:pass
  expected=[(key,inv) for key in showcase.KEYS for inv in (False,True)]*2
  assert seen==expected[:cancel+1]
  assert display.inverted is True and b.S['invert'] is True and b.S['showing'] is None
asyncio.run(run())
print('PASS: 46 variants, both polarities, wraparound, cancellation and original inversion restored')
