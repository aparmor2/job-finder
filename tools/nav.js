// Controla el Brave abierto con --remote-debugging-port=9223 hablando CDP directamente.
// Sin Playwright: Playwright fuerza modo claro (prefers-color-scheme) en todas las pestañas al conectarse.
// Uso: node tools/nav.js <accion> [args]
//   acciones: shot | goto <url> | click <selector|texto> | realclick <selector> | fill <selector> <texto> | key <tecla> | text | fields | upload <selector> <ruta> | eval <js>
// TAB=<trozo de URL> elige la pestaña; si no, la primera. SHOT=<ruta> guarda captura (por defecto shot.png).
const fs = require('fs');
const PORT = 9223;

async function pickTab() {
  const tabs = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json())
    .filter(t => t.type === 'page' && !/^(devtools|chrome|brave|about)/.test(t.url));
  const tab = (process.env.TAB && tabs.find(t => t.url.includes(process.env.TAB))) || tabs[0];
  if (!tab) throw new Error('No hay pestañas abiertas');
  return tab;
}

function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const { res, rej } = pending.get(m.id);
      pending.delete(m.id);
      m.error ? rej(new Error(m.error.message)) : res(m.result);
    }
  };
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = ++id;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  return new Promise((res, rej) => { ws.onopen = () => res({ send, close: () => ws.close() }); ws.onerror = rej; });
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const [, , action, a1, a2] = process.argv;
  const tab = await pickTab();
  const cdp = await connect(tab.webSocketDebuggerUrl);
  const evaluate = async expr => {
    const r = await cdp.send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  };
  const waitLoad = async () => {
    for (let i = 0; i < 60; i++) {
      await sleep(250);
      try { if (await evaluate('document.readyState') === 'complete') return; } catch { }
    }
  };
  // Busca por selector CSS o, si no lo parece, por texto visible (el elemento más pequeño que lo contenga)
  const findEl = q => `(() => {
    const q = ${JSON.stringify(q)};
    if (/^[.#\\[]|^\\w+[\\[.#:]/.test(q)) return document.querySelector(q);
    const vis = e => e.offsetParent !== null;
    const cands = [...document.querySelectorAll('a,button,input[type=submit],input[type=button],label,span,td,div,li,img')]
      .filter(e => vis(e) && ((e.innerText || e.value || e.title || e.alt || '').includes(q)));
    cands.sort((a, b) => (a.innerText || '').length - (b.innerText || '').length);
    return cands[0] || null;
  })()`;

  if (action === 'goto') { await cdp.send('Page.navigate', { url: a1 }); await waitLoad(); }
  if (action === 'click') {
    const ok = await evaluate(`(() => { const e = ${findEl(a1)}; if (!e) return false; e.scrollIntoView({block:'center'}); e.click(); return true; })()`);
    if (!ok) throw new Error('No encontrado: ' + a1);
    await sleep(1000); await waitLoad();
  }
  if (action === 'fill') {
    const ok = await evaluate(`(() => { const e = ${findEl(a1)}; if (!e) return false; e.focus();
      const proto = e.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto, 'value').set.call(e, ${JSON.stringify(a2 ?? '')});
      e.dispatchEvent(new Event('input', {bubbles:true})); e.dispatchEvent(new Event('change', {bubbles:true})); e.blur(); return true; })()`);
    if (!ok) throw new Error('No encontrado: ' + a1);
  }
  if (action === 'upload') {
    const { root } = await cdp.send('DOM.getDocument');
    const { nodeId } = await cdp.send('DOM.querySelector', { nodeId: root.nodeId, selector: a1 });
    await cdp.send('DOM.setFileInputFiles', { nodeId, files: [require('path').resolve(a2)] });
  }
  // Clic "de verdad" (evento de ratón del navegador): abre el autocompletado de contraseñas guardadas
  if (action === 'realclick') {
    const r = await evaluate(`(() => { const e = ${findEl(a1)}; if (!e) return null; e.scrollIntoView({block:'center'}); const b = e.getBoundingClientRect(); return {x: b.x + b.width/2, y: b.y + b.height/2}; })()`);
    if (!r) throw new Error('No encontrado: ' + a1);
    await cdp.send('Page.bringToFront');
    for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased'])
      await cdp.send('Input.dispatchMouseEvent', { type, x: r.x, y: r.y, button: 'left', clickCount: 1 });
    await sleep(1000);
  }
  // Pulsa teclas: key ArrowDown,Enter
  if (action === 'key') {
    const codes = { ArrowDown: 40, ArrowUp: 38, Enter: 13, Tab: 9, Escape: 27 };
    for (const k of a1.split(',')) {
      for (const type of ['rawKeyDown', 'keyUp'])
        await cdp.send('Input.dispatchKeyEvent', { type, key: k, code: k, windowsVirtualKeyCode: codes[k] });
      if (k === 'Enter') await cdp.send('Input.dispatchKeyEvent', { type: 'char', text: '\r' });
      await sleep(400);
    }
    await sleep(1000); await waitLoad();
  }
  if (action === 'eval')console.log(JSON.stringify(await evaluate(a1), null, 0));
  if (action === 'text') console.log((await evaluate('document.body.innerText')).slice(0, 6000));
  if (action === 'fields') console.log(JSON.stringify(await evaluate(`[...document.querySelectorAll('input,select,textarea,button,a[role=button]')]
    .filter(e => e.offsetParent !== null).map(e => ({ tag: e.tagName, type: e.type, name: e.name, id: e.id,
      label: e.getAttribute('aria-label') || e.placeholder || (e.labels && e.labels[0] && e.labels[0].innerText) || e.innerText?.slice(0, 40), value: e.value?.slice(0, 40) }))`), null, 0));

  await sleep(800);
  const out = process.env.SHOT || 'shot.png';
  if (out !== '-') {
    const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(out, Buffer.from(data, 'base64'));
  }
  console.log('URL:', await evaluate('location.href'), '| captura:', out);
  cdp.close(); // solo desconecta, no cierra Brave
})().catch(e => { console.error(e.message); process.exit(1); });
