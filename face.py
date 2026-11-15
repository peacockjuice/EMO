# Kawaii BMO face filling a 128x64 mono display. draw(fb, ...) works on any FrameBuffer.
from array import array

LX, RX, EY = 30, 98, 21      # eye centres
MX, MY = 64, 40              # mouth anchor (top of the mouth)

def _eye(fb, x, y, kind):
    if kind == "open":
        fb.ellipse(x, y, 9, 13, 1, True)
        fb.ellipse(x - 3, y - 6, 3, 3, 0, True)   # sparkle
        fb.fill_rect(x + 3, y + 6, 2, 2, 0)
    elif kind == "closed":
        fb.fill_rect(x - 11, y, 23, 3, 1)
    elif kind == "happy":                         # ^ ^
        for t in range(4):
            fb.ellipse(x, y + 6 + t, 12, 12, 1, False, 0b0011)
    elif kind == "wide":
        fb.ellipse(x, y, 12, 15, 1, True)
        fb.ellipse(x - 4, y - 7, 4, 4, 0, True)
        fb.fill_rect(x + 4, y + 6, 3, 3, 0)

    elif kind == "heart":
        fb.ellipse(x - 5, y - 4, 6, 6, 1, True)
        fb.ellipse(x + 5, y - 4, 6, 6, 1, True)
        fb.poly(x, y, array("h", (-11, -1, 11, -1, 0, 12)), 1, True)

def _mouth(fb, x, y, kind):
    if kind == "smile":
        for t in range(3):
            fb.ellipse(x, y + t, 20, 12, 1, False, 0b1100)
    elif kind == "small":
        for t in range(3):
            fb.ellipse(x, y + 3 + t, 9, 5, 1, False, 0b1100)
    elif kind == "open":                          # big happy mouth with tongue
        fb.ellipse(x, y, 22, 19, 1, True, 0b1100)
        fb.fill_rect(x - 22, y - 2, 45, 3, 1)
        fb.ellipse(x, y + 13, 10, 4, 0, True)
    elif kind == "frown":
        for t in range(3):
            fb.ellipse(x, y + 12 + t, 16, 9, 1, False, 0b0011)
    elif kind == "o":
        fb.ellipse(x, y + 8, 7, 9, 1, True)
        fb.ellipse(x, y + 8, 4, 6, 0, True)
    elif kind == "talk":
        fb.ellipse(x, y + 6, 14, 8, 1, True)
        fb.ellipse(x, y + 6, 11, 5, 0, True)

def _blush(fb, x, y):
    for i in range(3):
        for t in (0, 1):
            fb.line(x + i * 6 + t, y + 5, x + i * 6 + 4 + t, y, 1)

def draw(fb, le="open", re="open", mouth="smile", dx=0, dy=0, blush=False, zzz=0):
    fb.fill(0)
    _eye(fb, LX + dx, EY + dy, le)
    _eye(fb, RX + dx, EY + dy, re)
    _mouth(fb, MX + dx // 2, MY + dy, mouth)
    if blush:
        _blush(fb, 2, EY + 17 + dy)
        _blush(fb, 110, EY + 17 + dy)
    for i in range(zzz):                          # sleeping: z z z rising to the right
        fb.text("z", 104 + i * 8, 11 - i * 5, 1)
