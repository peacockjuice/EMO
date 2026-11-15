from pathlib import Path
import json, base64, struct, zlib
P=Path(__file__).resolve().parents[1]
catalog=json.loads((P/"preview/catalog.json").read_text())
manifest=json.loads((P/"preview/full-manifest.json").read_text())
# Embed small 1-bit PNGs made from the actual OLED frames (no external assets).
bank=(P/"emotions.bin").read_bytes()
def thumbnail(index):
 frame=bank[index*1024:(index+1)*1024]
 assert len(frame)==1024
 rows=bytearray()
 for y in range(64):
  rows.append(0)
  for group in range(16):
   value=0
   for bit in range(8):
    x=group*8+bit
    if frame[x+y//8*128]&(1<<(y%8)):value|=1<<(7-bit)
   rows.append(value)
 def chunk(kind,data):
  return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
 png=b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",128,64,1,0,0,0,0))+chunk(b"IDAT",zlib.compress(bytes(rows)))+chunk(b"IEND",b"")
 return "data:image/png;base64,"+base64.b64encode(png).decode()
speech=[]
for key,title in (("talk_calm","Рассказывает"),("talk_fast","Болтает"),("talk_excited","Сердится и говорит"),("talk_bobo","Бобобо"),("talk_bebe","Бебебе"),("talk_baba","Бабаба"),("talk_bibi","Бибиби")):
 # Vowel frame for syllable modes, angry base pose for angry speech.
 index=manifest["sequences"][key][0 if key=="talk_excited" else 1][0]
 speech.append({"id":key,"name":title,"number":len(speech)+1,"thumb":thumbnail(index)})
( P/"preview/speech-cards.json").write_text(json.dumps(speech,ensure_ascii=False))
import sys
sys.path.insert(0,str(P))
from behaviour import SCENES
scenes=[]
for key,(title,steps,ending) in SCENES.items():
 # A representative pose, not the common neutral first frame.
 preview={"scene_curious":("look",2),"scene_greeting":("rosto02",0),"scene_shy":("rosto05",0),"scene_drowsy":("sleep",-1),"scene_wake":("rosto13",0),"scene_grumpy":("rosto07",0)}
 mode,frame=preview[key]
 index=manifest["sequences"][mode][frame][0]
 scenes.append({"id":key,"name":title,"number":len(scenes)+1,"thumb":thumbnail(index)})
(P/"preview/scene-cards.json").write_text(json.dumps(scenes,ensure_ascii=False))
html=(P/"tools/index.template.html").read_text().replace("__CATALOG__",json.dumps(catalog,ensure_ascii=False,separators=(",",":"))).replace("__SPEECH_CARDS__",json.dumps(speech,ensure_ascii=False,separators=(",",":"))).replace("__SCENE_CARDS__",json.dumps(scenes,ensure_ascii=False,separators=(",",":"))).replace("__COUNT__",str(len(catalog))).replace("__ALIASES__",json.dumps(manifest["aliases"],separators=(",",":")))
(P/"index.html").write_text(html)
print("Built web gallery:",len(catalog),"faces,",len(html.encode()),"bytes")
