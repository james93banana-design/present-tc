// Run with Node 22+: node tests/verify_presentation_return.js report.html [chrome-path]
// Uses an isolated headless Chrome profile; never modifies the supplied report.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {spawn} = require('node:child_process');
const assert = require('node:assert/strict');
const report = process.argv[2];
if (!report) throw new Error('Supply an HTML report with at least 8 .brief-section pages.');
const chrome = process.argv[3] || process.env.CHROME_BIN ||
  (process.platform === 'darwin' ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' : 'google-chrome');
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'tc-return-'));
const child = spawn(chrome, ['--headless', '--disable-gpu', '--no-first-run',
  '--disable-background-networking', '--remote-debugging-port=0',
  '--user-data-dir=' + profile, 'about:blank'], {stdio: ['ignore', 'ignore', 'pipe']});
let startupError, startupLog = '';
child.stderr.on('data', data => { startupLog += data; });
child.on('error', e => { startupError = e; });
const pause = ms => new Promise(r => setTimeout(r, ms));
let ws;
(async () => {
  try {
    const active = path.join(profile, 'DevToolsActivePort');
    for (let i=0; i<120 && !fs.existsSync(active); i++) {
      if (startupError) throw startupError;
      if (child.exitCode !== null || child.signalCode) throw new Error('Chrome failed to start: ' + startupLog);
      await pause(100);
    }
    const port = fs.readFileSync(active, 'utf8').split('\n')[0];
    const targets = await (await fetch('http://127.0.0.1:' + port + '/json')).json();
    ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
    let sequence = 0;
    const pending = new Map(), errors = [];
    ws.onmessage = event => {
      const msg = JSON.parse(event.data);
      if (msg.method === 'Runtime.exceptionThrown') errors.push(msg.params);
      const item = pending.get(msg.id);
      if (item) { pending.delete(msg.id); clearTimeout(item.timer); msg.error ? item.reject(msg.error) : item.resolve(msg.result); }
    };
    const call = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++sequence;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout: ' + method)); }, 15000);
      pending.set(id, {resolve, reject, timer});
      ws.send(JSON.stringify({id, method, params}));
    });
    const js = async expression => {
      const r = await call('Runtime.evaluate', {expression, returnByValue:true, awaitPromise:true, userGesture:true});
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result.value;
    };
    const wait = async expr => {
      for (let i=0; i<100; i++) { if (await js(expr)) return; await pause(50); }
      throw new Error('Condition timed out: ' + expr);
    };
    const settle = async () => { await js('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))'); await pause(250); };
    await call('Page.enable'); await call('Runtime.enable'); await call('Network.enable');
    await call('Network.emulateNetworkConditions', {offline:true, latency:0, downloadThroughput:0, uploadThroughput:0});
    const state = target => js(`(()=>{const pages=[...document.querySelectorAll('.brief-section')],p=pages[${target-1}],r=p.getBoundingClientRect(),m=parseFloat(getComputedStyle(p).scrollMarginTop)||0,max=document.scrollingElement.scrollHeight-innerHeight;return {error:Math.abs(scrollY-Math.max(0,Math.min(max,scrollY+r.top-m))),allVisible:pages.every(p=>!p.hidden),active:[...document.querySelectorAll('aside nav a[aria-current]')].some(a=>a.hash==='#'+p.id),presenting:document.body.classList.contains('presentation')}})()`);
    const enter = async page => {
      await js(`document.querySelectorAll('.brief-section')[${page-1}].scrollIntoView({behavior:'instant',block:'start'})`);
      await settle(); await js('document.querySelector("#sidebar-present").click()'); await settle();
      assert.match(await js('document.querySelector("#page-number").textContent'), new RegExp('^'+page+' /'));
    };
    for (const [name, from, target, mode, lang, fallback, width] of [
      ['same page',6,6,'button','cn',false,1600],
      ['changed page',6,8,'button','cn',false,1600],
      ['Escape',6,6,'escape','cn',false,1600],
      ['native fullscreen exit',6,7,'native','cn',false,1600],
      ['English',6,8,'escape','en',false,1600],
      ['fullscreen denied',6,8,'button','cn',true,1600],
      ['compact window',6,7,'escape','cn',false,1080],
      ['cover',1,1,'button','cn',false,1600],
      ['rapid reentry',6,7,'rapid','cn',true,1600],
    ]) {
      await call('Emulation.setDeviceMetricsOverride', {width,height:width===1080?800:1050,deviceScaleFactor:1,mobile:false});
      await call('Page.navigate', {url:pathToFileURL(path.resolve(report)).href});
      await wait('document.readyState==="complete" && document.querySelectorAll(".brief-section").length>=8');
      await js(`document.fonts.ready.then(()=>{if(window.sumoSetLanguage)window.sumoSetLanguage(${JSON.stringify(lang)});else document.documentElement.dataset.language=${JSON.stringify(lang)}})`);
      if (fallback) await js('document.documentElement.requestFullscreen=()=>Promise.reject(new Error("test fullscreen rejection"))');
      await settle(); await enter(from);
      if (target!==from) await js(`document.querySelectorAll('aside nav a').forEach(a=>{if(a.hash==='#'+document.querySelectorAll('.brief-section')[${target-1}].id)a.click()})`);
      await settle();
      if (mode==='escape') {
        await call('Input.dispatchKeyEvent', {type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
        await call('Input.dispatchKeyEvent', {type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
      } else if (mode==='native') {
        assert.equal(await js('!!document.fullscreenElement'),true,'Native fullscreen test requires real fullscreen');
        await js('document.exitFullscreen()');
      } else if (mode==='rapid') {
        await js(`document.querySelector('#leave-present').click();document.querySelector('#sidebar-present').click();document.querySelector('#next-page').click()`);
        await settle();
        assert.match(await js('document.querySelector("#page-number").textContent'), /^8 \/ /);
        await js('document.querySelector("#leave-present").click()');
      } else await js('document.querySelector("#leave-present").click()');
      await wait('!document.body.classList.contains("presentation") && !document.fullscreenElement');
      await settle();
      const expected = mode==='rapid'?8:target;
      const end = await state(expected);
      assert.ok(end.error<3 && end.allVisible && end.active && !end.presenting, JSON.stringify(end));
      // Reenter without scrolling: verifies the exit's actual reading position.
      await js('document.querySelector("#sidebar-present").click()'); await settle();
      assert.match(await js('document.querySelector("#page-number").textContent'), new RegExp('^'+expected+' /'));
      await js('document.querySelector("#leave-present").click()'); await settle();
      console.log('PASS:',name);
    }
    assert.deepEqual(errors, []);
  } finally {
    if (ws) ws.close();
    if (child.exitCode===null) { child.kill(); await Promise.race([new Promise(r=>child.once('exit',r)),pause(3000)]); }
    fs.rmSync(profile, {recursive:true,force:true});
  }
})().catch(e => { console.error(e); process.exitCode=1; });
