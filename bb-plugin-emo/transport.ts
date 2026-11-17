import {createHmac,createHash,timingSafeEqual} from 'node:crypto';
import type {Card} from './model.ts';
export type Receipt={ok:boolean;status?:string;epoch?:number;seq?:number;heap?:number;frames?:number;error?:string};
async function boundedBody(response:Response,limit:number):Promise<Buffer>{
 const reader=response.body?.getReader();if(!reader)throw Error('Пустой ответ робота');
 const chunks:Uint8Array[]=[];let size=0;
 try{
  while(true){
   const {done,value}=await reader.read();if(done)break;
   size+=value.byteLength;if(size>limit)throw Error('Ответ робота превышает лимит');
   chunks.push(value);
  }
  return Buffer.concat(chunks,size);
 }finally{try{await reader.cancel();}finally{reader.releaseLock();}}
}
export class Transport{
 private sequence=0;
 private epoch:number;
 constructor(epoch:number){this.epoch=epoch;}
 async send(url:string,secret:string,card:Card,signal:AbortSignal):Promise<Receipt>{
  if(!/^[a-f0-9]{64}$/i.test(secret))throw Error('Настройте ключ уведомлений');
  const base=new URL(url);if(!['http:','https:'].includes(base.protocol)||base.username||base.password)throw Error('Некорректный адрес робота');
  const key=Buffer.from(secret,'hex');
  const timeout=AbortSignal.any([signal,AbortSignal.timeout(6000)]);
  const challengeResponse=await fetch(new URL('/bb/challenge',base),{signal:timeout});
  if(!challengeResponse.ok)throw Error('Приёмник BB недоступен: '+challengeResponse.status);
  const challenge=JSON.parse((await boundedBody(challengeResponse,512)).toString()) as {boot:string;nonce:string};
  if(!/^[a-f0-9]{32}$/.test(challenge.boot)||!/^[a-f0-9]{32}$/.test(challenge.nonce))throw Error('Некорректный challenge');
  const seq=++this.sequence;const body=JSON.stringify({...card,boot:challenge.boot,epoch:this.epoch,seq});
  if(Buffer.byteLength(body)>1024)throw Error('Снимок превышает 1 KiB');
  const digest=createHash('sha256').update(body).digest('hex');
  const signature=createHmac('sha256',key).update('POST\n/bb/state\n'+challenge.nonce+'\n'+digest).digest('hex');
  const response=await fetch(new URL('/bb/state',base),{method:'POST',body,headers:{'Content-Type':'application/json','X-EMO-Nonce':challenge.nonce,'X-EMO-Signature':signature},signal:timeout});
  const raw=await boundedBody(response,4096);
  const expected=createHmac('sha256',key).update(challenge.nonce+'\n').update(raw).digest();
  const actual=Buffer.from(response.headers.get('X-EMO-Reply')??'','hex');
  if(actual.length!==expected.length||!timingSafeEqual(actual,expected))throw Error('Подпись ответа не подтверждена');
  const receipt=JSON.parse(raw.toString()) as Receipt;
  if(!response.ok||!receipt.ok||receipt.seq!==seq||receipt.epoch!==this.epoch)throw Error('Снимок отклонён: '+(receipt.error??response.status));
  return receipt;
 }
}
