# One executor, existing frame bank; no extra display task.
import random, time
SCENES = {
 "scene_curious": ("Что там?", (("look",1),("rosto13",1),("rosto01",1)), "rosto01"),
 "scene_greeting": ("Рад тебя видеть", (("rosto02",1),("wink",1),("rosto01",1)), "rosto01"),
 "scene_shy": ("Смущается", (("rosto13",1),("rosto05",1),("rosto15",1)), "rosto15"),
 "scene_drowsy": ("Клюёт носом", (("rosto04",1),("sleep",2)), "sleep"),
 "scene_wake": ("Просыпается", (("sleep",1),("rosto13",1),("rosto02",1)), "rosto01"),
 "scene_grumpy": ("Возмущён!", (("rosto08",1),("talk_excited",1),("rosto08",1)), "rosto08")}
TITLES = {"calm":"Спокойствие", "curious":"Интерес", "joy":"Радость", "sleepy":"Сонливость"}
NEXT = {"calm":("curious","sleepy"), "curious":("joy",), "joy":("calm",), "sleepy":("calm",)}
CHOICES = {"calm":("scene_shy",), "curious":("scene_curious","scene_shy"), "joy":("scene_greeting",), "sleepy":("scene_drowsy",)}
BASE = {"calm":"rosto01", "curious":"rosto01", "joy":"rosto02", "sleepy":"rosto04"}
class Character:
 def __init__(self, now, rng=random):
  self.rng=rng; self.feeling="calm"; self.last=None; self.reaction=None
  self.until=time.ticks_add(now,rng.randint(120000,240000))
  self.due=time.ticks_add(now,rng.randint(20000,40000))
  self.sleep_due=time.ticks_add(now,300000)
 def next(self,now):
  wake=False
  if time.ticks_diff(now,self.until)>=0:
   old=self.feeling
   options=NEXT[old]
   if old=="calm" and time.ticks_diff(now,self.sleep_due)<0: options=("curious",)
   self.feeling=self.rng.choice(options); wake=old=="sleepy"
   self.until=time.ticks_add(now,self.rng.randint(120000,240000))
  if wake:
   self.last="scene_wake"; self.due=time.ticks_add(now,60000)
   return self.last
  if time.ticks_diff(now,self.due)>=0:
   options=[s for s in CHOICES[self.feeling] if s!=self.last and (s!="scene_drowsy" or time.ticks_diff(now,self.sleep_due)>=0)]
   self.due=time.ticks_add(now,self.rng.randint(30000,90000))
   if options:
    self.last=self.rng.choice(options)
    if self.last=="scene_drowsy":self.sleep_due=time.ticks_add(now,300000)
    return self.last
  # Small reactions are sparse and never repeated consecutively.
  reaction="look" if self.feeling=="curious" else "wink" if self.feeling=="joy" else BASE[self.feeling]
  if reaction!=BASE[self.feeling] and reaction!=self.reaction and self.rng.randint(1,5)==1:
   self.reaction=reaction; return reaction
  self.reaction=BASE[self.feeling]; return self.reaction

async def scene(o,key,play):
 import bmo
 bmo.S["scene"]=key; bmo.S["phase"]="scene"
 for animation,repeats in SCENES[key][1]:
  for _ in range(repeats): await play(o,animation)

async def manual(o,key,play):
 import bmo
 bmo.S["feeling"]=None
 await scene(o,key,play)
 bmo.S["phase"]="hold"
 while True: await play(o,SCENES[key][2])

async def automatic(o,play):
 import bmo
 character=Character(time.ticks_ms())
 while True:
  key=character.next(time.ticks_ms())
  bmo.S["feeling"]=character.feeling
  if key in SCENES:
   await scene(o,key,play)
   # Quiet interval starts after the scene, not before it.
   character.due=time.ticks_add(time.ticks_ms(),character.rng.randint(30000,90000))
  else:
   bmo.S["scene"]=None; bmo.S["phase"]="idle"
   await play(o,key)
