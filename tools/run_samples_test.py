"""Run from project root: python3 tools/run_samples_test.py /dev/cu.usbserial-110."""
import os, sys, json, subprocess
from pathlib import Path
import mp
port = sys.argv[1]
root = Path(__file__).resolve().parents[1]
try:
    fd = mp.opn(port)
    try:
        mp.raw(fd)
        # Soft reset in raw REPL releases old sockets without starting main.py.
        mp.wr(fd, b"\x04")
        boot = mp.rd(fd, 4, b"raw REPL")
        if b"raw REPL" not in boot: raise RuntimeError("No REPL after soft reset")
        mp.rd(fd, .3)
        output = mp.ex(fd, (root/"tools/test_samples_board.py").read_text(), 55)
        (root/"preview/animation-board.log").write_text(output)
        expected = json.loads((root/"preview/animation-manifest.json").read_text())["sha256"]
        assert "samples_sha256 " + expected in output
        assert "PASS: cycles" in output
        print(output)
    finally:
        os.close(fd)
finally:
    result = subprocess.run([sys.executable, str(root/"tools/ser.py"), port], capture_output=True, text=True)
    (root/"preview/animation-reset.log").write_text(result.stdout + result.stderr)
    print("Reset exit:", result.returncode)
