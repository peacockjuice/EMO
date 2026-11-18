"""Frozen visual contract, independent of HEAD and of the current generator."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def check():
    from emotion_sequences import SEQUENCES, ALIASES
    from behaviour import SCENES
    import showcase
    expected = json.loads((ROOT / 'tools/fixtures/active-frames.json').read_text())
    actual = {'sequences': SEQUENCES, 'aliases': ALIASES, 'scenes': SCENES}
    # JSON normalizes tuples/lists while preserving every index and duration.
    assert json.loads(json.dumps(actual)) == {k: expected[k] for k in actual}
    bank = (ROOT / 'emotions.bin').read_bytes()
    assert len(bank) % 1024 == 0
    for index, digest in enumerate(expected['frame_sha256']):
        frame = bank[index * 1024:(index + 1) * 1024]
        assert len(frame) == 1024 and hashlib.sha256(frame).hexdigest() == digest, index
    demo = {'keys': showcase.KEYS, 'timelines': {k: showcase.timeline(k) for k in showcase.KEYS}}
    assert hashlib.sha256(json.dumps(demo, sort_keys=True).encode()).hexdigest() == expected['showcase_sha256']

if __name__ == '__main__':
    check()
    print('PASS frozen 104 frames, 40 animations, six scenes, aliases and demo timings')
