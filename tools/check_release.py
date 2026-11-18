"""Offline release guards; no device, credentials or generated-file writes."""
import ast, asyncio, builtins, json, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]

class ReleaseTests(unittest.TestCase):
    def test_startup_fallback(self):
        tree = ast.parse((ROOT/'bmo.py').read_text())
        nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in ('set_mood', 'main')]
        for target in (None, 'emo_bb', 'emo_bb_http', 'reset_view'):
            for error in (MemoryError, RuntimeError):
                with self.subTest(target=target, error=error):
                    events = []
                    state = dict(mood='bb', ver=0, ip='', net='', scene=None, phase='idle', feeling=None, showing=None)
                    def reset():
                        events.append('reset')
                        if target == 'reset_view': raise error('injected')
                    bb = types.SimpleNamespace(reset_view=reset)
                    async def ota_start(): events.append('ota')
                    async def server(*args): events.append('panel')
                    async def animate():
                        events.append('animate')
                        self.assertEqual(len(asyncio.all_tasks()), 1)
                    original = builtins.__import__
                    def importer(name, *args, **kwargs):
                        if name == target: raise error('injected')
                        if name == 'emo_bb': events.append('bb'); return bb
                        if name == 'emo_bb_http': events.append('bb_http'); return types.SimpleNamespace()
                        if name == 'ota_http': return types.SimpleNamespace(start=ota_start)
                        return original(name, *args, **kwargs)
                    ns = dict(S=state, MOODS={'bb':None, 'auto':None}, net_up=lambda:None, handle=None, animate=animate,
                              asyncio=types.SimpleNamespace(start_server=server))
                    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'bmo.py', 'exec'), ns)
                    with patch('builtins.__import__', importer): asyncio.run(ns['main']())
                    self.assertEqual(events[0], 'ota')
                    self.assertEqual(events[-2:], ['panel', 'animate'])
                    self.assertEqual(state['mood'], 'auto' if target else 'bb')
                    self.assertEqual(state['ver'], 1)
                    if target: self.assertEqual(state['feeling'], 'calm')

    def test_measure_inventory(self):
        tree = ast.parse((ROOT/'preview/optimization-2026-11-18/measure.py').read_text())
        loop = next(n for n in tree.body if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == 'name')
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            ns = dict(ROOT=Path(folder), files=['tools/build_bb.py'], rows=[], hashlib=hashlib)
            code = compile(ast.Module(body=[loop], type_ignores=[]), 'measure.py', 'exec')
            exec(code, ns)
            self.assertEqual(ns['rows'][0]['bytes'], 0)
            ns['files'] = ['missing.py']
            with self.assertRaises(FileNotFoundError): exec(code, ns)
            (Path(folder)/'tools').mkdir()
            (Path(folder)/'tools/build_bb.py').write_bytes(b'present')
            ns['files'] = ['tools/build_bb.py']; ns['rows'] = []
            exec(code, ns)
            self.assertEqual(ns['rows'][0]['bytes'], 7)

    def test_version_labels(self):
        version = (ROOT/'VERSION').read_text().strip()
        self.assertEqual(json.loads((ROOT/'bb-plugin-emo/package.json').read_text())['version'], version+'.0')
        self.assertIn('>'+version+'</span>', (ROOT/'bb-plugin-emo/app.tsx').read_text())
        self.assertIn('EMO '+version, (ROOT/'index.html').read_text())
        for name in ('README.md', 'docs/build.md', 'docs/credits.md', 'bb-plugin-emo/README.md'):
            self.assertIn('**'+('Version ' if name == 'README.md' else '')+version+'**', (ROOT/name).read_text())
        self.assertIn('## EMO '+version, (ROOT/'bb-plugin-emo/PLUGIN_OVERVIEW.md').read_text())

if __name__ == '__main__': unittest.main()
