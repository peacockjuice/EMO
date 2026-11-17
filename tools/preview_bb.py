"""Exact pixel preview of the BB layout (no hardware required)."""
import sys,time
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from PIL import Image,ImageDraw
import emo_bb as bb
class Display:
 def __init__(self,frame):self.buffer=bytearray(frame)
 def pixel(self,x,y,c):
  if 0<=x<128 and 0<=y<64:
   index=x+y//8*128;mask=1<<(y%8)
   self.buffer[index]=(self.buffer[index]|mask) if c else (self.buffer[index]&~mask)
 def fill_rect(self,x,y,w,h,c):
  for yy in range(y,y+h):
   for xx in range(x,x+w):self.pixel(xx,yy,c)
 def scroll(self,dx,dy):
  old=self.image();self.buffer[:]=bytes(1024)
  for y in range(dy,64):
   for x in range(128):self.pixel(x,y,bool(old.getpixel((x,y-dy))))
 def image(self):
  im=Image.new('1',(128,64))
  for y in range(64):
   for x in range(128):im.putpixel((x,y),255 if self.buffer[x+y//8*128]&(1<<(y%8)) else 0)
  return im
if __name__=='__main__':
 from emotion_sequences import SEQUENCES
 time.ticks_diff=lambda a,b:a-b
 bb._card_at=0;bb._received=0
 bb._snapshot={'source':True,'ttl':30,'text':'? PDF#9: НУЖЕН ОТВЕТ','face':'question','counts':[2,1,0,1],'card':'preview'}
 bank=(P/'emotions.bin').read_bytes()
 def frame(ms):
  face,label,counts,offset=bb.view(ms)
  data=bytes(1024)
  if face:
   seq=SEQUENCES[face];elapsed=(ms if ms<1000 else ms-1000)%sum(duration for i,duration in seq)
   for i,duration in seq:
    if elapsed<duration:break
    elapsed-=duration
   data=bank[i*1024:(i+1)*1024]
  o=Display(data)
  if face:o.scroll(0,4)
  bb.overlay(o,label,counts,offset,face is None)
  return o.image().resize((512,256),Image.Resampling.NEAREST)
 result=Image.new('RGB',(528,920),'#e8ddc9');draw=ImageDraw.Draw(result)
 for n,(ms,title) in enumerate([(0,'SHOCK: 0-1s'),(1200,'BOBOBO: 1-2s'),(4200,'LARGE TEXT: 2-8s')]):
  result.paste(frame(ms),(8,n*304+20));draw.text((12,n*304+282),title,fill='#44352b')
 result.save(P/'preview/bb-layout.png')
 frames=[frame(ms) for ms in range(0,8000,125)]
 frames[0].save(P/'preview/bb-cycle.gif',save_all=True,append_images=frames[1:],duration=125,loop=0)
 print(P/'preview/bb-layout.png')
