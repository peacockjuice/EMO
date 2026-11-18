export type Kind = 'question'|'error'|'done'|'work'|'wait'|'idle';
export type RecordState = {id:string;projectId:string;title:string;alias:string;status:string;working:boolean;pending:boolean;retry:boolean;queued:boolean;completion:number;completionAt:number;seen:number;notifiedCompletion?:number;notifiedAt?:number;dismissed:number;failure:number;failureRequestId:string;cursor:number;rootTurn:string;requestId:string};
export type Event = {seq:number;createdAt:number;type:string;scope:{kind:string;turnId?:string};data:Record<string,unknown>};
export const labels:Record<Kind,string>={question:'НУЖЕН ОТВЕТ',error:'ОШИБКА',done:'ЕСТЬ ОТВЕТ',work:'РАБОТАЕТ',wait:'ЖДЁТ ЗАПУСКА',idle:'ВСЁ СПОКОЙНО'};
export function eventsInto(s:RecordState,events:Event[],bootstrap=false){
 for(const e of [...events].sort((a,b)=>a.seq-b.seq)){
  if(e.seq<=s.cursor)continue;
  s.cursor=e.seq;
  if(e.type==='client/turn/requested' && typeof e.data.requestId==='string')s.requestId=e.data.requestId;
  if(e.type==='turn/started' && !e.data.parentToolCallId && e.scope.kind==='turn'){
   s.rootTurn=e.scope.turnId??'';s.completion=0;s.failure=0;s.dismissed=0;
  }
  if(e.type==='system/thread/interrupted'){s.completion=0;s.rootTurn='';}
  if(e.type==='turn/completed' && e.scope.kind==='turn' && e.scope.turnId===s.rootTurn){
   if(e.data.status==='completed'){
    s.completion=e.seq;s.completionAt=e.createdAt;
    if(bootstrap)s.seen=e.seq;
   }else{
    s.completion=0;
    if(e.data.status==='failed'){s.failure=e.seq;s.failureRequestId=s.requestId;}
   }
  }
 }
}
export function kind(s:RecordState):Kind{
 if(s.pending)return 'question';
 if(s.status==='error'&&!s.retry&&s.dismissed!==s.failure)return 'error';
 if(s.completion)return 'done';
 if(s.retry)return 'wait';
 if(s.working)return 'work';
 if(s.queued||['starting','pending','stopping'].includes(s.status))return 'wait';
 return 'idle';
}
export function counts(states:RecordState[]){return [states.filter(s=>s.working).length,states.filter(s=>s.pending).length,states.filter(s=>s.status==='error'&&!s.retry&&s.dismissed!==s.failure).length,states.filter(s=>s.completion>0).length];}
export type Card={card:string;face:Kind;text:string;counts:number[];source:boolean;ttl:number};
export type Selection={card:Card;notice?:{id:string;notifiedCompletion:number;notifiedAt:number}};
// Display history is separate from unread state; only BB read events clear completion.
export const SLOT_MS=8000, REMINDER_MS=60000;
export class Carousel{
 private urgentQueue:string[]=[];private replyQueue:string[]=[];
 private current='';private identity='';private until=0;private lastUrgent=false;
 private sync(queue:string[],states:RecordState[]){
  const ids=new Set(states.map(s=>s.id));
  const result=queue.filter(id=>ids.has(id));
  for(const s of states)if(!result.includes(s.id))result.push(s.id);
  return result;
 }
 private id(s:RecordState){const k=kind(s);return s.id+':'+k+':'+(k==='done'?s.completion:k==='error'?s.failure:0);}
 next(states:RecordState[],now:number,source=true):Selection{
  let notice:Selection['notice'];
  if(!source){this.current='';return {card:{card:'unknown',face:'idle',text:'СТАТУС BB НЕИЗВЕСТЕН',counts:[0,0,0,0],source:false,ttl:30}};}
  const urgent=states.filter(s=>['question','error'].includes(kind(s)));
  const replies=states.filter(s=>kind(s)==='done');
  const due=replies.filter(s=>s.notifiedCompletion!==s.completion||now-(s.notifiedAt??0)>=REMINDER_MS);
  this.urgentQueue=this.sync(this.urgentQueue,urgent);
  this.replyQueue=this.sync(this.replyQueue,replies);
  let selected=states.find(s=>s.id===this.current);
  // Keep a complete attention card until its slot ends, unless its event was resolved.
  if(!selected||this.id(selected)!==this.identity||now>=this.until){
   const dueIds=new Set(due.map(s=>s.id));
   const replyId=this.replyQueue.find(id=>dueIds.has(id));
   if(urgent.length&&(!this.lastUrgent||!replyId)){
    const id=this.urgentQueue.shift();
    if(id)this.urgentQueue.push(id);
    selected=urgent.find(s=>s.id===id);
   }else if(replyId){
    selected=due.find(s=>s.id===replyId);
    this.replyQueue=this.replyQueue.filter(id=>id!==replyId);this.replyQueue.push(replyId);
   }else selected=undefined;
   this.current=selected?.id??'';this.identity=selected?this.id(selected):'';this.until=now+SLOT_MS;
   if(selected){
    this.lastUrgent=['question','error'].includes(kind(selected));
    if(kind(selected)==='done')notice={id:selected.id,notifiedCompletion:selected.completion,notifiedAt:now};
   }else this.lastUrgent=false;
  }
  if(!selected){
   const face=states.some(s=>s.working)?'work':states.some(s=>kind(s)==='wait')?'wait':'idle';
   return {card:{card:'background:'+face,face,text:labels[face],counts:counts(states),source:true,ttl:30}};
  }
  const face=kind(selected);
  return {card:{card:this.identity,face,text:(face==='question'?'? ':face==='error'?'! ':'')+selected.alias+': '+labels[face],counts:counts(states),source:true,ttl:30},notice};
 }
}
