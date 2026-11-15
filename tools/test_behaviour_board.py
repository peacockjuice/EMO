# Execute in a fresh board session via tools/mp.py; reset afterwards.
import asyncio, gc, hashlib, binascii, time, json
import bmo
from emotion_sequences import SEQUENCES as ALL_SEQUENCES, ALIASES
SEQUENCES = {key:value for key,value in ALL_SEQUENCES.items() if key in ("rosto08","sleep","talk_excited","look","wink")}

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
            assert (await request("/invert?value="+str(repeat)))["ok"]
            for name, seq in SEQUENCES.items():
                before = completed.get(name,0)
                answer = await request("/set?e="+name)
                assert answer["ok"] and answer["mood"] == name
                end = time.ticks_add(time.ticks_ms(),sum(ms for _,ms in seq)+1000)
                polls = 0
                interrupts = 0
                while completed.get(name,0) <= before:
                    assert time.ticks_diff(end,time.ticks_ms()) > 0, "Cycle timeout: "+name
                    state = await request("/state")
                    assert state["invert"] == bool(repeat)
                    actual = state["mood"]
                    if actual != name:
                        interrupts += 1
                        print("external selection",name,"->",actual)
                        assert interrupts <= 3, "Repeated external changes: "+name
                        await request("/set?e="+name)
                        end = time.ticks_add(time.ticks_ms(),sum(ms for _,ms in seq)+1000)
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
        await request("/invert?value=0")
        # Legacy commands and auto still drive the new renderer.
        for name in ALIASES:
            assert (await request("/set?e="+name))["ok"]
            await asyncio.sleep_ms(100)
        assert (await request("/set?e=auto"))["ok"]
        for _ in range(35):
            if (await request("/state"))["mood"] != "auto":
                print("external selection during auto test")
                await request("/set?e=auto")
            await asyncio.sleep_ms(200)
        gc.collect()
        assert gc.mem_free() > 20000
        print("final_free",gc.mem_free())
        print("completed",completed)
        print("memory_after_each_cycle",samples)
        print("PASS: updated behaviours in both inversion modes, HTTP polls, rapid switches, aliases, auto")
    finally:
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
        server.close()
        await server.wait_closed()

h=hashlib.sha256()
with open("emotions.bin","rb") as f:
    while True:
        chunk=f.read(1024)
        if not chunk:break
        h.update(chunk)
print("emotions_sha256",binascii.hexlify(h.digest()).decode())
asyncio.run(test())
