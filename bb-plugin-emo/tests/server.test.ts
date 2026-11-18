import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setTimeout as sleep} from 'node:timers/promises';
import {createFakePluginHost,makeThreadResponse} from '@get-bb/plugin-sdk/testing';
import plugin from '../server.ts';
import {Transport} from '../transport.ts';
test('monitor observes interactions, source disconnect, read state, exclusions and removal without polling',async()=>{
 const callbacks=new Map<string,(e:any)=>void>();let listCalls=0;let pending=true;let events:any[]=[];
 let row={...makeThreadResponse({id:'t',projectId:'p',visibility:'visible',status:'active',hasPendingInteraction:true,parentThreadId:null}),activity:{activeBackgroundAgentCount:0,activeBackgroundCommandCount:0,activeWorkflowCount:0}};
 const {bb,harness}=createFakePluginHost({pluginId:'emo',settings:{projectIds:'["p"]'},sdk:{subscribe:({event,callback}:any)=>{callbacks.set(event,callback);return ()=>callbacks.delete(event);},projects:{list:async()=>[{id:'p',name:'PDF'}]},threads:{list:async()=>{listCalls++;return [row];},interactions:{list:async()=>pending?[{status:'pending'}]:[]},queue:{list:async()=>[]},events:{list:async({afterSeq}:any)=>events.filter(e=>!afterSeq||e.seq>Number(afterSeq))}}} as any});
 await plugin(bb);const service=harness.behavior.runService('monitor');
 async function status(){return await harness.behavior.callRpc('status',null) as any;}
 async function eventually(predicate:(s:any)=>boolean){for(let i=0;i<50;i++){const s=await status();if(predicate(s))return s;await sleep(25);}assert.fail('monitor did not settle: '+JSON.stringify(await status()));}
 function changed(){callbacks.get('thread:changed')!({id:'t',changes:['status-changed']});}
 try{
  assert.equal((await status()).sourceReady,false);callbacks.get('realtime:connection')!({state:'connected'});
  let s=await eventually(s=>s.sourceReady&&s.threads.length===1);assert.equal(s.threads[0].pending,true);assert.equal(s.threads[0].working,true);
  const initialCalls=listCalls;await sleep(600);assert.equal(listCalls,initialCalls,'steady state polled list');
  pending=false;row={...row,hasPendingInteraction:false};changed();await eventually(s=>!s.threads[0].pending);
  events=[{seq:1,type:'turn/started',createdAt:1000,scope:{kind:'turn',turnId:'turn'},data:{}},{seq:2,type:'turn/completed',createdAt:Date.now(),scope:{kind:'turn',turnId:'turn'},data:{status:'completed'}}];row={...row,status:'idle',lastReadAt:0};changed();await eventually(s=>s.threads[0].completion===2);
  pending=true;row={...row,hasPendingInteraction:true,lastReadAt:Date.now()+1};changed();
  await eventually(s=>s.threads[0].completion===0&&s.threads[0].kind==='question');
  pending=false;row={...row,hasPendingInteraction:false};changed();await eventually(s=>!s.threads[0].pending);
  await harness.behavior.callRpc('exclude',{id:'t',excluded:true});assert.equal((await status()).threads[0].excluded,true);
  callbacks.get('realtime:connection')!({state:'disconnected'});assert.equal((await status()).sourceReady,false);
  callbacks.get('realtime:connection')!({state:'connected'});await eventually(s=>s.sourceReady);
  for(const hidden of [{parentThreadId:'parent'},{visibility:'hidden'},{archivedAt:1},{deletedAt:1}] as const){
   row={...row,...hidden};changed();await eventually(s=>s.sourceReady&&s.threads.length===0);
   row={...row,parentThreadId:null,visibility:'visible',archivedAt:null,deletedAt:null};
   changed();await eventually(s=>s.sourceReady&&s.threads.length===1);
  }
 }finally{service.controller.abort();await service.done;await harness.lifecycle.dispose();assert.equal(callbacks.size,0);}
});

test('a change during initial enumeration cannot be overwritten by its stale row',async()=>{
 const callbacks=new Map<string,(e:any)=>void>();let first=true;
 let row={...makeThreadResponse({id:'t',projectId:'p',visibility:'visible',status:'idle',parentThreadId:null}),activity:{activeBackgroundAgentCount:0,activeBackgroundCommandCount:0,activeWorkflowCount:0}};
 const {bb,harness}=createFakePluginHost({pluginId:'emo',settings:{projectIds:'["p"]'},sdk:{subscribe:({event,callback}:any)=>{callbacks.set(event,callback);return ()=>callbacks.delete(event);},projects:{list:async()=>[{id:'p',name:'PDF'}]},threads:{list:async()=>{
  const old={...row};if(first){first=false;row={...row,status:'active'};callbacks.get('thread:changed')!({id:'t',changes:['status-changed']});}return [old];
 },interactions:{list:async()=>[]},queue:{list:async()=>[]},events:{list:async()=>[]}}} as any});
 await plugin(bb);const service=harness.behavior.runService('monitor');
 try{callbacks.get('realtime:connection')!({state:'connected'});await sleep(600);const s=await harness.behavior.callRpc('status',null) as any;assert.equal(s.sourceReady,true);assert.equal(s.threads[0].status,'active');}
 finally{service.controller.abort();await service.done;await harness.lifecycle.dispose();}
});

