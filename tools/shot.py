import face, framebuf, binascii
frames=[dict(), dict(spread=12), dict(le="closed",re="closed",spread=12)]
for kw in frames:
    b=bytearray(128*64//8); fb=framebuf.FrameBuffer(b,128,64,framebuf.MONO_HLSB)
    face.draw(fb,**kw); print(binascii.hexlify(b).decode())
