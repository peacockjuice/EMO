# Exercise real frame player and animate reconnect path with fake hardware.
import ast,asyncio,sys,time,types
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
clock=[0]
time.ticks_ms=lambda:clock[0]
time.ticks_diff=lambda a,b:a-b
time.ticks_add=lambda a,b:a+b
async def sleep_ms(ms):clock[0]+=ms;await asyncio.sleep(0)
asyncio.sleep_ms=sleep_ms
class Changed(Exception):pass
b=types.ModuleType('bmo');b.Changed=Changed;b.S={'ver':0};b._v=0
sys.modules['bmo']=b
import emotions
class Display:
 def __init__(self):self.buffer=bytearray(1024);self.calls=0
 def show(self):self.calls+=1;b.S['ver']+=1
async def run():
 import os
 os.chdir(root)
 d=Display()
 try:await emotions.play(d,[(0,2400),(1,80)])
 except Changed:pass
 else:raise AssertionError('Cancellation lost')
 assert d.calls==1 and clock[0]<=40
 # In-flight scene fails; new mode selected during reconnect must win.
 source=ast.parse((root/'bmo.py').read_text())
 fn=next(n for n in source.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='animate')
 state={'ver':0,'mood':'old'};events=[]
 class Stop(Exception):pass
 async def connect():events.append('connect');return None
 async def splash(o):pass
 async def old(o):events.append('old');raise OSError('simulated display loss')
 async def new(o):events.append('new');raise Stop()
 async def recovery_sleep(seconds):state.update(mood='new',ver=1)
 ns={'S':state,'connect':connect,'splash':splash,'MOODS':{'old':old,'new':new},'Changed':Changed,'asyncio':types.SimpleNamespace(sleep=recovery_sleep),'print':lambda *a:None}
 exec(compile(ast.Module(body=[fn],type_ignores=[]),'animate','exec'),ns)
 try:await ns['animate']()
 except Stop:pass
 assert events==['connect','old','connect','new'],events
asyncio.run(run())
print('PASS: real frame-player cancellation within one 40ms slice; reconnect honours latest command')
