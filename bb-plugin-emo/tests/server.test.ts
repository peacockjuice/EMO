import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setTimeout as sleep} from 'node:timers/promises';
import {createFakePluginHost,makeThreadResponse} from '@get-bb/plugin-sdk/testing';
import plugin from '../server.ts';
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
  row={...row,lastReadAt:Date.now()+1};changed();await eventually(s=>s.threads[0].completion===0);
  await harness.behavior.callRpc('exclude',{id:'t',excluded:true});assert.equal((await status()).threads[0].excluded,true);
  callbacks.get('realtime:connection')!({state:'disconnected'});assert.equal((await status()).sourceReady,false);
  callbacks.get('realtime:connection')!({state:'connected'});await eventually(s=>s.sourceReady);
  row={...row,archivedAt:Date.now()};changed();await eventually(s=>s.threads.length===0);
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
