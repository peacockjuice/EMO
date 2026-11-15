# Temporary OLED review; run via tools/mp.py exec, then reset with tools/ser.py.
import gc, time, hashlib, binascii
import bmo
from machine import Pin, SoftI2C
import ssd1306
bus = SoftI2C(sda=Pin(bmo.SDA), scl=Pin(bmo.SCL), freq=400000)
address = next(a for a in bus.scan() if a in (0x3c, 0x3d))
o = ssd1306.SSD1306_I2C(128, 64, bus, addr=address)
o.rotate(not bmo.FLIP)
h = hashlib.sha256()
gc.collect()
print("free_before", gc.mem_free())
with open("review.bin", "rb") as f:
    while True:
        identifier = f.read(1)
        if not identifier: break
        n = identifier[0]
        assert 1 <= n <= 30
        h.update(identifier)
        t = time.ticks_us()
        assert f.readinto(o.buffer) == 1024
        h.update(o.buffer)
        o.show()
        print("face", n, "read_and_show_us", time.ticks_diff(time.ticks_us(), t))
        time.sleep_ms(1800)
gc.collect()
print("free_after", gc.mem_free())
print("sha256", binascii.hexlify(h.digest()).decode())
