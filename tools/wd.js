// Ayudante CDP para formularios React (Workday): teclea con Input.insertText y hace clic de ratón real. TAB=<trozo de URL>.
// node tools/wd.js <cmd> [args]; cmds: type <css> <texto> | click <css> | eval <js> | fields | key <k,..>
const PORT=9223, sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const tabs=(await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).filter(t=>t.type==='page');
 const tab=tabs.find(t=>t.url.includes(process.env.TAB||'/apply'));
 const ws=new WebSocket(tab.webSocketDebuggerUrl); let id=0; const p=new Map();
 ws.onmessage=e=>{const m=JSON.parse(e.data); if(m.id&&p.has(m.id)){const {res,rej}=p.get(m.id);p.delete(m.id);m.error?rej(new Error(m.error.message)):res(m.result);}};
 await new Promise(r=>ws.onopen=r);
 const send=(method,params={})=>new Promise((res,rej)=>{const i=++id;p.set(i,{res,rej});ws.send(JSON.stringify({id:i,method,params}))});
 const ev=async x=>{const r=await send('Runtime.evaluate',{expression:x,awaitPromise:true,returnByValue:true}); if(r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text); return r.result.value;};
 const click=async css=>{const r=await ev(`(()=>{const e=document.querySelector(${JSON.stringify(css)}); if(!e) return null; e.scrollIntoView({block:'center'}); const b=e.getBoundingClientRect(); return {x:b.x+b.width/2,y:b.y+b.height/2};})()`); if(!r) throw new Error('no '+css); await sleep(300); for(const type of ['mouseMoved','mousePressed','mouseReleased']) await send('Input.dispatchMouseEvent',{type,x:r.x,y:r.y,button:'left',clickCount:1}); await sleep(600);};
 const codes={ArrowDown:40,ArrowUp:38,Enter:13,Tab:9,Escape:27,Backspace:8};
 const key=async ks=>{for(const k of ks.split(',')){for(const type of ['rawKeyDown','keyUp']) await send('Input.dispatchKeyEvent',{type,key:k,code:k,windowsVirtualKeyCode:codes[k]}); if(k==='Enter') await send('Input.dispatchKeyEvent',{type:'char',text:'\r'}); await sleep(300);}};
 const [,,cmd,a,b]=process.argv;
 if(cmd==='type'){await click(a); await ev(`(()=>{const e=document.querySelector(${JSON.stringify(a)}); e.select&&e.select();})()`); await send('Input.insertText',{text:b}); await sleep(300);}
 if(cmd==='click') await click(a);
 if(cmd==='key') await key(a);
 if(cmd==='eval') console.log(JSON.stringify(await ev(a)));
 if(cmd==='fields') console.log(JSON.stringify(await ev(`[...document.querySelectorAll('input,textarea,button,[role=button]')].filter(e=>e.offsetParent!==null).map(e=>[e.tagName,e.type,e.id,e.getAttribute('data-automation-id'),(e.getAttribute('aria-label')||e.innerText||'').slice(0,50),(e.value||'').slice(0,30)].join('|'))`),null,1));
 ws.close();
})().catch(e=>{console.error(e.message);process.exit(1)});
