"""Build README artwork from the real frame bank and BB renderer. No device I/O.

Run with Pillow installed. --font selects a local TrueType font for demo captions.
Font files are not copied into the output. SVG covers use system font fallbacks.
"""
import argparse
import asyncio
import sys
import time
import types
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from emotion_sequences import SEQUENCES
from tools.preview_bb import Display
import emo_bb as state
import emo_bb_display as renderer

OUT = ROOT / 'assets/readme'
BANK = (ROOT / 'emotions.bin').read_bytes()
PAPER, INK, MUTED, ACCENT = '#f1eadf', '#252922', '#66685d', '#ad5735'


def pose(name, step=0):
    index = SEQUENCES[name][step][0]
    return Display(BANK[index * 1024:(index + 1) * 1024]).image()


def pixel_paths(im):
    # Horizontal runs keep the SVG small and preserve every original pixel.
    runs = []
    for y in range(64):
        x = 0
        while x < 128:
            if not im.getpixel((x, y)):
                x += 1
                continue
            start = x
            while x < 128 and im.getpixel((x, y)):
                x += 1
            runs.append(f'M{start} {y}h{x-start}v1h-{x-start}z')
    return ''.join(runs)


def hero(theme):
    dark = theme == 'dark'
    paper, ink, muted = ('#20251f', '#f1eadf', '#b3b6a8') if dark else (PAPER, INK, MUTED)
    accent = '#e4a37b' if dark else ACCENT
    edge = '#606858' if dark else '#ccc5b7'
    pixels = pixel_paths(pose('rosto01'))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="600" viewBox="0 0 1440 600" role="img" aria-labelledby="title desc">
