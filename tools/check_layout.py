"""Run after build_faces.py and build_animations.py with the project venv."""
from pathlib import Path
import json
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "preview"
m = json.loads((p/"animation-manifest.json").read_text())
bank = (ROOT/"samples.bin").read_bytes()
static = (p/"faces.bin").read_bytes()
for name,n in (("sample_blink",1),("sample_talk",2),("sample_cry",12)):
    first = m["sequences"][name][0][0]
    reference = bank[first*1024:(first+1)*1024]
    assert reference == static[(n-1)*1024:n*1024]
    if name == "sample_blink":
        for index,_ in m["sequences"][name]:
            frame = bank[index*1024:(index+1)*1024]
            # Lower half contains the mouth: no movement during an eye blink.
            assert frame[512:] == reference[512:]
for name,t in json.loads((p/"layouts.json").read_text()).items():
    if t[0] > 1:
        x0,y0,x1,y1 = Image.open(p/(name+".png")).getbbox()
        assert x0 >= 10 and x1 <= 118 and y0 >= 6 and y1 <= 58, name
print("PASS: static poses, stable mouth during blink, layout margins")
