# Execute in a fresh board session via tools/mp.py; reset afterwards.
import asyncio, gc, hashlib, binascii, time, json
import bmo
from sample_sequences import SEQUENCES

async def request(path):
    r,w = await asyncio.open_connection("127.0.0.1",80)
    w.write("GET "+path+" HTTP/1.0\r\n\r\n")
    await w.drain()
    reply = await r.read()
    w.close()
    await w.wait_closed()
    assert b"200 OK" in reply
    return json.loads(reply.split(b"\r\n\r\n",1)[1])

async def test():
    bmo.net_up()
    server = await asyncio.start_server(bmo.handle,"0.0.0.0",80)
    completed = {}
    for name in SEQUENCES:
        old = bmo.MOODS[name]
        def wrap(fn, key):
            async def cycle(o):
                await fn(o)
                completed[key] = completed.get(key,0)+1
            return cycle
        bmo.MOODS[name] = wrap(old,name)
    task = asyncio.create_task(bmo.animate())
    samples = []
    try:
        await asyncio.sleep_ms(5500)
        for repeat in range(2):
            for name, seq in SEQUENCES.items():
                answer = await request("/set?e="+name)
                assert answer["ok"] and answer["mood"] == name
                end = time.ticks_add(time.ticks_ms(),sum(ms for _,ms in seq)+250)
                polls = 0
                while time.ticks_diff(end,time.ticks_ms()) > 0:
                    assert (await request("/state"))["mood"] == name
                    polls += 1
                    await asyncio.sleep_ms(120)
                gc.collect(); samples.append(gc.mem_free())
                print("cycle",repeat,name,"polls",polls,"free",samples[-1])
        for i in range(12):
            name = tuple(SEQUENCES)[i%3]
            assert (await request("/set?e="+name))["ok"]
            await asyncio.sleep_ms(80)
        assert not (await request("/set?e=invalid"))["ok"]
        assert all(completed.get(n,0)>=2 for n in SEQUENCES)
        print("completed",completed)
        print("memory_after_each_cycle",samples)
        print("PASS: cycles, HTTP polls, rapid switches, invalid mood")
    finally:
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
        server.close()
        await server.wait_closed()

h=hashlib.sha256()
with open("samples.bin","rb") as f:
    while True:
        chunk=f.read(1024)
        if not chunk:break
        h.update(chunk)
print("samples_sha256",binascii.hexlify(h.digest()).decode())
asyncio.run(test())
