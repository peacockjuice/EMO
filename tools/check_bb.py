"""Offline BB receiver and frame checks; no device or credentials required."""
import asyncio, gc, hashlib, hmac, json, sys, time, types, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
now=[0];PERIOD=1<<30
time.ticks_ms=lambda:now[0]%PERIOD
time.ticks_diff=lambda a,b:((a-b+PERIOD//2)%PERIOD)-PERIOD//2
gc.mem_free=lambda:123456
class Changed(Exception):pass
bmo=types.SimpleNamespace(S={'mood':'bb','ver':1,'frames':0},_v=1,Changed=Changed)
sys.modules['bmo']=bmo
import emo_bb as bb
from emo_font import DATA,glyph
from tools.wifi_update import bundle
class Reader:
 def __init__(self,data):self.data=data
 async def readexactly(self,n):
  if len(self.data)<n:raise ValueError('short')
  return self.data[:n]
class Writer:
 def __init__(self):self.data=b''
 def write(self,data):self.data+=data.encode() if isinstance(data,str) else data
 async def drain(self):pass
class BBTests(unittest.TestCase):
 def setUp(self):
  import emo_bb_view
  emo_bb_view._connection=None
  now[0]=1000;bb._snapshot=None;bb._epoch=0;bb._seq=0;bb._nonce=None;bb._key=b'K'*32;bmo.S.update(mood='bb',ver=1);bmo._v=1
 def value(self,**kw):return dict(boot=bb._boot,epoch=1,seq=1,ttl=30,source=True,card='a',face='work',text='PDF#1: РАБОТАЕТ',counts=[1,0,0,0],**kw) if not kw else dict(self.value(),**kw)
 def test_order_epoch_boot(self):
  bb.accept(self.value(seq=2),1)
  for v in [self.value(seq=1),self.value(seq=2),self.value(boot='old',seq=3)]:
   with self.assertRaises(ValueError):bb.accept(v,1)
  bb.accept(self.value(epoch=2,seq=1),1)
  with self.assertRaises(ValueError):bb.accept(self.value(epoch=1,seq=100),1)
 def test_heartbeat_card_and_ttl_wrap(self):
  now[0]=PERIOD-100;bb.accept(self.value(),1);start=bb._card_at
  now[0]+=10000;bb.accept(self.value(seq=2,counts=[2,1,0,0]),1);self.assertEqual(bb._card_at,start)
  now[0]+=30001;self.assertEqual(bb.status(),'offline');self.assertEqual(bb.view(time.ticks_ms())[1],'НЕТ СВЯЗИ С BB')
  bb.accept(self.value(seq=3),1);self.assertEqual(bb.status(),'live');self.assertNotEqual(bb._card_at,start)
 def test_manual_mode_and_inflight_version(self):
  bmo.S['mood']='auto';self.assertEqual(bb.accept(self.value(),1),'mode_disabled');self.assertIsNone(bb._snapshot)
  bmo.S.update(mood='bb',ver=2);self.assertEqual(bb.accept(self.value(seq=2),1),'mode_disabled');self.assertIsNone(bb._snapshot)
  self.assertEqual(bb.accept(self.value(seq=3),2),'live');bb.reset_view();self.assertEqual(bb.status(),'waiting')
 def test_bad_fields(self):
  for field,value in [('seq',True),('epoch',-1),('ttl',31),('counts',[0,0,0,-1]),('text','x'*65),('source',1),('face','evil'),('text','bad\n')]:
   with self.assertRaises(ValueError,msg=field):bb.accept(self.value(**{field:value}),1)
 def test_question_cycle_scroll_and_heartbeat(self):
  label='? PDF#9: НУЖЕН ОТВЕТ';bb.accept(self.value(face='question',text=label),1)
  self.assertEqual(bb.view(1000)[0],'rosto22');self.assertEqual(bb.view(1999)[0],'rosto22')
  self.assertEqual(bb.view(2000)[0],'talk_bobo');self.assertEqual(bb.view(2999)[0],'talk_bobo')
  self.assertIsNone(bb.view(3000)[0]);self.assertEqual(bb.view(3500)[3],0)
  distance=len(label)*24-4-128
  self.assertEqual(bb.view(4750)[3],distance*121//200);self.assertEqual(bb.view(6000)[3],distance);self.assertEqual(bb.view(8500)[3],distance);self.assertEqual(bb.view(8999)[3],distance)
  self.assertEqual(bb.view(9000)[0],'rosto22')
  now[0]=9500;bb.accept(self.value(seq=2,face='question',text=label),1)
  self.assertEqual(bb._card_at,1000);self.assertEqual(bb.view(10000)[0],'talk_bobo')
 def test_scroll_done_unknown(self):
  bb.accept(self.value(text='Я'*36,face='done'),1)
  self.assertEqual(bb.view(1000)[0],'wink')
  self.assertEqual(bb.view(1999)[0],'wink')
  self.assertEqual(bb.view(2000)[0],'rosto01')
  self.assertEqual(bb.view(2999)[0],'rosto01')
  self.assertIsNone(bb.view(3000)[0]);self.assertIsNone(bb.view(4000)[0])
  self.assertEqual(bb.view(8500)[3],732);self.assertEqual(bb.view(9000)[0],'rosto04')
  bb.accept(self.value(seq=2,source=False),1);self.assertEqual(bb.status(),'unknown');self.assertIsNone(bb.view(4000)[2])
 def test_large_font_clips_and_has_no_footer(self):
  from emo_bb_display import overlay
  class Display:
   def __init__(self):self.pixels=[]
   def pixel(self,x,y,c):self.pixels.append((x,y));assert 0<=x<128 and 0<=y<64
   def fill_rect(self,x,y,w,h,c):
    if c:
     for yy in range(y,y+h):
      for xx in range(x,x+w):self.pixel(xx,yy,c)
  o=Display();overlay(o,'? PDF#9: НУЖЕН ОТВЕТ',[2,1,0,1],10,True)
  self.assertTrue(any(y==59 for x,y in o.pixels));self.assertTrue(all(y<60 for x,y in o.pixels))
  o=Display();overlay(o,'NO FOOTER',[2,1,0,1],0,False);self.assertEqual(o.pixels,[])
 def test_accents_above_full_height_letters_and_horizontal_clipping(self):
  from emo_font import text
  class Display:
   def __init__(self):self.pixels=set()
   def pixel(self,x,y,c):
    assert 0<=x<128 and 0<=y<64
    if c:self.pixels.add((x,y))
   def fill_rect(self,x,y,w,h,c):
    for yy in range(y,y+h):
     for xx in range(x,x+w):self.pixel(xx,yy,c)
  for letter,base in [('Ё','Е'),('Й','И')]:
   o=Display();b=Display();text(o,letter,0,32,4);text(b,base,0,32,4)
   self.assertEqual({p for p in o.pixels if p[1]>=32},b.pixels)
   marks={p for p in o.pixels if p[1]<32}
   self.assertTrue(marks);self.assertTrue(all(20<=y<28 for x,y in marks))
   for x in (-19,-4,120,127):text(Display(),letter,x,32,4)
  dots=Display();text(dots,'Ё',0,32,4)
  self.assertIn((4,24),dots.pixels);self.assertIn((12,24),dots.pixels);self.assertNotIn((8,24),dots.pixels)
  breve=Display();text(breve,'Й',0,32,4)
  self.assertIn((4,20),breve.pixels);self.assertIn((8,24),breve.pixels);self.assertIn((12,20),breve.pixels)
 def test_idle_has_only_face_but_stale_completion_and_offline_stay_visible(self):
  bb.accept(self.value(card='idle',face='idle',text='BB: ВСЁ СПОКОЙНО'),1)
  for t in (1000,3000,6000,8999,9000):
   self.assertEqual(bb.view(t),('rosto04','',None,0))
  bb.accept(self.value(seq=2,card='thread:done:42',face='done',text='PDF#9: ЕСТЬ ОТВЕТ'),1)
  self.assertIsNone(bb.view(4000)[0]);self.assertIn('ЕСТЬ ОТВЕТ',bb.view(4000)[1])
  self.assertEqual(bb.view(32000)[1],'НЕТ СВЯЗИ С BB')
 def test_background_states_are_quiet_and_error_has_two_distinct_faces(self):
  for seq,(kind,face) in enumerate([('work','look'),('wait','rosto04'),('idle','rosto04')],1):
   bb.accept(self.value(seq=seq,face=kind),1)
   for t in (1000,3000,8000):self.assertEqual(bb.view(t),(face,'',None,0))
  bb.accept(self.value(seq=4,face='error'),1)
  self.assertEqual(bb.view(1000)[0],'rosto17');self.assertEqual(bb.view(2000)[0],'rosto03');self.assertIsNone(bb.view(3000)[0])
 def test_connection_grace_and_minute_reminders(self):
  self.assertEqual(bb.view(1000),('rosto04','',None,0))
  self.assertEqual(bb.view(30999)[1],'')
  self.assertEqual(bb.view(31000)[0],'rosto17');self.assertIsNone(bb.view(33000)[0])
  self.assertEqual(bb.view(39000)[1],'');self.assertEqual(bb.view(90999)[1],'')
  self.assertEqual(bb.view(91000)[1],'НЕТ СВЯЗИ С BB')
  now[0]=92000;bb.accept(self.value(source=False),1)
  self.assertEqual(bb.view(92000)[0],'rosto16');self.assertIsNone(bb.view(94000)[0])
  self.assertEqual(bb.view(100000)[1],'')
  now[0]=102000;bb.accept(self.value(seq=2,source=False),1)
  self.assertEqual(bb.view(102000)[1],'','unknown heartbeat must not restart notice')
  self.assertEqual(bb.view(122000)[1],'')
  now[0]=150000;bb.accept(self.value(seq=3,source=False),1)
  self.assertEqual(bb.view(152000)[0],'rosto16')
  now[0]=153000;bb.accept(self.value(seq=4),1)
  self.assertEqual(bb.view(153000)[1],'')
 def test_signed_utf8_replay_size_tamper(self):
  async def run():
   challenge=bb.challenge();raw=json.dumps(self.value(text='? PDF#2: НУЖЕН ОТВЕТ'),ensure_ascii=False).encode();nonce=challenge['nonce']
   sig=hmac.new(bb._key,('POST\n/bb/state\n'+nonce+'\n'+hashlib.sha256(raw).hexdigest()).encode(),hashlib.sha256).hexdigest()
   headers={'content-length':str(len(raw)),'x-emo-nonce':nonce,'x-emo-signature':sig}
   bad=Writer();await bb.handle('POST','/bb/state',headers,Reader(raw.replace(b'PDF',b'BAD')),bad,1);self.assertIn(b'401 Result',bad.data);self.assertIsNone(bb._snapshot)
   large=Writer();await bb.handle('POST','/bb/state',dict(headers,**{'content-length':'1025'}),Reader(raw),large,1);self.assertIn(b'400 Result',large.data)
   w=Writer();await bb.handle('POST','/bb/state',headers,Reader(raw),w,1);self.assertIn(b'200 Result',w.data)
   head,body=w.data.split(b'\r\n\r\n');expected=hmac.new(bb._key,nonce.encode()+b'\n'+body,hashlib.sha256).hexdigest().encode();self.assertIn(expected,head);self.assertTrue(json.loads(body)['ok'])
   replay=Writer();await bb.handle('POST','/bb/state',headers,Reader(raw),replay,1);self.assertIn(b'401 Result',replay.data)
  asyncio.run(run())
 def test_nonce_is_single_use_across_overlapping_posts(self):
  async def run():
   nonce=bb.challenge()['nonce'];gate=asyncio.Event();waiting=asyncio.Event()
   def packet(seq):
    raw=json.dumps(self.value(seq=seq)).encode()
    sig=hmac.new(bb._key,('POST\n/bb/state\n'+nonce+'\n'+hashlib.sha256(raw).hexdigest()).encode(),hashlib.sha256).hexdigest()
    return raw,{'content-length':str(len(raw)),'x-emo-nonce':nonce,'x-emo-signature':sig}
   raw2,h2=packet(2)
   class Slow(Reader):
    async def readexactly(self,n):waiting.set();await gate.wait();return self.data
   w2=Writer();late=asyncio.create_task(bb.handle('POST','/bb/state',h2,Slow(raw2),w2,1));await waiting.wait()
   raw1,h1=packet(1);w1=Writer();await bb.handle('POST','/bb/state',h1,Reader(raw1),w1,1)
   gate.set();await late
   self.assertIn(b'200 Result',w1.data);self.assertIn(b'401 Result',w2.data);self.assertEqual(bb._seq,1)
  asyncio.run(run())
 def test_bounded_headers(self):
  import emo_http
  class R:
   def __init__(self,data):self.data=data
   async def read(self,n):out=self.data[:n];self.data=self.data[n:];return out
  async def check():
   self.assertEqual(await emo_http.request(R(b'GET /state HTTP/1.1\r\nHost: test\r\n\r\n')),('GET','/state',{'host':'test'}))
   for data in [b'GET / HTTP/1.1\r\nHost: a\r\nHost: b\r\n\r\n',b'GET / HTTP/1.1\r\nX: '+b'x'*513+b'\r\n\r\n',b'GET / HTTP/1.1\r\n']:
    with self.assertRaises(ValueError):await emo_http.request(R(data))
  asyncio.run(check())
 def test_buffered_headers_preserve_body_and_bound_socket_reads(self):
  import emo_http
  body=b'x'*300
  class Socket:
   data=b'POST /bb/state HTTP/1.0\r\nContent-Length: 300\r\n\r\n'+body
   calls=0
   async def read(self,n):
    self.calls+=1;self.requested=n
    out=self.data[:n];self.data=self.data[n:];return out
  async def run():
   sock=Socket();r=emo_http.Buffered(sock)
   method,path,headers=await emo_http.request(r)
   self.assertEqual((method,path),('POST','/bb/state'));self.assertEqual(headers['content-length'],'300')
   self.assertEqual(await r.readexactly(300),body)
   self.assertLessEqual(sock.calls,3);self.assertEqual(sock.requested,128)
   with self.assertRaises(ValueError):await r.readexactly(1)
  asyncio.run(run())
 def test_frame_bank_and_font(self):
  from tools.check_assets import check
  check()
  for c in 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ':self.assertNotEqual(DATA[glyph(c)*5:glyph(c)*5+5],bytes(5))
  self.assertEqual(len(DATA),460)
  payload,_=bundle(ROOT);self.assertLess(len(payload),384*1024)
 def test_http_releases_slot_after_write_timeout(self):
  import ast,os
  import emo_http
  tree=ast.parse((ROOT/'bmo.py').read_text())
  function=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='handle')
  ns={'asyncio':asyncio,'gc':gc,'S':{'ver':1},'_clients':0,'state_json':lambda:'{}'}
  exec(compile(ast.Module(body=[function],type_ignores=[]),'bmo.py','exec'),ns)
  class R:
   data=b'GET /state HTTP/1.1\r\n\r\n'
   async def read(self,n):out=self.data[:n];self.data=self.data[n:];return out
  class W(Writer):
   closed=False
   drained=False
   async def drain(self):self.drained=True;raise asyncio.TimeoutError('simulated slow peer')
   def close(self):self.closed=True
   async def wait_closed(self):pass
  w=W();asyncio.run(ns['handle'](R(),w));self.assertTrue(w.closed);self.assertTrue(w.drained);self.assertEqual(ns['_clients'],0)
 def test_renderer_restores_face_after_large_text(self):
  bb.accept(self.value(face='question',text='? PDF#9: НУЖЕН ОТВЕТ'),1)
  rendered={}
  class Display:
   buffer=bytearray(1024)
   def pixel(self,x,y,c):
    i=x+y//8*128;mask=1<<(y%8)
    self.buffer[i]=(self.buffer[i]|mask) if c else (self.buffer[i]&~mask)
   def fill_rect(self,x,y,w,h,c):
    for yy in range(y,y+h):
     for xx in range(x,x+w):self.pixel(xx,yy,c)
   def scroll(self,dx,dy):
    old=bytes(self.buffer)
    for y in range(63,-1,-1):
     for x in range(128):self.pixel(x,y,1 if y>=dy and old[x+(y-dy)//8*128]&(1<<((y-dy)%8)) else 0)
   def show(self):rendered[now[0]]=bytes(self.buffer)
  async def sleep_ms(ms):
   now[0]+=250
   if now[0]>9250:bmo.S['ver']+=1
   await asyncio.sleep(0)
  asyncio.sleep_ms=sleep_ms
  with self.assertRaises(Changed):asyncio.run(bb.run(Display()))
  self.assertEqual(rendered[1000],rendered[9000])
  self.assertNotEqual(rendered[1000],rendered[2000])
  self.assertNotEqual(rendered[2000],rendered[3000])
  # The gap between the enlarged header and lowered text stays empty.
  self.assertEqual(rendered[3000][3*128:4*128],bytes(128))
  from emotion_sequences import SEQUENCES
  i=SEQUENCES['rosto22'][0][0]
  self.assertEqual(rendered[1000],(ROOT/'emotions.bin').read_bytes()[i*1024:(i+1)*1024])
 def test_renderer_yields_to_manual_change(self):
  class Display:
   buffer=bytearray(1024)
   def fill_rect(self,*args):pass
   def pixel(self,*args):pass
   def scroll(self,*args):pass
   def show(self):bmo.S['ver']+=1
  async def sleep_ms(ms):await asyncio.sleep(0)
  asyncio.sleep_ms=sleep_ms
  with self.assertRaises(Changed):asyncio.run(bb.run(Display()))
if __name__=='__main__':unittest.main()
