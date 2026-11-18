// Fixed clock and identical inputs before/after; records selection, not delivery/read receipts.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {Carousel, counts} from '../../bb-plugin-emo/model.ts';

function state(id, extra={}) {
  return {id, projectId:'p', title:id, alias:'BB#'+id, status:'idle', working:false,
    pending:false, retry:false, queued:false, completion:0, completionAt:0,
    seen:0, dismissed:0, failure:0, failureRequestId:'', cursor:0, rootTurn:'', requestId:'', ...extra};
}
const trace=[];
let carousel=new Carousel();
function sample(scenario, now, states, source=true) {
  const card=carousel.next(states,now,source);
  trace.push({scenario,now,card,counts:counts(states),states:structuredClone(states)});
}
const q=state('q',{pending:true,working:true});
const a=state('a',{completion:5,completionAt:1000});
const b=state('b',{completion:6,completionAt:1000});
const error=state('e',{status:'error',failure:7});
sample('background',0,[state('w',{working:true})]);
const all=[q,a,b];
sample('urgent arrives',100,all);
all.push(error);
sample('new error cannot interrupt',101,all);
sample('complete slot boundary',8099,all);
sample('reply after urgent',8100,all);
sample('complete reply slot',16099,all);
sample('next urgent',16100,all);
sample('second reply',24100,all);
b.completion=0;
sample('read removes current reply immediately',24101,all);
q.completion=8;
sample('pending and unread independent',25000,all);
q.completion=0;
sample('read cannot clear question',25001,all);
q.pending=false;error.dismissed=7;
sample('resolved events leave work',25002,all);
sample('reply not due yet',68099,all);
sample('reply due after sixty seconds',68100,all);
carousel=new Carousel();
sample('restart preserves reminder history',68101,all);
sample('unknown source',70000,all,false);
sample('source recovers',70001,all);
sample('next minute',128100,all);
a.completion=0;
sample('actual read stops reminder',128101,all);
sample('retry face only',130000,[state('r',{status:'error',failure:1,retry:true})]);
sample('queued face only',130001,[state('r',{queued:true})]);
sample('idle',130002,[]);
carousel=new Carousel();
const many=Array.from({length:10},(_,i)=>state(String(i),{pending:true}));
for(let i=0;i<20;i++) {
  if(i)many.push(state('new'+i,{pending:true}));
  sample('fair queue with arrivals',i*8000,many);
}
const baseline=JSON.parse(gunzipSync(readFileSync(new URL('./before-trace.json.gz',import.meta.url))).toString());
assert.deepEqual(trace,baseline,'Selection, timing, counters or unread state changed');
console.log('PASS',trace.length,'deterministic selections match the frozen baseline');
