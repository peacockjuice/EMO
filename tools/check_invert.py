"""Check inversion handler without importing hardware-specific modules."""
import ast, json
from pathlib import Path
source=ast.parse((Path(__file__).resolve().parents[1]/"bmo.py").read_text())
functions=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ("state_json","set_invert")]
class Display:
 def __init__(self):self.calls=[];self.fail=False
 def invert(self,value):
  if self.fail:raise OSError("disconnected")
  self.calls.append(value)
d=Display();state={"mood":"rosto13","ver":4,"invert":False,"scene":None,"phase":"idle","feeling":None,"showing":None}
ns={"S":state,"_display":d};exec(compile(ast.Module(body=functions,type_ignores=[]),"bmo.py","exec"),ns)
for value in ("1","1","0"):
 assert ns["set_invert"](value)
 assert json.loads(ns["state_json"]())["invert"]==(value=="1")
 assert state["mood"]=="rosto13" and state["ver"]==4
assert d.calls==[True,True,False]
assert not ns["set_invert"]("invalid")
d.fail=True
try:ns["set_invert"]("1")
except OSError:pass
else:raise AssertionError("Hardware failure swallowed")
assert state["invert"] is False
ns["_display"]=None
assert ns["set_invert"]("1") and state["invert"] is True
print("PASS: native driver command, idempotence, unchanged mood, invalid input, hardware failure, deferred state")
