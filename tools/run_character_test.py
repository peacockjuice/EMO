import os,sys,subprocess
from pathlib import Path
import mp
root=Path(__file__).resolve().parents[1]
try:
 fd=mp.opn(sys.argv[1])
 try:
  mp.raw(fd);mp.wr(fd,b"\x04");mp.rd(fd,4,b"raw REPL");mp.rd(fd,.3)
  code=(root/"tools/test_character_board.py").read_text()
  if len(sys.argv)>2 and sys.argv[2]=="soak":
   code=code[:code.index(" for inv in")] + code[code.index(' bmo.set_invert("0");bmo.set_mood("auto")'):]
   code=code.replace("PASS: character board scenes, inversion, cancel, 30min auto HTTP soak", "PASS: character board 30min auto HTTP soak only")
  wrapped="try:\n exec(%r)\nexcept Exception as e:\n import sys\n sys.print_exception(e)\n print('FAIL: character board')"%code
  output=mp.ex(fd,wrapped,2100)
  (root/"preview/character-board.log").write_text(output)
  print(output)
  assert "PASS: character board" in output
 finally:os.close(fd)
finally:
 subprocess.run([sys.executable,str(root/"tools/ser.py"),sys.argv[1]],stdout=subprocess.DEVNULL)
