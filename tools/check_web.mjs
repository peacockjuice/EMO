// Execute the shipped page JS against a small DOM model; optional live HTTP via BMO_TEST_URL.
// This verifies handlers/state, not CSS layout or browser rendering.
import fs from "node:fs";
import vm from "node:vm";
import assert from "node:assert/strict";
const root=new URL("../",import.meta.url);
const html=fs.readFileSync(new URL("index.html",root),"utf8");
const elements=[];
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.attrs={};this.hidden=false;elements.push(this)}
 append(...nodes){this.children.push(...nodes)}
 setAttribute(k,v){this.attrs[k]=v}
}
const nodes=Object.fromEntries(["status","retry","modes","speech","scenes","grid","invert"].map(id=>[id,new Element("div")]));
const document={hidden:false,getElementById:id=>nodes[id],createElement:tag=>new Element(tag),querySelectorAll:selector=>elements.filter(e=>selector===".face img"?e.tag==="img":e.dataset.mood)};
let mood="auto",inverted=false,fail=false;
const calls=[];
const base=process.env.BMO_TEST_URL;
const context=vm.createContext({document,AbortController,setTimeout,clearTimeout,setInterval:()=>0,fetch:async(path,options)=>{
 calls.push(path);
 if(fail){fail=false;throw Error("offline")}
 if(base)return fetch(base+path,options);
 if(path.startsWith("/set?e="))mood=decodeURIComponent(path.split("=")[1]);
 if(path.startsWith("/invert?value="))inverted=path.endsWith("=1");
 return {ok:true,json:async()=>({ok:true,mood,invert:inverted})};
}});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
async function idle(){const deadline=Date.now()+10000;while(vm.runInContext("busy",context)){assert(Date.now()<deadline,"request timed out");await new Promise(r=>setTimeout(r,10))}}
await idle();assert.equal(nodes.scenes.children.length,6);assert.equal(nodes.grid.children.length,33);assert.equal(nodes.modes.children.length,1);assert.equal(nodes.speech.children.length,7);
assert(nodes.speech.children.every(b=>b.className==="face"&&b.children[0].tag==="img"&&b.children[0].src.startsWith("data:image/png;base64,")));
assert.equal(new Set(nodes.speech.children.slice(3).map(b=>b.children[0].src)).size,4,"Syllable previews must show different mouth shapes");
for(const button of [...nodes.grid.children,...nodes.modes.children,...nodes.speech.children,...nodes.scenes.children]){
 button.onclick();await idle();assert.equal(button.attrs["aria-pressed"],"true",button.dataset.mood);
 assert.equal(elements.filter(e=>e.attrs["aria-pressed"]==="true").length,1);
}
// Auto scene status must not steal selected-card focus; manual hold keeps its card.
vm.runInContext('mark({mood:"auto",invert:false,feeling:"curious",scene:"scene_curious",phase:"scene"})',context);
assert.equal(nodes.modes.children[0].attrs["aria-pressed"],"true");
assert(nodes.status.textContent.includes("Интерес")&&nodes.status.textContent.includes("Что там?"));
vm.runInContext('mark({mood:"scene_grumpy",invert:false,feeling:null,scene:"scene_grumpy",phase:"hold"})',context);
assert.equal(nodes.scenes.children[5].attrs["aria-pressed"],"true");
assert(nodes.status.textContent.includes("Завершено"));
// Rapid taps are serialized and the latest selection wins.
nodes.grid.children[0].onclick();nodes.grid.children[12].onclick();nodes.grid.children[29].onclick();await idle();
assert.equal(nodes.grid.children[29].attrs["aria-pressed"],"true");
fail=true;await vm.runInContext("poll()",context);assert.equal(nodes.retry.hidden,false);assert.equal(nodes.status.className,"error");
await nodes.retry.onclick();await idle();assert.equal(nodes.retry.hidden,true);
// A failed selection must survive until retry; a later tap must supersede it.
fail=true;nodes.grid.children[0].onclick();await idle();
assert.equal(nodes.retry.hidden,false);
await nodes.retry.onclick();await idle();
assert.equal(nodes.grid.children[0].attrs["aria-pressed"],"true","retry lost failed selection");
fail=true;nodes.grid.children[1].onclick();nodes.grid.children[2].onclick();await idle();
await nodes.retry.onclick();await idle();
assert.equal(nodes.grid.children[2].attrs["aria-pressed"],"true","retry ignored latest selection");
nodes.modes.children[0].onclick();await idle();
// Inversion is independent of the selected mood, reflected by every thumbnail.
nodes.invert.checked=true;nodes.invert.onchange();await idle();
assert.equal(nodes.invert.checked,true);assert.equal(nodes.modes.children[0].attrs["aria-pressed"],"true");
assert(elements.filter(e=>e.tag==="img").every(e=>e.className==="inverted"));
nodes.grid.children[5].onclick();await idle();assert.equal(nodes.invert.checked,true);
fail=true;nodes.invert.checked=false;nodes.invert.onchange();await idle();assert.equal(nodes.retry.hidden,false);
await nodes.retry.onclick();await idle();assert.equal(nodes.invert.checked,false);
assert(elements.filter(e=>e.tag==="img").every(e=>e.className===""));
// Queue a face selection and inversion together; neither should be lost.
nodes.grid.children[0].onclick();nodes.invert.checked=true;nodes.invert.onchange();await idle();
assert.equal(nodes.grid.children[0].attrs["aria-pressed"],"true");assert.equal(nodes.invert.checked,true);
nodes.invert.checked=false;nodes.invert.onchange();await idle();
nodes.modes.children[0].onclick();await idle();
const report=[{name:base?"Live page handlers: 33 cards + auto + 7 speech modes + 6 scenes":"Page handlers: 33 cards + auto + 7 speech modes + 6 scenes",status:"passed"},{name:"Rapid selections, inversion, exclusive active state, failure and retry",status:"passed"},{name:"Visual browser rendering",status:"skipped",message:"Computer-use browser host unavailable"}];
fs.writeFileSync(new URL("preview/web-tests.json",root),JSON.stringify(report,null,2));
console.log("PASS:",base?"live":"mock","handlers, 33 cards, auto, 7 speech modes + 6 scenes, rapid taps, error recovery;",calls.length,"requests");
