"""Build OLED review assets. Run with ../.venv/bin/python; requires Pillow, CairoSVG."""
from pathlib import Path
import io, json, xml.etree.ElementTree as ET
import cairosvg
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "preview"
OUT.mkdir(exist_ok=True)

def render(svg):
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg, output_width=1024, output_height=576))).convert("RGB")

def mono_svg(path):
    root = ET.parse(path).getroot()
    # Masks and clip paths describe coverage, not visible ink: never recolour them.
    coverage = {child for e in root.iter() if e.tag.rsplit("}", 1)[-1] in ("mask", "clipPath") for child in e.iter()}
    for e in root.iter():
        if e in coverage: continue
        fill = e.get("fill", "").lower()
        stroke = e.get("stroke", "").lower()
        e.attrib.pop("filter", None)
        if "opacity" in e.attrib: e.set("opacity", "1")
        for attr in ("fill", "stroke"):
            c = e.get(attr)
            if c is None or c == "none": continue
            dark = c.lower() in ("#c9e4c3", "#396337", "white")
            e.set(attr, "black" if dark else "white")
        if "stroke-width" in e.attrib:
            e.set("stroke-width", str(max(16, float(e.get("stroke-width")))))
        # Cheeks use three short hatches so they cannot read as extra eyes.
        if fill in ("#548b51", "#ffc8d8"):
            cx, cy = float(e.get("cx")), float(e.get("cy"))
            e.tag = "{http://www.w3.org/2000/svg}path"
            e.attrib.clear()
            e.set("d", " ".join("M %s %s l 20 -34" % (cx+dx, cy+17) for dx in (-42, -10, 22)))
            e.set("stroke", "white"); e.set("stroke-width", "14"); e.set("fill", "none")
        # Preserve the large light reflections inside outlined dark eyes.
        if path.stem == "Rosto-13" and e.get("cy") and float(e.get("cy")) < 370:
            if fill == "black":
                e.set("fill", "black"); e.set("stroke", "white"); e.set("stroke-width", "16")
            elif fill == "white": e.set("fill", "white")
        # Outline the streams; solid white columns overwhelmed the closed eyes.
        if path.stem == "Rosto-12":
            if fill == "#5ad49f":
                e.set("fill", "black"); e.set("stroke", "white"); e.set("stroke-width", "18")
            if stroke == "#8ef5c5": e.set("display", "none")
    return ET.tostring(root)

def pack(im):
    data = bytearray(1024)
    for y in range(64):
        for x in range(128):
            if im.getpixel((x, y)): data[x + (y // 8) * 128] |= 1 << (y % 8)
    return bytes(data)

REVIEW_IDS = (1, 5, 12, 13, 21, 24)
all_data = bytearray()
for i, path in enumerate(sorted((ROOT / "assets/figma").glob("*.svg"))):
    original = render(path.read_bytes())
    adapted = render(mono_svg(path)).convert("L").resize((114,64), Image.Resampling.LANCZOS)
    frame = Image.new("L", (128,64))
    frame.paste(adapted, (7,0))
    frame = frame.point(lambda v: 255 if v >= 110 else 0).convert("1")
    frame.save(OUT / (path.stem + ".png"))
    data = pack(frame)
    assert len(data) == 1024 and any(data)
    # Round trip checks the SSD1306 page layout, including bit direction.
    assert all(bool(data[x + y//8*128] & (1 << (y%8))) == bool(frame.getpixel((x,y))) for y in range(64) for x in range(128))
    all_data.extend(data)
    original.resize((256,144)).save(OUT / (path.stem + "-source.png"))
assert len(all_data) == 30*1024
(OUT / "faces.bin").write_bytes(all_data)
review = b"".join(bytes((n,)) + all_data[(n-1)*1024:n*1024] for n in REVIEW_IDS)
(OUT / "review.bin").write_bytes(review)
import hashlib
(OUT / "manifest.json").write_text(json.dumps({"review_ids": REVIEW_IDS, "review_sha256": hashlib.sha256(review).hexdigest(), "faces_sha256": hashlib.sha256(all_data).hexdigest()}, indent=2))
# Full comparison sheet.
sheet = Image.new("RGB", (1056, 10*318), "#20252b")
d = ImageDraw.Draw(sheet)
for i in range(30):
    name = "Rosto-%02d" % (i+1)
    x,y = i%3*352,i//3*318
    d.text((x+48,y+8),name + " | original / OLED",fill="white")
    sheet.paste(Image.open(OUT/(name+"-source.png")),(x+48,y+28))
    sheet.paste(Image.open(OUT/(name+".png")).resize((256,128),Image.Resampling.NEAREST).convert("RGB"),(x+48,y+180))
sheet.save(OUT/"comparison.png")
(OUT/"checks.json").write_text(json.dumps([{"name":"30 frames: dimensions, nonempty, SSD1306 round trip", "status":"passed"}]))
print("Built 30 faces, 30720 bytes. Preview:", OUT/"comparison.png")

# Large comparisons, all raster enlargement uses nearest-neighbour.
for n in (5, 12, 13):
    name = "Rosto-%02d" % n
    panel = Image.new("RGB", (816, 560), "#20252b")
    draw = ImageDraw.Draw(panel)
    draw.text((20, 10), name + " | SOURCE", fill="white")
    panel.paste(Image.open(OUT/(name+"-source.png")), (20, 30))
    draw.text((20, 200), "BEFORE", fill="white")
    draw.text((420, 200), "REFINED", fill="white")
    for x, folder in ((20, OUT/"before-refinement"), (420, OUT)):
        if not (folder/(name+".png")).exists(): continue
        panel.paste(Image.open(folder/(name+".png")).resize((384,192), Image.Resampling.NEAREST).convert("RGB"), (x, 230))
    draw.text((420, 448), "128 x 64", fill="white")
    panel.paste(Image.open(OUT/(name+".png")).convert("RGB"), (420, 475))
    panel.save(OUT/(name+"-detail.png"))