function unreadHost(){
 const callbacks=new Map<string,(e:any)=>void>();let pending=false;
 let row={...makeThreadResponse({id:'t',projectId:'p',visibility:'visible',status:'idle',parentThreadId:null,lastReadAt:0}),activity:{activeBackgroundAgentCount:0,activeBackgroundCommandCount:0,activeWorkflowCount:0}};
 const events=[{seq:1,type:'turn/started',createdAt:1000,scope:{kind:'turn',turnId:'root'},data:{}},{seq:2,type:'turn/completed',createdAt:1000,scope:{kind:'turn',turnId:'root'},data:{status:'completed'}}];
 const host=createFakePluginHost({pluginId:'emo',settings:{projectIds:'["p"]',notifyKey:'11'.repeat(32)},sdk:{
  subscribe:({event,callback}:any)=>{callbacks.set(event,callback);return ()=>callbacks.delete(event);},projects:{list:async()=>[{id:'p',name:'PDF'}]},
  threads:{list:async()=>[row],interactions:{list:async()=>pending?[{status:'pending'}]:[]},queue:{list:async()=>[]},events:{list:async({afterSeq}:any)=>events.filter(e=>!afterSeq||e.seq>Number(afterSeq))}},
 } as any});
 return {host,connect:()=>callbacks.get('realtime:connection')!({state:'connected'}),readWithQuestion:()=>{
  pending=true;row={...row,lastReadAt:Date.now(),hasPendingInteraction:true};callbacks.get('thread:changed')!({id:'t',changes:['status-changed']});
 }};
}
async function eventually(predicate:()=>Promise<boolean>){
 for(let i=0;i<120;i++){if(await predicate())return;await sleep(25);}
 assert.fail('monitor did not reach the expected state');
}

test('persisted notices survive a host reload; disabled mode and failed delivery never mark a reply read',async t=>{
 let now=1000000;t.mock.method(Date,'now',()=>now);
 const fixture=unreadHost();let host=fixture.host;let failDelivery=false;const notices:number[]=[];
 t.mock.method(Transport.prototype,'send',async(_url,_key,card)=>{
  if(card.face==='done'){
   const saved=await host.bb.storage.kv.get<any>('thread:t');
   assert.equal(saved.notifiedCompletion,2);assert.equal(saved.notifiedAt,now,'notice was not saved before sending');
   assert.equal(saved.completion,2);notices.push(saved.notifiedAt);
  }
  if(failDelivery)throw Error('simulated delivery failure');
  return {ok:true,status:'mode_disabled'};
 });
 await plugin(host.bb);let service=host.harness.behavior.runService('monitor');
 const status=async()=>await host.harness.behavior.callRpc('status',null) as any;
 try{
  // Let the startup unknown-card receipt finish, then pass its 300 ms send gate.
  await eventually(async()=>(await status()).delivery==='mode_disabled');now=1001000;
  fixture.connect();await eventually(async()=>notices.length===1&&(await status()).delivery==='mode_disabled');
  const saved=await host.bb.storage.kv.get<any>('thread:t');assert.equal(saved.notifiedAt,1001000);assert.equal(saved.completion,2);
  service.controller.abort();await service.done;
  now+=1000;host=await host.harness.lifecycle.reload(plugin);
  service=host.harness.behavior.runService('monitor');fixture.connect();
  await eventually(async()=>(await status()).sourceReady);await sleep(300);
  assert.equal(notices.length,1);assert.equal((await status()).threads[0].notifiedAt,1001000);
  assert.equal((await host.bb.storage.kv.get<any>('thread:t')).alias,saved.alias);
  now=1061000;failDelivery=true;
  await eventually(async()=>notices.length===2&&(await status()).delivery==='offline');
  assert.deepEqual(notices,[1001000,1061000]);
  const afterFailure=await host.bb.storage.kv.get<any>('thread:t');assert.equal(afterFailure.notifiedAt,1061000);assert.equal(afterFailure.completion,2);
  fixture.readWithQuestion();await eventually(async()=>{const s=(await status()).threads[0];return s.completion===0&&s.kind==='question';});
  assert.equal((await host.bb.storage.kv.get<any>('thread:t')).completion,0);
 }finally{service.controller.abort();await service.done;await host.harness.lifecycle.dispose();}
});

test('a failed notice save stops the monitor before the answer card can be sent',async t=>{
 const {host,connect}=unreadHost();const sent:string[]=[];
 const set=host.bb.storage.kv.set.bind(host.bb.storage.kv);
 t.mock.method(host.bb.storage.kv,'set',async(key,value)=>{
  if(key==='thread:t'&&(value as any).notifiedAt!==undefined)throw Error('simulated notice save failure');
  return set(key,value);
 });
 t.mock.method(Transport.prototype,'send',async(_url,_key,card)=>{sent.push(card.face);return {ok:true,status:'live'};});
 await plugin(host.bb);const service=host.harness.behavior.runService('monitor');
 const failed=assert.rejects(service.done,/simulated notice save failure/);
 try{
  connect();await failed;assert.ok(!sent.includes('done'));
  const saved=await host.bb.storage.kv.get<any>('thread:t');assert.equal(saved.completion,2);assert.equal(saved.notifiedAt,undefined);
 }finally{service.controller.abort();await host.harness.lifecycle.dispose();}
});
