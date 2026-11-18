"""Reproduce source/bundle metrics against a frozen file inventory; no device I/O."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from wifi_update import bundle

inventory = HERE / 'source-files.json'
files = json.loads(inventory.read_text())
rows = []
for name in files:
    file = ROOT / name
    if not file.exists() and name != 'tools/build_bb.py':
        raise FileNotFoundError(name)
    data = file.read_bytes() if file.exists() else b''
    rows.append({'file': name, 'bytes': len(data),
                 'nonempty_lines': sum(bool(line.strip()) for line in data.splitlines()),
                 'sha256': hashlib.sha256(data).hexdigest()})
body, release = bundle(ROOT)
report = {'git_head': subprocess.check_output(['rtk', 'proxy', 'git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
          'plugin_version': json.loads((ROOT / 'bb-plugin-emo/package.json').read_text())['version'],
          'inventory_sha256': hashlib.sha256(inventory.read_bytes()).hexdigest(),
          'files': rows, 'source_bytes': sum(r['bytes'] for r in rows),
          'source_nonempty_lines': sum(r['nonempty_lines'] for r in rows),
          'ota_bytes': len(body), 'ota_release': release,
          'ota_body_sha256': hashlib.sha256(body).hexdigest()}
for language, suffixes in [('python', ('.py',)), ('typescript', ('.ts', '.tsx'))]:
    subset = [r for r in rows if Path(r['file']).suffix in suffixes]
    report[language] = {'bytes': sum(r['bytes'] for r in subset),
                        'nonempty_lines': sum(r['nonempty_lines'] for r in subset)}
print(json.dumps(report, indent=2))
