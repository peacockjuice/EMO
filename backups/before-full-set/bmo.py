# BMO robot face: animated emotions on an SSD1306 OLED + a web page to switch them.
# Wiring: SDA -> IO8, SCL -> IO9, VDD -> 3.3V, GND -> GND
import asyncio, random, network, time
from machine import Pin, SoftI2C
import ssd1306, face

SDA, SCL = 8, 9
FLIP = True                  # display is mounted upside down in the robot: rotate image 180 degrees
from ap_cfg import AP_NAME, AP_PASS  # private board-local configuration

i2c = SoftI2C(sda=Pin(SDA), scl=Pin(SCL), freq=400000)
S = {"mood": "auto", "ver": 0, "ip": "", "net": ""}
_v = 0

class Changed(Exception):
    pass

# ---------- network ----------
def net_up():
    try:
        network.hostname("bmo")
    except Exception:
        pass
    try:
        import wifi_cfg                       # optional file: SSID = "...", PASSWORD = "..."
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        sta.connect(wifi_cfg.SSID, wifi_cfg.PASSWORD)
        t = time.ticks_ms()
        while not sta.isconnected() and time.ticks_diff(time.ticks_ms(), t) < 15000:
            time.sleep_ms(200)
        if sta.isconnected():
            S["ip"], S["net"] = sta.ifconfig()[0], wifi_cfg.SSID
            return
        sta.active(False)
        print("home wifi failed, starting own network")
    except ImportError:
        pass
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_NAME, password=AP_PASS, authmode=3)
    S["ip"], S["net"] = ap.ifconfig()[0], AP_NAME

# ---------- display ----------
async def connect():
    while True:
        try:
            a = next((x for x in i2c.scan() if x in (0x3C, 0x3D)), None)
            if a is not None:
                o = ssd1306.SSD1306_I2C(128, 64, i2c, addr=a)
                o.rotate(not FLIP)            # driver default is rotate(True)
                return o
        except OSError:
            pass
        print("waiting for display")
        await asyncio.sleep(1)

async def show(o, ms, **kw):
    face.draw(o, **kw)
    o.show()
    while ms > 0:
        await asyncio.sleep_ms(min(40, ms))
        ms -= 40
        if S["ver"] != _v:
            raise Changed

async def splash(o):
    o.fill(0)
    o.text("BMO  wifi:", 0, 4)
    o.text(S["net"][:16], 0, 20)
    o.text("open in browser:", 0, 36)
    o.text(S["ip"], 0, 52)
    o.show()
    await asyncio.sleep(5)

# ---------- emotions: each function plays one short cycle ----------
async def blink(o, **kw):
    await show(o, 90, le="closed", re="closed", **kw)

async def smile(o):
    await show(o, random.randint(1200, 3200))
    await blink(o)

async def look(o):
    for dx in (-5, -10, -10, -5, 0, 5, 10, 10, 5, 0):
        await show(o, 110, dx=dx, mouth="small")

async def happy(o):
    for i in range(6):
        await show(o, 160, le="happy", re="happy", mouth="open", blush=True, dy=-2 if i % 2 else 2)

async def talk(o):
    for i in range(8):
        await show(o, 130, mouth="talk" if i % 2 else "small")

async def wink(o):
    await show(o, 600, re="closed", blush=True)
    await show(o, 900, blush=True)

async def wow(o):
    await show(o, 1500, le="wide", re="wide", mouth="o")
    await blink(o, mouth="o")

async def sad(o):
    await show(o, 2200, mouth="frown", dy=2)
    await show(o, 180, le="closed", re="closed", mouth="frown", dy=2)

async def love(o):
    for dy in (0, -2):
        await show(o, 350, le="heart", re="heart", blush=True, dy=dy)

async def sleep(o):
    for z in (0, 1, 2, 3):
        await show(o, 600, le="closed", re="closed", mouth="small", zzz=z)

async def auto(o):
    for _ in range(random.randint(1, 3)):
        await smile(o)
    await random.choice((look, happy, talk, wink, wow))(o)

MOODS = {"auto": auto, "smile": smile, "happy": happy, "love": love, "wow": wow, "wink": wink,
         "talk": talk, "look": look, "sad": sad, "sleep": sleep}

import samples
samples.install(MOODS)

async def animate():
    global _v
    first = True
    while True:
        try:
            oled = await connect()
            if first:
                await splash(oled)
                first = False
            while True:
                _v = S["ver"]
                try:
                    await MOODS[S["mood"]](oled)
                except Changed:
                    pass
        except OSError:                       # display contact lost: reconnect
            print("display lost")
            await asyncio.sleep(1)

# ---------- web ----------
def set_mood(m):
    if m in MOODS:
        S["mood"] = m
        S["ver"] += 1
        return True
    return False

async def handle(r, w):
    try:
        line = await asyncio.wait_for(r.readline(), 5)
        while True:
            h = await asyncio.wait_for(r.readline(), 5)
            if not h or h == b"\r\n":
                break
        parts = line.split()
        path = parts[1].decode() if len(parts) > 1 else "/"
        if path.startswith("/set"):
            ok = set_mood(path.split("e=")[-1].split("&")[0])
            body = '{"ok":%s,"mood":"%s"}' % ("true" if ok else "false", S["mood"])
            w.write("HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nCache-Control: no-store\r\n\r\n" + body)
        elif path.startswith("/state"):
            w.write('HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nCache-Control: no-store\r\n\r\n{"mood":"%s"}' % S["mood"])
        elif path == "/" or path.startswith("/?"):
            w.write("HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n")
            with open("index.html", "rb") as f:
                while True:
                    chunk = f.read(512)
                    if not chunk:
                        break
                    w.write(chunk)
                    await w.drain()
        else:
            w.write("HTTP/1.0 404 Not Found\r\n\r\n")
        await w.drain()
    except Exception as e:
        print("http error:", e)
    finally:
        w.close()
        await w.wait_closed()

async def main():
    net_up()
    print("web page: http://%s/  (wifi: %s)" % (S["ip"], S["net"]))
    await asyncio.start_server(handle, "0.0.0.0", 80)
    await animate()

def run():
    asyncio.run(main())
