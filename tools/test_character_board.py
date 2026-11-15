import asyncio,time,gc,hashlib
import bmo,behaviour,emotions
from emotion_sequences import SEQUENCES
async def check():
 bmo.net_up()
 server=await asyncio.start_server(bmo.handle,"0.0.0.0",80)
 task=asyncio.create_task(bmo.animate())
 await asyncio.sleep(7)
 if TEST_MODE != "soak":
  await check_scenes()
 if TEST_MODE == "scenes":
  task.cancel();server.close();await server.wait_closed()
  print("PASS: character board scenes and cancellation")
  return
 await check_soak()
 task.cancel();server.close();await server.wait_closed()
 print("PASS: character board " + TEST_MODE)

async def check_scenes():
 # Record actual frame buffers handed to the driver, not just phase transitions.
 hashes=[]
 with open("emotions.bin","rb") as bank:
  while True:
   frame=bank.read(1024)
   if not frame:break
   hashes.append(hashlib.sha256(frame).digest())
 display=bmo._display;original_show=display.show;seen=[]
 def record_show():
  seen.append(hashlib.sha256(display.buffer).digest())
  original_show()
 display.show=record_show
 for inv in (False,True):
  bmo.set_invert("1" if inv else "0")
  for key in behaviour.SCENES:
   seen.clear()
   expected=[hashes[index] for mode,count in behaviour.SCENES[key][1] for _ in range(count) for index,duration in SEQUENCES[mode]]
   bmo.set_mood(key)
   deadline=time.ticks_add(time.ticks_ms(),20000)
   while bmo.S["phase"]!="hold":
    assert time.ticks_diff(deadline,time.ticks_ms())>0,key
    await asyncio.sleep_ms(40)
   assert bmo.S["mood"]==key and bmo.S["invert"]==inv
   assert seen[:len(expected)]==expected,(key,"frame sequence mismatch")
   print("scene_complete",key,inv)
   bmo.set_mood("rosto01")
   await asyncio.sleep_ms(180)
   assert bmo.S["scene"] is None
 display.show=original_show
 # Measure cancellation by watching the first show after a mode command.
 display=bmo._display;original=display.show;shown=[]
 def show():
  shown.append(time.ticks_ms())
  original()
 display.show=show
 bmo.set_mood("scene_grumpy");await asyncio.sleep_ms(120)
 shown.clear();start=time.ticks_ms();bmo.set_mood("rosto01")
 await asyncio.sleep_ms(180)
 assert shown and time.ticks_diff(shown[0],start)<=150
 print("cancel_ms",time.ticks_diff(shown[0],start))
 display.show=original

async def check_soak():
 bmo.set_invert("0");bmo.set_mood("auto")
 await asyncio.sleep(2);gc.collect();before=gc.mem_free();minimum=before
 print("soak_start_heap",before)
 start=time.ticks_ms();polls=0;feelings=set()
 while time.ticks_diff(time.ticks_ms(),start)<1800000:
  r,w=await asyncio.open_connection("127.0.0.1",80)
  w.write(b"GET /state HTTP/1.0\r\n\r\n");await w.drain()
  response=b""
  while True:
   chunk=await asyncio.wait_for(r.read(512),10)
   if not chunk:break
   response+=chunk
  w.close();await w.wait_closed()
  assert b'200 OK' in response and b'"auto"' in response,repr(response)
  feelings.add(bmo.S["feeling"]);polls+=1
  gc.collect();minimum=min(minimum,gc.mem_free())
  await asyncio.sleep(3)
 gc.collect();after=gc.mem_free()
 print("soak_30min",polls,"heap",before,after,minimum,"feelings",feelings)
 assert before-after<4096,"Investigate retained memory"

asyncio.run(check())
