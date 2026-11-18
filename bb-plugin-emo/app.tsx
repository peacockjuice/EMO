import { useCallback, useEffect, useRef, useState } from "react";
import { definePluginApp, useBbNavigate, useRealtime, useRealtimeConnectionState, useRpc } from "@get-bb/plugin-sdk/app";
import type { rpcContract, Status } from "./server";
import { counts } from "./model";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

const kinds:Record<string,string>={question:"Нужен ответ",error:"Ошибка",done:"Есть ответ",work:"Работает",wait:"Ждёт запуска",idle:"Спокойно"};
const deliveries:Record<string,string>={live:"Экран получает уведомления",mode_disabled:"На роботе выбран другой режим",unknown:"Состояния BB уточняются",offline:"Нет подтверждения от робота",waiting:"Подключение к роботу","needs-key":"Нужна настройка ключа"};
function EmoPage(){
 const rpc=useRpc<typeof rpcContract>();const navigate=useBbNavigate();const connection=useRealtimeConnectionState();
 const [data,setData]=useState<Status|null>(null);const [error,setError]=useState("");const [busy,setBusy]=useState(false);const pending=useRef(false);
 const report=useCallback((e:unknown)=>setError(e instanceof Error?e.message:String(e)),[]);
 const refresh=useCallback(()=>{
  if(pending.current)return;pending.current=true;
  rpc.call("status",null).then(setData,report).finally(()=>{pending.current=false;});
 },[rpc,report]);
 useEffect(refresh,[refresh,connection]);useRealtime("changed",refresh);
 async function change(action:()=>Promise<unknown>){setBusy(true);setError("");try{await action();refresh();}catch(e){report(e);}finally{setBusy(false);}}
 if(!data)return <div className="p-6" role="status">{error||"Подключение к EMO…"}</div>;
 const totals=counts(data.threads.filter(s=>!s.excluded));
 const order:Record<string,number>={question:0,error:1,done:2,work:3,wait:4,idle:5};
 const threads=[...data.threads].sort((a,b)=>Number(a.excluded)-Number(b.excluded)||(order[a.kind]-order[b.kind])||a.alias.localeCompare(b.alias));
 return <main className="mx-auto max-w-4xl space-y-6 p-6">
  <header className="flex flex-wrap items-start justify-between gap-4">
   <div><h1 className="text-2xl font-semibold">EMO</h1><p className="mt-1 text-sm text-muted-foreground">Сессии BB на экране робота</p></div>
   <Button variant="outline" onClick={()=>navigate.openUrl(data.url)}>Панель робота</Button>
  </header>
  <section className="rounded-lg border p-4" aria-label="Подключение">
   <p className="font-medium" role="status">{connection!=="connected"?"Нет связи этой страницы с BB":deliveries[data.delivery]??data.delivery}</p>
   {!data.sourceReady&&<p className="mt-1 text-sm text-muted-foreground">Сверяю состояния сессий. Прежняя сводка не считается актуальной.</p>}
   {data.delivery==="mode_disabled"&&<p className="mt-1 text-sm text-muted-foreground">В панели робота выберите «Уведомления BB». После перезагрузки режим нужно включить снова.</p>}
   {data.delivery==="needs-key"&&<p className="mt-1 text-sm text-muted-foreground">На Mac с ключом обновления выполните bb emo provision.</p>}
   {(error||data.error)&&<p className="mt-2 text-sm text-destructive" role="alert">{error||data.error}</p>}
  </section>
  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{["▶ Работают","? Нужен ответ","! Ошибки","● Не прочитано"].map((label,i)=><div key={label} className="rounded-lg border p-3"><p className="text-sm text-muted-foreground">{label}</p><p className="mt-1 text-2xl tabular-nums">{data.sourceReady?totals[i]:"—"}</p></div>)}</div>
  <details className="rounded-lg border p-4"><summary className="cursor-pointer font-medium">Проекты · {data.projects.filter(p=>p.selected).length}</summary>
   <p className="my-3 text-sm text-muted-foreground">Новые основные сессии выбранных проектов появятся автоматически. Архивные и скрытые сессии не учитываются.</p>
   <div className="flex flex-wrap gap-4">{data.projects.map(p=><label key={p.id} className="flex items-center gap-2 text-sm"><Checkbox checked={p.selected} disabled={busy} onCheckedChange={checked=>change(()=>rpc.call("projects",{ids:data.projects.filter(x=>x.id===p.id?!!checked:x.selected).map(x=>x.id)}))}/>{p.name}</label>)}</div>
  </details>
  <section aria-label="Сессии"><h2 className="mb-3 text-lg font-medium">Сессии</h2>
   {!threads.length&&<p className="rounded-lg border p-4 text-muted-foreground">Сессий пока нет. Выберите проект выше.</p>}
   <ul className="divide-y rounded-lg border">{threads.map(s=><li key={s.id} className="flex flex-wrap items-center gap-3 p-3">
    <label className="flex items-center gap-2"><Checkbox aria-label={`Показывать ${s.alias}`} checked={!s.excluded} disabled={busy} onCheckedChange={checked=>change(()=>rpc.call("exclude",{id:s.id,excluded:!checked}))}/><span className="min-w-16 font-mono text-xs">{s.alias}</span></label>
    <button className="min-w-0 flex-1 text-left hover:underline" onClick={()=>navigate.toThread(s.id)}><span className="block truncate">{s.title}</span><span className="text-xs text-muted-foreground">{s.excluded?"Исключена":kinds[s.kind]}{!s.excluded&&s.working&&s.pending?" · Работа продолжается":""}{s.retry?" · Ожидает повтора":""}</span></button>
    {s.status==="error"&&s.failure!==s.dismissed&&<Button size="sm" variant="ghost" disabled={busy} onClick={()=>change(()=>rpc.call("dismiss",{id:s.id}))}>Скрыть ошибку</Button>}
   </li>)}</ul>
   <p className="mt-3 text-xs text-muted-foreground">Вопрос остаётся до ответа. Чтение сессии снимает напоминание «Есть ответ». Показ на роботе не помечает ответ прочитанным.</p>
  </section>
 </main>;
}
export default definePluginApp(app=>{app.slots.navPanel({id:"emo",title:"EMO",icon:"Bot",path:"status",component:EmoPage});});
