import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {createHash,createHmac} from 'node:crypto';
import {Transport} from '../transport.ts';
import type {Card} from '../model.ts';
const key=Buffer.alloc(32,7),nonce='1'.repeat(32),boot='2'.repeat(32);
const card:Card={card:'a',face:'question',text:'? PDF#2: НУЖЕН ОТВЕТ',counts:[2,1,0,1],source:true,ttl:30};
test('signed UTF8 wire, monotonic sequence, forged response and cancellation',async()=>{
 let forged=false;const observed:number[]=[];
 const server=createServer(async(req,res)=>{
  if(req.url==='/bb/challenge'){res.end(JSON.stringify({nonce,boot}));return;}
  const chunks=[];for await(const chunk of req)chunks.push(chunk);const body=Buffer.concat(chunks);const data=JSON.parse(body.toString());
  const sig=createHmac('sha256',key).update('POST\n/bb/state\n'+nonce+'\n'+createHash('sha256').update(body).digest('hex')).digest('hex');
  assert.equal(req.headers['x-emo-signature'],sig);assert.equal(data.boot,boot);assert.equal(data.text,card.text);assert.ok(body.length<=1024);observed.push(data.seq);
  const raw=JSON.stringify({ok:true,status:'live',seq:data.seq,epoch:data.epoch});res.setHeader('X-EMO-Reply',forged?'0'.repeat(64):createHmac('sha256',key).update(nonce+'\n'+raw).digest('hex'));res.end(raw);
 });await new Promise<void>(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{const address=server.address() as {port:number};const url='http://127.0.0.1:'+address.port;const t=new Transport(123);const signal=new AbortController().signal;assert.equal((await t.send(url,key.toString('hex'),card,signal)).status,'live');await t.send(url,key.toString('hex'),card,signal);assert.deepEqual(observed,[1,2]);forged=true;await assert.rejects(t.send(url,key.toString('hex'),card,signal),/Подпись/);await assert.rejects(t.send(url,key.toString('hex'),card,AbortSignal.abort()));}finally{await new Promise<void>((resolve,reject)=>server.close(e=>e?reject(e):resolve()));}
});

test('oversized challenge is cancelled before buffering the full response',async(t)=>{
 let pulls=0,cancelled=false;
 t.mock.method(globalThis,'fetch',async()=>new Response(new ReadableStream({
  pull(controller){pulls++;controller.enqueue(new Uint8Array(1024).fill(32));if(pulls===64)controller.close();},
  cancel(){cancelled=true;}
 })));
 await assert.rejects(new Transport(123).send('http://robot',key.toString('hex'),card,new AbortController().signal));
 assert.ok(pulls<64,'buffered the whole oversized response');assert.equal(cancelled,true);
});
