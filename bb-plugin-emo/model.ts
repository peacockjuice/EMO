export type Kind = 'question'|'error'|'done'|'work'|'wait'|'idle';
export type RecordState = {id:string;projectId:string;title:string;alias:string;status:string;working:boolean;pending:boolean;retry:boolean;queued:boolean;completion:number;completionAt:number;seen:number;dismissed:number;failure:number;failureRequestId:string;cursor:number;rootTurn:string;requestId:string};
export type Event = {seq:number;createdAt:number;type:string;scope:{kind:string;turnId?:string};data:Record<string,unknown>};
export const labels:Record<Kind,string>={question:'НУЖЕН ОТВЕТ',error:'ОШИБКА',done:'ХОД ЗАВЕРШЁН',work:'РАБОТАЕТ',wait:'ЖДЁТ ЗАПУСКА',idle:'ВСЁ СПОКОЙНО'};
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
 if(s.completion && s.completion!==s.seen)return 'done';
 if(s.retry)return 'wait';
 if(s.working)return 'work';
 if(s.queued||['starting','pending','stopping'].includes(s.status))return 'wait';
 return 'idle';
}
export function counts(states:RecordState[]){return [states.filter(s=>s.working).length,states.filter(s=>s.pending).length,states.filter(s=>s.status==='error'&&!s.retry&&s.dismissed!==s.failure).length,states.filter(s=>s.completion>0).length];}
export type Card={card:string;face:Kind;text:string;counts:number[];source:boolean;ttl:number};
export class Carousel{
 private queue:string[]=[];private current='';private until=0;private urgent=false;private completion=0;private identity='';
 next(states:RecordState[],now:number,source=true):Card{
  if(!source)return {card:'unknown',face:'idle',text:'СТАТУС BB НЕИЗВЕСТЕН',counts:[0,0,0,0],source:false,ttl:30};
  const old=states.find(s=>s.id===this.current);
  const incomingUrgent=states.some(s=>['question','error'].includes(kind(s)));
  if(this.completion && old && old.completion===this.completion && (now>=this.until || incomingUrgent)){old.seen=this.completion;this.completion=0;}
  const urgent=states.filter(s=>['question','error'].includes(kind(s)));
  const done=states.filter(s=>kind(s)==='done');
  const working=states.filter(s=>kind(s)==='work'||kind(s)==='wait');
  const candidates=urgent.length?urgent:done.length?done:working;
  const isUrgent=urgent.length>0;const ids=new Set(candidates.map(s=>s.id));
  this.queue=this.queue.filter(id=>ids.has(id));
  for(const s of candidates)if(!this.queue.includes(s.id))this.queue.push(s.id);
  if(!ids.has(this.current)||now>=this.until||(isUrgent&&!this.urgent)){
   // The existing ring stays in order when new urgent events arrive.
   const old=this.queue.indexOf(this.current);
   if(old>=0)this.queue.push(...this.queue.splice(0,old+1));
   this.current=this.queue[0]??'';this.until=now+8000;
  }
  this.urgent=isUrgent;
  const selected=candidates.find(s=>s.id===this.current);
  if(!selected)return {card:'idle',face:'idle',text:'BB: ВСЁ СПОКОЙНО',counts:counts(states),source:true,ttl:30};
  const k=kind(selected);
  const identity=selected.id+':'+k+':'+(k==='done'?selected.completion:k==='wait'&&selected.retry?'retry':0);
  if(identity!==this.identity){this.identity=identity;this.until=now+8000;}
  this.completion=k==='done'?selected.completion:0;
  const face=k==='done'&&now-selected.completionAt>30000?'idle':k;
  return {card:identity,face,text:(k==='question'?'? ':k==='error'?'! ':'')+selected.alias+': '+(k==='wait'&&selected.retry?'ЖДЁТ ПОВТОРА':labels[k]),counts:counts(states),source:true,ttl:30};
 }
}
