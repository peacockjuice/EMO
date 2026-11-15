# BMO robot face: animated emotions on an SSD1306 OLED + a web page to switch them.
# Wiring: SDA -> IO8, SCL -> IO9, VDD -> 3.3V, GND -> GND
import asyncio, network, time
from machine import Pin, SoftI2C
import ssd1306

SDA, SCL = 8, 9
FLIP = True                  # display is mounted upside down in the robot: rotate image 180 degrees
from ap_cfg import AP_NAME, AP_PASS  # private board-local configuration

i2c = SoftI2C(sda=Pin(SDA), scl=Pin(SCL), freq=400000)
S = {"mood": "auto", "ver": 0, "ip": "", "net": "", "invert": False, "scene": None, "phase": "idle", "feeling": None}
_v = 0
_display = None

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
    global _display
    while True:
        try:
            a = next((x for x in i2c.scan() if x in (0x3C, 0x3D)), None)
            if a is not None:
                o = ssd1306.SSD1306_I2C(128, 64, i2c, addr=a)
                o.rotate(not FLIP)            # driver default is rotate(True)
                o.invert(S["invert"])
                _display = o
                return o
        except OSError:
            pass
        print("waiting for display")
        await asyncio.sleep(1)

async def splash(o):
    o.fill(0)
    o.text("BMO  wifi:", 0, 4)
    o.text(S["net"][:16], 0, 20)
    o.text("open in browser:", 0, 36)
    o.text(S["ip"], 0, 52)
    o.show()
    await asyncio.sleep(5)

# ---------- streamed face animations ----------
import emotions
MOODS = {}
emotions.install(MOODS)

async def animate():
    global _v, _display
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
            _display = None
            print("display lost")
            await asyncio.sleep(1)

# ---------- web ----------
def set_mood(m):
    if m in MOODS:
        S["mood"] = m
        S["ver"] += 1
        S["scene"] = m if m.startswith("scene_") else None
        S["phase"] = "scene" if S["scene"] else "idle"
        S["feeling"] = "calm" if m == "auto" else None
        return True
    return False

def state_json(ok=None):
    prefix = '"ok":%s,' % ("true" if ok else "false") if ok is not None else ""
    import json
    result = {k:S[k] for k in ("mood","invert","scene","phase","feeling")}
    if ok is not None: result["ok"] = ok
    return json.dumps(result)


def set_invert(value):
    if value not in ("0", "1"):
        return False
    enabled = value == "1"
    if _display is not None:
        _display.invert(enabled)
    S["invert"] = enabled
    return True

async def handle(r, w):
    try:
        line = await asyncio.wait_for(r.readline(), 5)
        while True:
            h = await asyncio.wait_for(r.readline(), 5)
            if not h or h == b"\r\n":
                break
        parts = line.split()
        path = parts[1].decode() if len(parts) > 1 else "/"
        if path.split("?", 1)[0] == "/invert":
            value = path.split("value=", 1)[-1].split("&", 1)[0]
            ok = set_invert(value)
            w.write("HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nCache-Control: no-store\r\n\r\n" + state_json(ok))
        elif path.startswith("/set"):
            ok = set_mood(path.split("e=")[-1].split("&")[0])
            body = state_json(ok)
            w.write("HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nCache-Control: no-store\r\n\r\n" + body)
        elif path.startswith("/state"):
            w.write('HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nCache-Control: no-store\r\n\r\n' + state_json())
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