<title id="title">EMO. Give your coding sessions a face.</title>
<desc id="desc">A warm editorial cover with the EMO wordmark and an exact pixel face from the OLED frame bank. Display preview, not a photograph.</desc>
<rect width="1440" height="600" fill="{paper}"/>
<g fill="{muted}" font-family="ui-monospace,monospace" font-size="18" letter-spacing="2">
<text x="64" y="64">A DESK COMPANION FOR BB</text><text x="1376" y="64" text-anchor="end">DIY / 01</text></g>
<path d="M64 90H1376M64 526H1376" stroke="{edge}"/>
<text x="52" y="364" fill="{ink}" font-family="Georgia,serif" font-size="268" letter-spacing="-17">EMO</text>
<circle cx="667" cy="350" r="11" fill="{accent}"/>
<rect x="790" y="145" width="568" height="312" rx="8" fill="#111610"/>
<g transform="translate(818 173) scale(4)" fill="#f8f7ed" shape-rendering="crispEdges"><path d="{pixels}"/></g>
<path d="M780 164v-29h29M1368 438v29h-29" fill="none" stroke="{accent}" stroke-width="2"/>
<g font-family="ui-monospace,monospace" font-size="16" fill="{muted}">
<text x="790" y="490">EXACT PIXELS. A LITTLE CHARACTER.</text>
<text x="64" y="566">WORK / QUESTIONS / REPLIES</text><text x="1376" y="566" text-anchor="end">DISPLAY PREVIEW · NOT TO SCALE</text></g>
</svg>'''


def font(path, size):
    return ImageFont.truetype(path, size)


def stage(ms):
    if ms < 2400:
        return 0, 'Work in progress.', 'Your agent is working in BB.', 'work'
    if ms < 10400:
        return 1, 'Your input is needed.', 'Reply in BB to continue.', 'question'
    return 2, 'Back to work.', 'The question is resolved in this example.', 'work'


def render_story():
    """Sample the actual renderer at 80 ms; keep the real eight-second slot."""
    clock = [0]
    samples = []
    previous_stage = [-1]
    class Changed(Exception):
        pass
    bmo = types.SimpleNamespace(S={'ver': 0, 'frames': 0}, _v=0, Changed=Changed)
    sys.modules['bmo'] = bmo
    time.ticks_ms = lambda: clock[0]
    time.ticks_diff = lambda a, b: a - b
    screen = Display(bytes(1024))
    screen.show = lambda: None

    def update():
        number, _, _, kind = stage(clock[0])
        if number == previous_stage[0]:
            return
        previous_stage[0] = number
        state._card_at = clock[0]
        state._received = clock[0]
        state._snapshot = {'source': True, 'ttl': 30, 'card': str(number),
                           'face': kind, 'counts': [1, int(kind == 'question'), 0, 0],
                           'text': '? BB#1: НУЖЕН ОТВЕТ' if kind == 'question' else 'РАБОТАЕТ'}

    async def sleep_ms(ms):
        if clock[0] % 80 == 0:
            samples.append((clock[0], bytes(screen.buffer)))
        clock[0] += ms
        update()
        if clock[0] >= 12800:
            bmo.S['ver'] += 1

    asyncio.sleep_ms = sleep_ms
    update()
    try:
        asyncio.run(renderer.run(screen))
    except Changed:
        pass
    assert len(samples) == 160 and samples[-1][0] == 12720
    return samples


def compose(ms, raw, font_path):
    number, title, caption, _ = stage(ms)
    im = Image.new('RGB', (720, 650), PAPER)
    d = ImageDraw.Draw(im)
    d.text((40, 30), 'EMO / A MOMENT AT YOUR DESK', fill=MUTED, font=font(font_path, 20))
    d.line((40, 72, 680, 72), fill='#ccc5b7')
    d.text((40, 100), title, fill=INK, font=font(font_path, 39))
    d.rounded_rectangle((88, 186, 632, 474), radius=8, fill='#111610')
    face = Display(raw).image().resize((512, 256), Image.Resampling.NEAREST).convert('RGB')
    im.paste(face, (104, 202))
    d.text((40, 510), caption, fill=INK, font=font(font_path, 24))
    for i, label in enumerate(('WORKING', 'NEEDS INPUT', 'WORKING')):
        x = 40 + i * 220
        d.line((x, 565, x + 198, 565), fill=ACCENT if i == number else '#ccc5b7', width=4)
        d.text((x, 581), label, fill=ACCENT if i == number else MUTED, font=font(font_path, 17))
    d.text((40, 623), 'STAGED EXAMPLE · ACTUAL DISPLAY RENDERER', fill=MUTED, font=font(font_path, 13))
    return im


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', help='Path to a local .ttf/.ttc file for demo captions')
    args = parser.parse_args()
    candidates = [args.font, '/System/Library/Fonts/Supplemental/Trebuchet MS.ttf',
                  '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'DejaVuSans.ttf']
    selected = None
    for candidate in filter(None, candidates):
        try:
            font(candidate, 20)
            selected = candidate
            break
        except OSError:
            pass
    if selected is None:
        parser.error('Pass --font with a local TrueType font; no font download is required.')
    OUT.mkdir(parents=True, exist_ok=True)
    for theme in ('light', 'dark'):
        (OUT / f'hero-{theme}.svg').write_text(hero(theme))
    images = [compose(ms, raw, selected) for ms, raw in render_story()]
    images[30].save(OUT / 'demo-poster.png', optimize=True)
    frames = [im.convert('P', palette=Image.Palette.ADAPTIVE, colors=32) for im in images]
    frames[0].save(OUT / 'demo.gif', save_all=True, append_images=frames[1:],
                   duration=80, loop=0, optimize=True, disposal=1)
    strip = Image.new('RGB', (1080, 270), PAPER)
    d = ImageDraw.Draw(strip)
    for i, name in enumerate(('look', 'wink', 'sleep')):
        strip.paste(pose(name, 2 if name == 'wink' else 0).resize((256, 128), Image.Resampling.NEAREST).convert('RGB'), (52 + i * 360, 36))
        d.text((52 + i * 360, 192), name.upper(), fill=INK, font=font(selected, 20))
    strip.save(OUT / 'character.png', optimize=True)
    with Image.open(OUT / 'demo.gif') as gif:
        durations = []
        for n in range(gif.n_frames):
            gif.seek(n)
            durations.append(gif.info['duration'])
        assert sum(durations) == 12800, 'GIF changed the narrative timing'
    print('Built two SVG covers, a 12.8 s renderer demo, a poster and character strip.')


if __name__ == '__main__':
    main()
