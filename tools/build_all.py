"""Build full face bank + timelines + browser metadata. Run after build_animations.py."""
from pathlib import Path
import json, hashlib, base64, runpy, io
from PIL import Image, ImageDraw
from face_layout import layout, apply_layout
P=Path(__file__).resolve().parents[1]; OUT=P/"preview"
names=["Улыбка","Радость","Грусть","Спокойствие","Смущение","На грани слёз","Злость","Недовольство","Раздражение","Хмурится","Плачет","Рыдает","Восторг","Дразнится","Робкая улыбка","Скепсис","Растерянность","Хитрая улыбка","Поцелуй","Восхищение","Влюблён","Шок","Вдохновение","Головокружение","Выключился","Пиксельная улыбка","Ужас","Счастье","Скука","Невозмутимость"]
def pack(im):
 d=bytearray(1024)
 for y in range(64):
  for x in range(128):
   if im.getpixel((x,y)):d[x+y//8*128]|=1<<(y%8)
 return bytes(d)
def raw(n):return Image.open(OUT/("Rosto-%02d-raw.png"%n)).convert("1")
def move(im,dx=0,dy=0):
 out=Image.new("1",im.size);out.paste(im,(dx,dy));return out

def squeeze(im,boxes,factor):
 out=im.copy();draw=ImageDraw.Draw(out)
 for x0,y0,x1,y1 in boxes:
  h=max(1,round((y1-y0)*factor))
  part=im.crop((x0,y0,x1,y1)).resize((x1-x0,h),Image.Resampling.NEAREST)
  draw.rectangle((x0,y0,x1-1,y1-1),fill=0)
  out.paste(part,(x0,(y0+y1-h)//2))
 return out

def pulse(im,boxes):
 # Isolate the two large connected symbols: keep nearby cheek pixels untouched.
 points={(x,y) for y in range(40) for x in range(128) if im.getpixel((x,y))}
 out=im.copy()
 while points:
  start=points.pop();group=[start];stack=[start]
  while stack:
   x,y=stack.pop()
   for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)):
    v=(x+dx,y+dy)
    if v in points:points.remove(v);stack.append(v);group.append(v)
  if len(group)<150:continue
  x0=min(x for x,y in group);y0=min(y for x,y in group)
  x1=max(x for x,y in group)+1;y1=max(y for x,y in group)+1
  part=Image.new("1",(x1-x0,y1-y0))
  for x,y in group:part.putpixel((x-x0,y-y0),255);out.putpixel((x,y),0)
  part=part.resize((part.width-2,part.height-2),Image.Resampling.NEAREST)
  out.paste(255,(x0+1,y0+1,x1-1,y1-1),part)
 return out

def blink(im,boxes):
 return [(im,2500),(squeeze(im,boxes,.5),80),(squeeze(im,boxes,.08),100),(squeeze(im,boxes,.5),80),(im,600)]
def rock(im):return [(im,1300),(move(im,1),140),(im,140),(move(im,-1),140),(im,700)]
def breathe(im):return [(im,1600),(move(im,dy=1),650),(im,900)]
def glance_pupils(im,dx):
 out=im.copy()
 for box in ((22,16,42,19),(70,16,90,19)):
  part=im.crop(box); shifted=Image.new("1",part.size)
  shifted.paste(part,(dx,0));out.paste(shifted,(box[0],box[1]))
 return out

def unpack(data):
 im=Image.new("1",(128,64))
 for y in range(64):
  for x in range(128):im.putpixel((x,y),255 if data[x+y//8*128]&(1<<(y%8)) else 0)
 return im

sample_seq=runpy.run_path(str(P/"sample_sequences.py"))["SEQUENCES"]
sample_data=(P/"samples.bin").read_bytes()
frames=[];sequences={};metadata=[]
def add(name,sequence):
 seq=[]
 for data,ms in sequence:
  if data not in frames:frames.append(data)
  seq.append((frames.index(data),ms))
 sequences[name]=seq
for n,title in enumerate(names,1):
 key="rosto%02d"%n;im=raw(n)
 if n in (1,2,12):
  sample={1:"sample_blink",2:"sample_talk",12:"sample_cry"}[n]
  add(key,[(sample_data[i*1024:(i+1)*1024],ms) for i,ms in sample_seq[sample]])
 else:
  if n in (3,5,14):seq=blink(im,[(32,19,42,30),(87,19,97,30)])
  elif n==13:seq=blink(im,[(24,10,48,34),(80,10,104,34)])
  elif n==18:seq=blink(im,[(95,17,104,29)])
  elif n in (7,9,10,17,27):seq=rock(im)
  elif n==11:
   # Move drops down within their own lanes; eyes and mouth remain fixed.
   seq=[]
   for dy in (0,2,4,6):
    f=im.copy()
    for box in ((18,30,30,62),(98,30,110,62)):
     x0,y0,x1,y1=box;part=im.crop(box);shifted=Image.new("1",part.size)
     shifted.paste(part,(0,dy));shifted.paste(part,(0,dy-part.height));f.paste(shifted,(x0,y0))
    seq.append((f,200))
  elif n in (20,21,23):
   boxes=[(21,8,52,40),(77,8,108,40)]
   seq=[(im,600),(pulse(im,boxes),220),(im,900)]
  elif n==22:seq=[(im,1800),(squeeze(im,[(24,11,49,37),(79,11,105,37)],.85),140),(im,700)]
  elif n==24:
   seq=[]
   for angle in range(0,360,45):
    f=im.copy()
    for box in ((19,10,48,39),(80,10,109,39)):
     f.paste(im.crop(box).rotate(angle,resample=Image.Resampling.NEAREST),(box[0],box[1]))
    seq.append((f,160))
  elif n==8:seq=[(glance_pupils(im,dx),ms) for dx,ms in ((0,700),(3,150),(6,150),(9,500),(6,150),(3,150),(0,150),(-2,450),(0,700))]
  elif n==16:seq=[(im,1800),(move(im,2),500),(im,800)]
  elif n==19:seq=[(im,1400),(squeeze(im,[(55,35,73,60)],.8),200),(im,700)]
  elif n in (25,29):seq=[(im,3500),(move(im,dy=1),500),(im,1200)]
  elif n==30:seq=blink(im,[(32,8,40,29),(88,8,96,29)])
  else:seq=breathe(im)
  trans=layout(im)
  add(key,[(pack(apply_layout(f,trans)),ms) for f,ms in seq])
 # Each face starts on its exact approved static pose.
 first=sequences[key][0][0]
 assert frames[first]==pack(Image.open(OUT/("Rosto-%02d.png"%n))),key
 metadata.append({"id":key,"number":n,"name":title,"thumb":"data:image/png;base64,"+base64.b64encode((OUT/("Rosto-%02d.png"%n)).read_bytes()).decode()})
# Legacy behaviours use the same visual style.
im=raw(1);trans=layout(im)
add("look",[(pack(apply_layout(move(im,dx),trans)),ms) for dx,ms in ((0,900),(-2,220),(-3,500),(0,300),(3,500),(0,600))])
add("wink",[(pack(apply_layout(f,trans)),ms) for f,ms in blink(im,[(87,19,97,29)])])
sleep=raw(4);trans=layout(sleep)
sleep_seq=[]
for count in (0,1,2,3):
 f=apply_layout(move(sleep,dy=count%2),trans)
 d=ImageDraw.Draw(f)
 for i in range(count):
  x,y=92+i*10,12-i*5
  d.line((x,y,x+4,y),fill=255)
  d.line((x+4,y,x,y+4),fill=255)
  d.line((x,y+4,x+4,y+4),fill=255)
 sleep_seq.append((pack(f),650))
add("sleep",sleep_seq)
# These behaviours now live alongside the original 30 faces.
for key,title,thumb_index in (("look","Осматривается",0),("wink","Подмигивает",2),("sleep","Спит",-1)):
 thumb=unpack(frames[sequences[key][thumb_index][0]])
 data=io.BytesIO();thumb.save(data,format="PNG")
 metadata.append({"id":key,"number":len(metadata)+1,"name":title,"thumb":"data:image/png;base64,"+base64.b64encode(data.getvalue()).decode()})
# Three speech rhythms with distinct mouth shapes; eyes and layout stay fixed.
def speech_frame(reference,shape,dy=0):
 if shape=="rest":return reference.copy()
 out=reference.copy();d=ImageDraw.Draw(out)
 d.rectangle((44,33,84,56+dy),fill=0)
 if shape=="m":d.line((57,41+dy,71,41+dy),fill=255,width=1)
 elif shape=="a":
  d.ellipse((56,34+dy,72,44+dy),outline=255,width=1)
  d.line((60,42+dy,68,42+dy),fill=255,width=1)
 elif shape=="o":d.ellipse((60,34+dy,68,44+dy),outline=255,width=1)
 elif shape=="e":d.rounded_rectangle((54,37+dy,74,43+dy),radius=2,outline=255,width=1)
 elif shape=="i":d.rounded_rectangle((54,39+dy,74,41+dy),radius=1,outline=255,width=1)
 else:raise ValueError(shape)
 return out
speech={
 "talk_calm":(1,0,[("rest",700),("e",220),("a",260),("m",120),("o",240),("rest",350),("e",220),("m",120),("a",280),("rest",1100)]),
 "talk_fast":(1,0,[("rest",180),("a",120),("m",80),("e",100),("o",100),("m",80),("a",140),("rest",120),("e",100),("m",80),("o",120),("a",120),("m",80),("rest",300)]),
 "talk_excited":(7,4,[("rest",600),("o",280),("a",360),("m",100),("e",200),("a",480),("rest",450),("o",220),("m",100),("a",400),("rest",900)]),
}
# Continuous syllable loop: lip closure (b) followed by the chosen vowel shape.
for key,vowel,hold in (("talk_bobo","o",210),("talk_bebe","e",170),("talk_baba","a",230),("talk_bibi","i",120)):
 speech[key]=(1,0,[("m",90),(vowel,hold)])
for key,(n,dy,syllables) in speech.items():
 ref=raw(n);trans=layout(ref)
 add(key,[(pack(apply_layout(speech_frame(ref,shape,dy),trans)),ms) for shape,ms in syllables])
aliases={"smile":"rosto01","happy":"rosto02","love":"rosto21","wow":"rosto13","talk":"rosto02","sad":"rosto03","sample_blink":"rosto01","sample_talk":"rosto02","sample_cry":"rosto12"}
bank=b"".join(frames);(P/"emotions.bin").write_bytes(bank)
(P/"emotion_sequences.py").write_text("# Generated by tools/build_all.py\nSEQUENCES = "+repr(sequences)+"\nALIASES = "+repr(aliases)+"\n")
(OUT/"catalog.json").write_text(json.dumps(metadata,ensure_ascii=False))
(OUT/"full-manifest.json").write_text(json.dumps({"sha256":hashlib.sha256(bank).hexdigest(),"frames":len(frames),"bytes":len(bank),"sequences":sequences,"aliases":aliases},indent=2))
# Readable animation contact sheets and GIFs for local visual QA.
for entry in metadata+[{"id":key} for key in speech]:
 key=entry["id"];seq=sequences[key];images=[]
 for idx,ms in seq:
  im=Image.new("1",(128,64));data=frames[idx]
  for y in range(64):
   for x in range(128): im.putpixel((x,y),255 if data[x+y//8*128]&(1<<(y%8)) else 0)
  images.append(im)
 images[0].resize((384,192),Image.Resampling.NEAREST).save(OUT/(key+".gif"),save_all=True,append_images=[im.resize((384,192),Image.Resampling.NEAREST) for im in images[1:]],duration=[ms for _,ms in seq],loop=0,optimize=False,disposal=2)
 strip=Image.new("RGB",(128*len(images),80),"#20252b");d=ImageDraw.Draw(strip)
 for j,(im,(_,ms)) in enumerate(zip(images,seq)):
  d.text((128*j+2,0),str(ms),fill="white");strip.paste(im.convert("RGB"),(128*j,16))
 strip.save(OUT/(key+"-frames.png"))
print("Built 33 emotion cards + 7 speech variants:",len(frames),"unique frames,",len(bank),"bytes")
