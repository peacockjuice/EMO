import {readFile} from 'node:fs/promises';
import {homedir} from 'node:os';
import {createHmac} from 'node:crypto';
import {setTimeout as sleep} from 'node:timers/promises';
import {defineRpcContract,type BbPluginApi} from '@get-bb/plugin-sdk';
import {z} from 'zod';
import {Carousel,eventsInto,kind,type RecordState,type Event} from './model.ts';
import {Transport,type Receipt} from './transport.ts';

export type Status={sourceReady:boolean;delivery:string;error:string;receipt:Receipt|null;projects:{id:string;name:string;selected:boolean}[];threads:(RecordState&{kind:string;excluded:boolean})[];url:string};
export const rpcContract=defineRpcContract({
 status:{input:z.null(),output:z.custom<Status>()},
 projects:{input:z.object({ids:z.array(z.string()).max(200)}),output:z.object({ok:z.boolean()})},
 exclude:{input:z.object({id:z.string(),excluded:z.boolean()}),output:z.object({ok:z.boolean()})},
 dismiss:{input:z.object({id:z.string()}),output:z.object({ok:z.boolean()})},
});
const TYPES=['turn/started','turn/completed','system/thread/interrupted','client/turn/requested'] as const;
export default async function plugin(bb:BbPluginApi){
 const settings=bb.settings.define({
  url:{type:'string',label:'Адрес EMO',default:'http://192.168.1.43'},
  notifyKey:{type:'string',label:'Ключ уведомлений',secret:true},
  projectIds:{type:'string',label:'Проекты (ID в JSON)',default:'[]'},
 });
 let config=await settings.get();
 const records=new Map<string,RecordState>();const dirty=new Set<string>();const revisions=new Map<string,number>();
 let excluded=new Set(await bb.storage.kv.get<string[]>('excluded')??[]);
 let projects:{id:string;name:string}[]=[];let nextAlias=await bb.storage.kv.get<number>('nextAlias')??1;
 let connected=false,ready=false,reconcile=true,disposed=false;let delivery='waiting',error='';let receipt:Receipt|null=null;
 const epoch=Math.max(Date.now(),(await bb.storage.kv.get<number>('epoch')??0)+1);await bb.storage.kv.set('epoch',epoch);
 const transport=new Transport(epoch);const carousel=new Carousel();
 const failures=new Map<string,string>();let fullVersion=0;
 function selected(){const value:unknown=JSON.parse(config.projectIds);if(!Array.isArray(value)||value.some(x=>typeof x!=='string'))throw Error('Выберите проекты EMO');return new Set<string>(value);}
 function mark(id:string){dirty.add(id);revisions.set(id,(revisions.get(id)??0)+1);}
 function full(){fullVersion++;reconcile=true;ready=false;}
 function publish(){if(!disposed)bb.realtime.publish('changed',{});}
 function status():Status{return {sourceReady:ready&&connected&&!reconcile&&dirty.size===0,delivery,error,receipt,projects:projects.map(p=>({...p,selected:selected().has(p.id)})),threads:[...records.values()].map(s=>({...s,kind:kind(s),excluded:excluded.has(s.id)})),url:config.url};}
 settings.onChange((next)=>{config=next;full();publish();});
 for(const name of ['thread.created','thread.active','thread.idle','thread.failed','thread.archived','thread.unarchived','thread.deleted','interaction.pending','experimental_thread.read','experimental_thread.parentChanged'] as const){
  bb.events.on(name,e=>{mark(e.thread.id);});
 }
 bb.events.on('turn.failed',e=>{failures.set(e.threadId,e.requestId);mark(e.threadId);});
 for(const name of ['message.queued','message.dispatched','message.cancelled'] as const)bb.events.on(name,e=>mark(e.entry.threadId));
 bb.onDispose(()=>{disposed=true;});
 async function provision(){
  const root=await readFile(homedir()+'/.config/emo/update.key');
  if(root.length!==32)throw Error('Ключ обновления должен содержать 32 байта');
  await settings.experimental_set({notifyKey:createHmac('sha256',root).update('emo.bb.notifications.v1').digest('hex')});
  return {ok:true};
 }
 async function setProjects(ids:string[]){
  const known=new Set((await bb.sdk.projects.list()).map(p=>p.id));
  if(ids.some(id=>!known.has(id)))throw Error('Неизвестный проект');
  await settings.experimental_set({projectIds:JSON.stringify([...new Set(ids)])});return {ok:true};
 }
 async function setExcluded(id:string,value:boolean){
  if(value)excluded.add(id);else excluded.delete(id);
  await bb.storage.kv.set('excluded',[...excluded]);publish();return {ok:true};
 }
 async function dismiss(id:string){const s=records.get(id);if(s){s.dismissed=s.failure;mark(id);await bb.storage.kv.set('thread:'+id,s);}publish();return {ok:true};}
 bb.rpc.register(rpcContract,{status:async()=>status(),projects:({ids})=>setProjects(ids),exclude:({id,excluded})=>setExcluded(id,excluded),dismiss:({id})=>dismiss(id)});
 bb.cli.register({name:'emo',summary:'Состояния сессий на OLED робота EMO',commands:[
  {name:'status',summary:'Статус доставки и сессий',usage:'bb emo status [--json]'},
  {name:'provision',summary:'Настроить производный ключ из локального update.key',usage:'bb emo provision'},
  {name:'projects',summary:'Выбрать проекты',usage:'bb emo projects <project-id>...'},
 ],async run(argv){
  const [cmd,...args]=argv.filter(a=>a!=='--json');
  if(cmd==='provision')return {exitCode:0,stdout:JSON.stringify(await provision())};
  if(cmd==='projects')return {exitCode:0,stdout:JSON.stringify(await setProjects(args))};
  if(cmd==='status'||!cmd){const value=status();return {exitCode:0,stdout:JSON.stringify({...value,threads:value.threads.slice(0,100),totalThreads:value.threads.length})};}
  return {exitCode:1,stderr:'Команды: status, provision, projects'};
 }});
 bb.onInstall(async()=>{await setProjects((await bb.sdk.projects.list()).map(p=>p.id));});
 type Row=Awaited<ReturnType<BbPluginApi['sdk']['threads']['list']>>[number];
 function eligible(row:Row){return selected().has(row.projectId)&&!row.parentThreadId&&!row.archivedAt&&!row.deletedAt&&row.visibility==='visible';}
 async function refresh(id:string,signal:AbortSignal,seed?:Row,bootstrap=false){
  const rev=revisions.get(id)??0;const version=fullVersion;
  const row=seed??(await bb.sdk.threads.list({threadIds:[id],includeHidden:true,signal}))[0];
  if(!row||!eligible(row)){if(version===fullVersion&&(revisions.get(id)??0)===rev){records.delete(id);dirty.delete(id);}return;}
  const saved=records.get(id)??await bb.storage.kv.get<RecordState>('thread:'+id);
  const prefix=(projects.find(p=>p.id===row.projectId)?.name??'BB').toUpperCase().replace(/[^A-ZА-ЯЁ0-9]/g,'').slice(0,3)||'BB';
  const state:RecordState=saved?{...saved}:{id,projectId:row.projectId,title:'',alias:prefix+'#'+nextAlias++,status:'idle',working:false,pending:false,retry:false,queued:false,completion:0,completionAt:0,seen:0,dismissed:0,failure:0,failureRequestId:'',cursor:0,rootTurn:'',requestId:''};
  const interactions=row.hasPendingInteraction?await bb.sdk.threads.interactions.list({threadId:id,signal}):[];
  const queue=row.queuedWork!=='none'||row.status==='error'?await bb.sdk.threads.queue.list({threadId:id,signal}):[];
  let events:Event[]=[];
  if(state.cursor){
   let after=state.cursor;
   while(true){
    const batch=await bb.sdk.threads.events.list({threadId:id,types:TYPES,afterSeq:String(after),limit:'100',order:'asc',signal});
    events.push(...batch as Event[]);if(batch.length<100)break;after=batch[batch.length-1].seq;
    if(events.length>2000){
     events=await bb.sdk.threads.events.list({threadId:id,types:TYPES,limit:'100',order:'desc',signal}) as Event[];
     state.cursor=0;state.rootTurn='';state.completion=0;bootstrap=true;break;
    }
   }
  }else{
   events=await bb.sdk.threads.events.list({threadId:id,types:TYPES,limit:'100',order:'desc',signal}) as Event[];
  }
  if(disposed||signal.aborted||version!==fullVersion||(revisions.get(id)??0)!==rev){mark(id);return;}
  eventsInto(state,events,bootstrap);
  state.title=(row.title??row.titleFallback??'Без названия').slice(0,160);state.projectId=row.projectId;state.status=row.status;
  state.pending=interactions.some(x=>x.status==='pending');
  state.working=row.status==='active'||row.activity.activeBackgroundAgentCount>0||row.activity.activeBackgroundCommandCount>0||row.activity.activeWorkflowCount>0;
  state.queued=queue.length>0;
  if(failures.has(id))state.failureRequestId=failures.get(id)!;
  if(row.status==='error'&&!state.failure)state.failure=row.latestAttentionAt||row.updatedAt;
  state.retry=queue.some(q=>q.payload.kind==='retry'&&q.payload.retryOfTurnRequestId===state.failureRequestId&&q.state!=='failed_exhausted');
  if((row.lastReadAt??0)>=state.completionAt)state.completion=0;
  if(row.status!=='error'){state.failure=0;state.dismissed=0;failures.delete(id);}
  records.set(id,state);dirty.delete(id);
  await bb.storage.kv.set('thread:'+id,state);await bb.storage.kv.set('nextAlias',nextAlias);
 }
 bb.background.service('monitor',{async start(signal){
  const unsub=bb.sdk.subscribe({event:'thread:changed',callback:e=>{
   if(e.changes.includes('events-appended')&&e.changes.length===1&&e.metadata?.eventTypes&&!e.metadata.eventTypes.some(t=>(TYPES as readonly string[]).includes(t))&&!e.metadata.backgroundActivityChanged)return;
   if(e.id)mark(e.id);else full();
  }});
  const connection=bb.sdk.subscribe({event:'realtime:connection',callback:e=>{connected=e.state==='connected';if(connected)full();else ready=false;publish();}});
  let nextRecovery=0,lastSend=0,lastFingerprint='',lastPublish=0;let sendTask:Promise<void>|null=null;let sendBackoff=1000,nextSend=0;
  try{
   while(!signal.aborted){
    const now=Date.now();
    try{
     if(reconcile&&connected&&now>=nextRecovery){
      const version=fullVersion;projects=(await bb.sdk.projects.list()).map(p=>({id:p.id,name:p.name}));
      const rows:Row[]=[];
      for(const projectId of selected())for(let offset=0;;offset+=100){
       const page=await bb.sdk.threads.list({projectId,hasParent:false,limit:100,offset,signal});rows.push(...page);if(page.length<100)break;
      }
      const ids=new Set(rows.filter(eligible).map(r=>r.id));for(const id of records.keys())if(!ids.has(id))records.delete(id);
      for(const row of rows)if(eligible(row))await refresh(row.id,signal,dirty.has(row.id)?undefined:row,true);
      if(version===fullVersion){reconcile=false;ready=true;}
     }
     if(connected&&!reconcile){for(const id of [...dirty].slice(0,8))await refresh(id,signal);}
    }catch(e){if(signal.aborted)break;ready=false;reconcile=true;nextRecovery=Date.now()+5000;error='Не удалось сверить состояния BB';bb.log.warn(error);}
    const source=connected&&ready&&!reconcile&&dirty.size===0;
    const states=[...records.values()].filter(s=>!excluded.has(s.id));
    const seenBefore=new Map(states.map(s=>[s.id,s.seen]));
    const card=carousel.next(states,Date.now(),source);
    for(const s of states)if(seenBefore.get(s.id)!==s.seen)await bb.storage.kv.set('thread:'+s.id,s);
    const fingerprint=JSON.stringify(card);
    if(!sendTask&&config.notifyKey&&Date.now()>=nextSend&&(fingerprint!==lastFingerprint||Date.now()-lastSend>=10000)){
     const sentFingerprint=fingerprint;const currentConfig=config;
     sendTask=transport.send(currentConfig.url,currentConfig.notifyKey!,card,signal).then(result=>{
      receipt=result;delivery=result.status??'unknown';error='';lastFingerprint=sentFingerprint;lastSend=Date.now();sendBackoff=1000;nextSend=lastSend+300;
     },()=>{if(!signal.aborted){delivery='offline';error='Нет подтверждения от EMO. Проверьте питание, адрес и ключ';nextSend=Date.now()+sendBackoff;sendBackoff=Math.min(15000,sendBackoff*2);}}).finally(()=>{sendTask=null;publish();});
    }else if(!config.notifyKey)delivery='needs-key';
    if(now-lastPublish>=1000){publish();lastPublish=now;}
    await sleep(250,undefined,{signal});
   }
  }catch(e){if(!signal.aborted)throw e;}finally{unsub();connection();if(sendTask)await sendTask;connected=false;ready=false;}
 }});
}
