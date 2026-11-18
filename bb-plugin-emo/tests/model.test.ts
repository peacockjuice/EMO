import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Carousel,counts,eventsInto,kind,type RecordState,type Event} from '../model.ts';
function state(id='a',extra:Partial<RecordState>={}):RecordState{return {id,projectId:'p',title:id,alias:'BB#'+id,status:'idle',working:false,pending:false,retry:false,queued:false,completion:0,completionAt:0,seen:0,dismissed:0,failure:0,failureRequestId:'',cursor:0,rootTurn:'',requestId:'',...extra};}
function event(seq:number,type:string,status?:string,turnId='root',data={}):Event{return {seq,type,createdAt:seq*1000,scope:{kind:'turn',turnId},data:{status,...data}};}
test('work and question are independent; question and error are both counted',()=>{const s=state('a',{working:true,pending:true,status:'error',failure:1});assert.equal(kind(s),'question');assert.deepEqual(counts([s]),[1,1,1,0]);s.pending=false;assert.equal(kind(s),'error');s.retry=true;assert.equal(kind(s),'wait');assert.deepEqual(counts([s]),[1,0,0,0]);});
test('completion only from root; stop, duplicate, new turn and bootstrap preserve only unread completion',()=>{const s=state();eventsInto(s,[event(1,'turn/started'),event(2,'turn/started',undefined,'child',{parentToolCallId:'tool'}),event(3,'turn/completed','completed','child')]);assert.equal(s.completion,0);eventsInto(s,[event(4,'turn/completed','completed')]);assert.equal(s.completion,4);eventsInto(s,[event(4,'turn/completed','completed')]);assert.equal(s.completion,4);eventsInto(s,[event(5,'turn/started'),event(6,'turn/completed','interrupted')]);assert.equal(s.completion,0);eventsInto(s,[event(7,'turn/started'),event(8,'turn/completed','completed')],true);assert.equal(s.seen,8);assert.equal(kind(s),'done');eventsInto(s,[event(9,'system/thread/interrupted')]);assert.equal(s.completion,0);});
test('completion reaction yields to work once; unread count persists',()=>{const done=state('a',{completion:5,completionAt:1000});const work=state('b',{working:true});const c=new Carousel();assert.equal(c.next([done,work],1000).face,'done');assert.equal(c.next([done,work],8999).face,'done');assert.equal(c.next([done,work],9000).face,'work');assert.equal(done.seen,0);assert.equal(done.notifiedCompletion,5);assert.deepEqual(counts([done,work]),[1,0,0,1]);});
test('urgent interruption and ten sessions remain fair as new urgent sessions arrive',()=>{const c=new Carousel();const a=state('work',{working:true});assert.equal(c.next([a],0).face,'work');const states=Array.from({length:10},(_,i)=>state(String(i),{pending:true}));assert.match(c.next([a,...states],100).card,/^0:/);for(let i=1;i<10;i++){states.push(state('new'+i,{pending:true}));assert.match(c.next(states,100+i*8000).card,new RegExp('^'+i+':'));}});
test('old unread completion is still an answer; stale source does not claim work',()=>{const c=new Carousel();const s=state('a',{completion:1,completionAt:0});assert.equal(c.next([s],31000).face,'done');const unknown=c.next([s],32000,false);assert.equal(unknown.source,false);assert.deepEqual(unknown.counts,[0,0,0,0]);});
test('dismissed failure does not hide a new failure and queued work is not running',()=>{const s=state('a',{status:'error',failure:4,dismissed:4,queued:true});assert.equal(kind(s),'wait');s.failure=5;assert.equal(kind(s),'error');assert.deepEqual(counts([s]),[0,0,1,0]);});

test('a new completion in the same session receives its own eight-second slot',()=>{
 const s=state('a',{working:true});const c=new Carousel();c.next([s],0);
 s.working=false;s.completion=7;s.completionAt=7000;
 assert.equal(c.next([s],7000).face,'done');
 assert.equal(c.next([s],9000).face,'done');
 assert.equal(s.seen,0);
 assert.equal(c.next([s],15000).face,'idle');assert.equal(s.seen,0);assert.equal(s.notifiedCompletion,7);
});
test('question label wins over retry just like its face',()=>{
 const s=state('a',{pending:true,retry:true});const card=new Carousel().next([s],0);
 assert.equal(card.face,'question');assert.match(card.text,/НУЖЕН ОТВЕТ/);
});

test('unread reminders repeat at sixty seconds, survive restart and stop on reading',()=>{
 const s=state('a',{completion:5,completionAt:1000,seen:5});let c=new Carousel();
 assert.equal(c.next([s],1000).text,'BB#a: ЕСТЬ ОТВЕТ');
 assert.equal(c.next([s],9000).face,'idle');assert.equal(kind(s),'done');
 c=new Carousel();assert.equal(c.next([s],60999).face,'idle');
 assert.equal(c.next([s],61000).face,'done');assert.equal(s.notifiedAt,61000);
 s.completion=0;assert.equal(c.next([s],62000).face,'idle');
 assert.deepEqual(counts([s]),[0,0,0,0]);
});
test('urgent and unread rings both progress without interrupting an attention card',()=>{
 const q=state('q',{pending:true});const q2=state('q2',{pending:true});
 const a=state('a',{completion:1});const b=state('b',{completion:2});const c=new Carousel();
 const all=[q,q2,a,b];
 assert.match(c.next(all,0).card,/^q:/);
 assert.match(c.next(all,7999).card,/^q:/);
 assert.match(c.next(all,8000).card,/^a:/);
 const error=state('e',{status:'error',failure:3});all.push(error);
 assert.match(c.next(all,9000).card,/^a:/);
 assert.match(c.next(all,16000).card,/^q2:/);
 assert.match(c.next(all,24000).card,/^b:/);
 assert.match(c.next(all,32000).card,/^q:/);
 assert.match(c.next(all,40000).card,/^e:/);
 q.pending=false;q2.pending=false;error.dismissed=3;a.completion=0;b.completion=0;
 assert.equal(c.next(all,41000).face,'idle');
});
test('read reply cannot clear a pending interaction; new completion gets a fresh notice',()=>{
 const s=state('a',{pending:true,completion:5});const c=new Carousel();
 assert.equal(c.next([s],0).face,'question');s.completion=0;
 assert.equal(c.next([s],1000).face,'question');s.pending=false;
 assert.equal(c.next([s],2000).face,'idle');s.completion=6;
 assert.equal(c.next([s],3000).face,'done');assert.equal(s.notifiedCompletion,6);
 s.completion=7;assert.equal(c.next([s],4000).face,'done');assert.equal(s.notifiedCompletion,7);
 assert.equal(c.next([s],11999).face,'done');assert.equal(c.next([s],12000).face,'idle');
});
