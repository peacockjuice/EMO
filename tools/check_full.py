from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parents[1]
m=json.loads((P/"preview/full-manifest.json").read_text());bank=(P/"emotions.bin").read_bytes();static=(P/"preview/faces.bin").read_bytes()
assert hashlib.sha256(bank).hexdigest()==m["sha256"]
assert len(bank)==m["frames"]*1024
assert m['bytes']==len(bank), 'manifest bytes differs from the actual bank'
for n in range(1,31):
 key="rosto%02d"%n;seq=m["sequences"][key]
 assert all(0<=i<m["frames"] and ms>=80 for i,ms in seq)
 assert len(set(i for i,ms in seq))>1,key
 first=seq[0][0];assert bank[first*1024:(first+1)*1024]==static[(n-1)*1024:n*1024],key
assert all(target in m["sequences"] for target in m["aliases"].values())
catalog=json.loads((P/"preview/catalog.json").read_text());assert len(catalog)==33
assert {f["id"] for f in catalog}==({"rosto%02d"%n for n in range(1,31)}|{"look","wink","sleep"})
for file in ("bmo.py","emotions.py","emotion_sequences.py"):
 compile((P/file).read_text(),file,"exec")
print("PASS: all 30 animated, exact static starting poses, frame offsets, aliases, catalog, syntax")
