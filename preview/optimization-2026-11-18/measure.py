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
if not inventory.exists():
    tracked = subprocess.check_output(['rtk', 'proxy', 'git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    excluded = {
        'ap_cfg.example.py', 'ssd1306.py', 'emotion_sequences.py',
        'sample_sequences.py', 'emo_bb_frames.py', 'bb-plugin-emo/lib/utils.ts',
        'tools/review_board.py', 'tools/selftest.py',
    }
    files = [name for name in tracked
             if Path(name).suffix in ('.py', '.ts', '.tsx')
             and not name.startswith(('backups/', 'preview/', 'bb-plugin-emo/components/',
                                      'bb-plugin-emo/tests/', 'tools/check_', 'tools/test_', 'tools/run_'))
             and name not in excluded]
    inventory.write_text(json.dumps(files, indent=2) + '\n')
files = json.loads(inventory.read_text())
rows = []
for name in files:
    data = (ROOT / name).read_bytes()
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
(HERE / (sys.argv[1] + '-metrics.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'files'}, indent=2))
