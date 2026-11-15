import asyncio, bmo, gc
async def get(path):
    r, w = await asyncio.open_connection(bmo.S["ip"], 80)
    w.write(b"GET %s HTTP/1.0\r\nHost: x\r\n\r\n" % path.encode()); await w.drain()
    data = b""
    while True:
        c = await r.read(512)
        if not c: break
        data += c
    w.close(); await w.wait_closed()
    return data
async def t():
    bmo.net_up(); print("net", bmo.S["net"], bmo.S["ip"])
    await asyncio.start_server(bmo.handle, "0.0.0.0", 80)
    d = await get("/"); print("GET / ->", d[:15], len(d), "bytes, ends", d[-8:])
    for p in ("/set?e=love", "/state", "/set?e=bogus", "/nope"):
        d = await get(p); print(p, "->", d.split(b"\r\n")[0], d.split(b"\r\n\r\n")[-1])
    o = await bmo.connect()
    for name, fn in bmo.MOODS.items():
        bmo._v = bmo.S["ver"]
        await fn(o); print("mood ok:", name)
    gc.collect(); print("free ram", gc.mem_free())
asyncio.run(t())
