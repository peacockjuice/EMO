"""Build scene GIFs from the existing bank; run with the project Pillow venv."""
from pathlib import Path
import sys,json
from PIL import Image
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from behaviour import SCENES
from emotion_sequences import SEQUENCES
bank=(P/"emotions.bin").read_bytes();report=[]
for key,(title,steps,end) in SCENES.items():
 frames=[];durations=[];poses=[]
 for mode,count in steps:
  for _ in range(count):
   for index,duration in SEQUENCES[mode]:
    data=bank[index*1024:(index+1)*1024];im=Image.new("RGB",(128,64))
    im.putdata([(255,255,255) if data[x+(y//8)*128]&(1<<(y%8)) else (0,0,0) for y in range(64) for x in range(128)])
    frames.append(im.resize((384,192),Image.Resampling.NEAREST));durations.append(duration)
  poses.append(frames[-1])
 frames[0].save(P/"preview"/(key+".gif"),save_all=True,append_images=frames[1:],duration=durations,loop=0)
 strip=Image.new("RGB",(384*len(poses),212),"#f2e8da")
 for i,im in enumerate(poses):strip.paste(im,(384*i,0))
 strip.save(P/"preview"/(key+"-strip.png"))
 report.append({"scene":key,"duration_ms":sum(durations),"ending":end})
(P/"preview/scenes-manifest.json").write_text(json.dumps(report,indent=2)+"\n")
print("Built",len(report),"scene previews; GIF loops are preview-only, manual scenes play once")
