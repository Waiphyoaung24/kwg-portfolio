import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
const dir=await fs.mkdtemp(path.join(os.tmpdir(),'kwg-dashboard-ui-'));
const origin=process.env.DASHBOARD_ORIGIN||'http://127.0.0.1:4327';
const executable=process.env.DASHBOARD_BROWSER||(process.platform==='darwin'?'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome':'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe');
const browser=spawn(executable,['--headless=new','--disable-gpu','--no-first-run','--remote-debugging-port=0',`--user-data-dir=${path.join(dir,'profile')}`,'about:blank'],{windowsHide:true,stdio:['ignore','ignore','inherit']});
let ws;const sleep=ms=>new Promise(r=>setTimeout(r,ms));
try{
 let port;for(let i=0;i<60;i++){try{port=(await fs.readFile(path.join(dir,'profile','DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{await sleep(200);}}
 if(!port)throw Error('The browser did not expose a debugging port.');
 const targets=await(await fetch(`http://127.0.0.1:${port}/json`)).json();ws=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);await Promise.race([new Promise((r,j)=>{ws.addEventListener('open',r,{once:true});ws.addEventListener('error',j,{once:true});}),sleep(10000).then(()=>{throw Error('Browser connection timed out');})]);let id=0;const pending=new Map();ws.addEventListener('message',e=>{const d=JSON.parse(e.data);if(d.id){const p=pending.get(d.id);pending.delete(d.id);d.error?p.reject(Error(d.error.message)):p.resolve(d.result);}});const send=(method,params={})=>new Promise((resolve,reject)=>{const next=++id;const timer=setTimeout(()=>{pending.delete(next);reject(Error('Browser command timed out: '+method));},10000);pending.set(next,{resolve:v=>{clearTimeout(timer);resolve(v);},reject:e=>{clearTimeout(timer);reject(e);}});ws.send(JSON.stringify({id:next,method,params}));});
 const evaluate=async expression=>{if(expression.includes('.click();'))expression='(async()=>{'+expression.replaceAll('.click();','.click();await new Promise(r=>setTimeout(r,0));').replaceAll('.requestSubmit();','.requestSubmit();await new Promise(r=>setTimeout(r,0));')+'})()';const r=await send('Runtime.evaluate',{expression,userGesture:true,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const wait=async expression=>{for(let i=0;i<60;i++){if(await evaluate(expression))return;await sleep(100);}throw Error('Timed out: '+expression);};
 const runtimeErrors=[];ws.addEventListener('message',e=>{const d=JSON.parse(e.data);if(d.method==='Runtime.exceptionThrown')runtimeErrors.push(d.params.exceptionDetails.text);});await send('Runtime.enable');
 await send('Page.enable');await send('Network.enable');const uploads=[];ws.addEventListener('message',e=>{const d=JSON.parse(e.data);if(d.method==='Network.requestWillBeSent'&&['POST','PUT','PATCH'].includes(d.params.request.method))uploads.push(d.params.request.url);});
 // Real browser directory/file handles from OPFS; only chooser and permission UI
 // are deterministic substitutes. Native desktop picker requires the separate smoke check.
 await send('Page.addScriptToEvaluateOnNewDocument',{source:`
 window.testDenied=false;
 FileSystemDirectoryHandle.prototype.queryPermission=async()=>window.testDenied?'denied':'granted';
 FileSystemDirectoryHandle.prototype.requestPermission=async()=>window.testDenied?'denied':'granted';
 window.showDirectoryPicker=async()=>{if(window.testCancel)throw new DOMException('Cancelled','AbortError');const root=await navigator.storage.getDirectory();return root.getDirectoryHandle(new URLSearchParams(location.search).get('workspace')||'personal',{create:true});};
 `});
 const url=(page='today',workspace='personal')=>origin+'/vault/dashboard?page='+page+'&workspace='+workspace;
 const navigate=async(page,workspace)=>{await send('Page.navigate',{url:url(page,workspace)});await wait("document.querySelector('#overview,#settings')?.getAttribute('aria-busy')==='false'");};
 const click=label=>evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent==='${label}'&&b.getClientRects().length).click()`);
 await fs.mkdir(path.join(dir,'screenshots'),{recursive:true});
 const capture=async name=>{await send('Runtime.evaluate',{expression:'scrollTo(0,0)'});await sleep(250);const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});await fs.writeFile(path.join(dir,'screenshots',name+'.png'),Buffer.from(shot.data,'base64'));};
 const key=async value=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key:value,code:value});await send('Input.dispatchKeyEvent',{type:'keyUp',key:value,code:value});};
 const readable=async selectors=>{
  const ratios=await evaluate(`(()=>{
   const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');canvas.width=canvas.height=1;
   const rgba=color=>{ctx.clearRect(0,0,1,1);ctx.fillStyle=color;ctx.fillRect(0,0,1,1);return [...ctx.getImageData(0,0,1,1).data];};
   const blend=(paint,under)=>paint.slice(0,3).map((v,i)=>v*paint[3]/255+under[i]*(1-paint[3]/255));
   const luminance=rgb=>rgb.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
   return ${JSON.stringify(selectors)}.flatMap(selector=>[...document.querySelectorAll(selector)].filter(el=>el.getClientRects().length).map(el=>{
    const ancestors=[];for(let parent=el;parent;parent=parent.parentElement)ancestors.unshift(parent);
    const bg=ancestors.reduce((under,parent)=>blend(rgba(getComputedStyle(parent).backgroundColor),under),[0,0,0]);
    const fg=blend(rgba(getComputedStyle(el).color),bg),a=luminance(fg),b=luminance(bg);
    return [selector,(Math.max(a,b)+.05)/(Math.min(a,b)+.05)];
   }));
  })()`);
  for(const [selector,ratio]of ratios)assert.ok(ratio>=4.5,selector+' text contrast '+ratio.toFixed(2)+' must meet 4.5:1');
 };
 for(const width of [375,1440,2560]){
  await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<768});
  for(const page of ['today','founder','journal']){
  await navigate(page,'personal');
  assert.equal(await evaluate("getComputedStyle(document.querySelector('h1')).fontWeight"),'600','Dashboard headings use the kwg weight hierarchy');
  assert.ok(await evaluate("parseFloat(getComputedStyle(document.querySelector('.vault-return')).borderRadius)<document.querySelector('.vault-return').getBoundingClientRect().height/2"),'Dashboard actions use rounded rectangles rather than site pills');
  await readable(['#heading','#subtitle','#search-help','#library-description','#empty p','#connection']);
  assert.ok(await evaluate("document.querySelector('.search-field svg').getBoundingClientRect().right<=document.querySelector('#search').getBoundingClientRect().left"),'Search text must clear its leading icon');
   assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
   if(width<1024)assert.equal(await evaluate("getComputedStyle(document.querySelector('.drawer-side')).visibility"),'hidden','Closed mobile navigation stays out of the reading path');
   else assert.ok(await evaluate("Math.abs(document.querySelector('main').getBoundingClientRect().left-parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--rail-width'))-(innerWidth-document.querySelector('main').getBoundingClientRect().right))<2"),'Desktop content should be centered beside the rail');
   const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width,height:await evaluate('document.documentElement.scrollHeight'),scale:1}});
   await fs.writeFile(path.join(dir,'screenshots',page+'-disconnected-'+width+'.png'),Buffer.from(shot.data,'base64'));
  }
 }
 await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
 await navigate('knowledge','personal');assert.equal(await evaluate("!!document.querySelector('.folder-panel')"),false);await evaluate("[...document.querySelectorAll('a')].find(a=>a.textContent==='Open Settings').click()");await wait("document.querySelector('#settings')?.getAttribute('aria-busy')==='false'");assert.equal(await evaluate("document.querySelector('nav a[aria-current=page]').textContent"),'Settings');assert.equal(await evaluate("document.querySelector('.sidebar').firstElementChild.matches('.vault-return')"),true);assert.equal(await evaluate("document.querySelector('.vault-return').getAttribute('href')"),'/vault');assert.equal(await evaluate("!!document.querySelector('#content,#create,#capture')"),false);assert.match(await evaluate("document.querySelector('.folder-panel').textContent"),/No notes are uploaded/);assert.equal(await evaluate("document.querySelector('#connection').textContent"),'Folder not connected');
 await readable(['.folder-panel p','.folder-panel h2']);
 await evaluate("document.querySelector('#workspace-select').focus()");await key('ArrowDown');await wait("document.querySelectorAll('[role=menuitemradio]').length===2");
 await key('Home');await wait("document.activeElement.getAttribute('data-workspace')==='personal'");await key('ArrowDown');await wait("document.activeElement.getAttribute('data-workspace')==='parallel'");
 await readable(['[role=menuitemradio]']);await capture('workspace-menu');await key('Escape');await wait("!document.querySelector('[role=menuitemradio]')");assert.equal(await evaluate('document.activeElement.id'),'workspace-select');
 await evaluate('window.testCancel=true');await click('Choose folder');await wait("document.querySelector('#status').textContent.includes('cancelled')");await evaluate('window.testCancel=false');await click('Choose folder');await wait("document.querySelector('#connection').textContent==='Local folder connected'");
 await navigate('knowledge','personal');await evaluate("document.querySelector('#create').focus();document.querySelector('#create').click()");await wait("document.activeElement.id==='title'");
 await readable(['#dialog-title','#new-dialog label','#new-dialog small']);await capture('new-note-dialog');await click('Cancel');await wait("!document.querySelector('#title')");await wait("document.activeElement.id==='create'");
 await evaluate("document.querySelector('#create').click()");await wait("!!document.querySelector('#title')");await evaluate("document.querySelector('#title').value='Browser note';document.querySelector('#new-form').requestSubmit()");await wait("document.querySelector('#note-path').textContent==='knowledge/Browser note.md'");await wait("document.activeElement.id==='content'");
 await evaluate("document.querySelector('#content').value='# Browser note\\n\\n[[Second note]]';document.querySelector('#content').dispatchEvent(new Event('input',{bubbles:true}))");await evaluate("document.querySelector('#save').click()");await wait("document.querySelector('#save-state').textContent==='Saved to your vault'");
 await send('Page.reload');await sleep(400);await wait("document.querySelector('#content')?.value.includes('Browser note')");assert.equal(await evaluate("document.querySelector('#connection').textContent"),'Local folder connected');
 await evaluate("document.querySelector('#content').value+=' draft';document.querySelector('#content').dispatchEvent(new Event('input',{bubbles:true}))");
 let dialog=false;ws.addEventListener('message',e=>{if(JSON.parse(e.data).method==='Page.javascriptDialogOpening')dialog=true;});await evaluate("document.querySelector('#workspace-select').click()");await wait("document.querySelectorAll('[role=menuitemradio]').length===2");const switching=evaluate("[...document.querySelectorAll('[role=menuitemradio]')].find(b=>b.textContent.includes('Parallel')).click()");for(let n=0;n<30&&!dialog;n++)await sleep(100);assert.ok(dialog);await send('Page.handleJavaScriptDialog',{accept:false});await switching;assert.match(await evaluate("document.querySelector('#content').value"),/draft/);
 await evaluate("window.testDenied=true;document.querySelector('#save').click()");await wait("document.querySelector('#save-state').textContent.includes('Not saved')");assert.match(await evaluate("document.querySelector('#content').value"),/draft/);
 // Reconnecting the same folder must never ask to discard or replace the draft.
 assert.equal(await evaluate("document.querySelector('#connection').textContent"),'Folder not connected','Revoked access must clear the connected status');
 await evaluate('window.confirmCalls=0;window.confirm=()=>{window.confirmCalls++;return true;}');
 await click('Reconnect folder');await wait("document.querySelector('#status').textContent.includes('denied')");
 assert.match(await evaluate("document.querySelector('#content').value"),/draft/);
 await evaluate('window.testDenied=false');await click('Reconnect folder');await wait("document.querySelector('#status').textContent.includes('connected')");
 assert.equal(await evaluate('window.confirmCalls'),0,'Permission recovery must not ask to discard the draft');
 assert.match(await evaluate("document.querySelector('#content').value"),/draft/);
 await evaluate("document.querySelector('#save').click()");await wait("document.querySelector('#save-state').textContent==='Saved to your vault'");
 await navigate('settings','personal');await evaluate('window.testDenied=true');await click('Reconnect folder');await wait("document.querySelector('#status').textContent.includes('denied')");
 assert.equal(await evaluate("document.querySelector('#connection').textContent"),'Folder not connected');
 await evaluate('window.testDenied=false');await click('Reconnect folder');await wait("document.querySelector('#connection').textContent==='Local folder connected'");
 await navigate('knowledge','personal');
 // A native/external edit makes the old browser version stale.
 await evaluate("(async()=>{const root=await navigator.storage.getDirectory(),vault=await root.getDirectoryHandle('personal'),folder=await vault.getDirectoryHandle('knowledge'),file=await folder.getFileHandle('Browser note.md'),s=await file.createWritable();await s.write('# External edit');await s.close();})()");
 await evaluate("document.querySelector('#content').value+=' stale draft';document.querySelector('#content').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#save').click()");await wait("document.querySelector('#status').textContent.includes('changed outside')");assert.match(await evaluate("document.querySelector('#content').value"),/stale draft/);
 // Reload after consciously discarding the synthetic test draft.
 await evaluate('window.onbeforeunload=null');const nav=navigate('settings','parallel');await sleep(100);if(dialog)await send('Page.handleJavaScriptDialog',{accept:true}).catch(()=>{});await nav;await click('Choose folder');await wait("document.querySelector('#connection').textContent==='Local folder connected'");await navigate('knowledge','parallel');assert.equal(await evaluate("document.querySelectorAll('#notes button').length"),0);
 await evaluate("document.querySelector('#create').click()");await wait("!!document.querySelector('#area')");assert.equal(await evaluate("document.querySelector('#area').value"),'parallel');assert.equal(await evaluate("document.querySelectorAll('#template option').length"),15);await click('Cancel');
 await fs.mkdir(path.join(dir,'screenshots'),{recursive:true});
 for(const [width,height]of [[320,800],[375,812],[768,1024],[1024,768],[1440,900],[2560,1348]]){await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<768});for(const page of ['today','founder','journal','knowledge','projects','review','settings']){await navigate(page,'parallel');if(width>=1024)assert.equal(await evaluate("getComputedStyle(document.querySelector('#pages-toggle')).display"),'none');if(width<1024){assert.equal(await evaluate("document.querySelector('#pages-toggle').getAttribute('aria-expanded')"),'false');await evaluate("document.querySelector('#pages-toggle').focus()");await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',text:'\r',windowsVirtualKeyCode:13});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await wait("document.querySelector('#pages-toggle').getAttribute('aria-expanded')==='true'");assert.equal(await evaluate("document.querySelectorAll('#workspace-navigation a').length"),7);assert.ok(await evaluate("[...document.querySelectorAll('#workspace-navigation a')].every(a=>a.getBoundingClientRect().height>=44&&a.getClientRects().length)"));await evaluate("document.querySelector('#workspace-navigation a[aria-current=page]').focus()");await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});await wait("document.querySelector('#pages-toggle').getAttribute('aria-expanded')==='false'");assert.equal(await evaluate("document.activeElement.id"),'pages-toggle');}assert.equal(await evaluate("!!document.querySelector('.folder-panel')"),page==='settings');assert.equal(await evaluate("document.querySelector('.vault-return').getBoundingClientRect().top>=0"),true);assert.equal(await evaluate("getComputedStyle(document.querySelector('.vault-return')).fontWeight"),'600');assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);assert.equal(await evaluate("getComputedStyle(document.body).backgroundColor"),'oklch(0.145 0 0)');assert.equal(await evaluate("getComputedStyle(document.querySelector('h1')).fontWeight"),'600');assert.equal(await evaluate("getComputedStyle(document.querySelector('nav a[aria-current=page]')).color"),'oklch(0.985 0 0)');}const shot=await send('Page.captureScreenshot',{format:'png'});await fs.writeFile(path.join(dir,'screenshots',width+'.png'),Buffer.from(shot.data,'base64'));}
 await navigate('knowledge','personal');assert.equal(await evaluate("document.querySelectorAll('[data-graph-node]').length"),1);assert.equal(await evaluate("(r=>r.length>0&&r.every(n=>getComputedStyle(n).display==='block'&&n.querySelector('b').offsetHeight<40))([...document.querySelectorAll('#notes .note')])"),true);assert.equal(await evaluate("[...document.querySelectorAll('a[href^=\"/vault/dashboard\"]')].every(a=>new URL(a.href).searchParams.get('workspace')==='personal')"),true);
 const writeDraft=async content=>{await evaluate(`document.querySelector('#content').value=${JSON.stringify(content)};document.querySelector('#content').dispatchEvent(new Event('input',{bubbles:true}))`);await evaluate("document.querySelector('#save').click()");await wait("document.querySelector('#save-state').textContent==='Saved to your vault'");};
 const create=async(name,content)=>{await evaluate("document.querySelector('#create').click()");await wait("!!document.querySelector('#title')");await evaluate(`document.querySelector('#title').value=${JSON.stringify(name)};document.querySelector('#new-form').requestSubmit()`);await wait("!document.querySelector('#title')");await wait("document.activeElement.id==='content'");await writeDraft(content);return evaluate("document.querySelector('#note-path').textContent");};
 await send('Emulation.setDeviceMetricsOverride',{width:375,height:812,deviceScaleFactor:1,mobile:true});
 for(const workspace of ['personal','parallel']){
  await navigate('knowledge',workspace);
  await create('Linked target','# Linked target\n\n'+workspace+' search-token');
  await create('Linked source','# Linked source\n\n[[Linked target]]');
  assert.ok(await evaluate("document.querySelectorAll('[data-graph-edge]').length>0"));
  await evaluate("document.querySelector('#preview-toggle').click();document.querySelector('[data-wiki]').click()");
  await wait("document.querySelector('#note-path').textContent==='knowledge/Linked target.md'");
  assert.match(await evaluate("document.querySelector('#backlinks').textContent"),/Linked source/);
  await evaluate("document.querySelector('#backlinks a').click()");await wait("document.querySelector('#note-path').textContent==='knowledge/Linked source.md'");
  await evaluate("document.querySelector('[data-graph-open=\"knowledge/Linked target.md\"]').click()");
  await wait("document.querySelector('#note-path').textContent==='knowledge/Linked target.md'");
  await writeDraft('# Linked target\n\n'+workspace+' edited search-token');
  await send('Page.reload');await sleep(400);await wait("document.querySelector('#overview,#settings')?.getAttribute('aria-busy')==='false'&&!!document.querySelector('#search')");
  await evaluate("document.querySelector('#search').value='search-token';document.querySelector('#search').dispatchEvent(new Event('input',{bubbles:true}))");
  await wait("document.querySelectorAll('#notes button').length===1");await evaluate("document.querySelector('#notes button').click()");
  assert.match(await evaluate("document.querySelector('#content').value"),new RegExp(workspace+' edited'));
  const actual=await evaluate(`(async()=>{const root=await navigator.storage.getDirectory(),vault=await root.getDirectoryHandle('${workspace}'),folder=await vault.getDirectoryHandle('knowledge');return (await(await folder.getFileHandle('Linked target.md')).getFile()).text();})()`);
  assert.equal(actual,'# Linked target\n\n'+workspace+' edited search-token');
  await navigate('journal',workspace);const dated=await evaluate("new Date().toLocaleDateString('en-CA')");
  await create(dated,'# '+dated+'\n\nSynthetic QA journal entry');
  await navigate('today',workspace);assert.match(await evaluate("document.querySelector('.daily-panel').textContent"),/Saved/);
  await navigate('review',workspace);assert.match(await evaluate("document.querySelector('#overview').textContent"),/1 entry/);
  const reviewPath=await create('QA weekly review','# QA weekly review\n\nSynthetic QA review');assert.equal(reviewPath,'reviews/QA weekly review.md');
  await send('Page.reload');await wait("document.querySelector('#content')?.value.includes('Synthetic QA review')");
  for(const page of ['founder','projects']){await navigate(page,workspace);await create('QA '+page,'# QA '+page+'\n\n- [ ] Synthetic QA action');}
  await navigate('founder',workspace);assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);assert.match(await evaluate("document.querySelector('#overview').textContent"),/2 remaining/);
 }
 // Goal-first Today and Founder: setup prompt, goal note, lead pipeline and conversation counter.
 await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
 await navigate('today','parallel');assert.equal(await evaluate("!!document.querySelector('.goal-setup,.goal-summary')"),false,'Parallel shows no goal panels without its own goals note');
 await navigate('today','personal');assert.match(await evaluate("document.querySelector('.goal-setup').textContent"),/Set your 2026 goal/);assert.match(await evaluate("document.querySelector('.sidebar .badge-primary').textContent"),/^(M[1-4] .+ left|Goal period ended)$/);
 const fromButton=async(selector,label)=>{await evaluate(`[...document.querySelectorAll('${selector} button')].find(b=>b.textContent==='${label}').click()`);await wait("document.activeElement.id==='title'");};
 await fromButton('.goal-setup','Create goal');assert.equal(await evaluate("document.querySelector('#template').value"),'goals');assert.equal(await evaluate("document.querySelector('#kind').value"),'founder');
 await evaluate("document.querySelector('#new-form').requestSubmit()");await wait("document.querySelector('#note-path').textContent==='founder/goals-2026.md'");await evaluate("document.querySelector('#save').click()");await wait("document.querySelector('#save-state').textContent==='Saved to your vault'");
 await navigate('today','personal');assert.equal(await evaluate("document.querySelector('#goal-clients').textContent"),'0 / 4');assert.equal(await evaluate("document.querySelectorAll('.goal-summary .step').length"),4);await readable(['.goal-summary .stat-title','.goal-summary .stat-value','.goal-summary .stat-desc','.sidebar .badge-primary']);
 await navigate('founder','personal');await fromButton('.pipeline','Add a lead');assert.equal(await evaluate("document.querySelector('#template').value"),'lead');
 await evaluate("document.querySelector('#title').value='QA client';document.querySelector('#new-form').requestSubmit()");await wait("document.querySelector('#note-path').textContent==='founder/QA client.md'");
 await writeDraft('---\ntype: lead\nname: QA client\nstage: won\nmrr: 800\n---\n\n# QA client\n');
 await navigate('founder','personal');assert.equal(await evaluate("document.querySelectorAll('.lead-card[data-stage=won]').length"),1);assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
 await fromButton('#overview','Log a conversation');assert.equal(await evaluate("document.querySelector('#template').value"),'conversation');await evaluate("document.querySelector('#title').value='QA call';document.querySelector('#new-form').requestSubmit()");await wait("document.querySelector('#note-path').textContent==='inbox/QA call.md'");await evaluate("document.querySelector('#save').click()");await wait("document.querySelector('#save-state').textContent==='Saved to your vault'");
 await navigate('founder','personal');assert.equal(await evaluate("document.querySelector('#conversation-count').textContent"),'1 / 20');
 await navigate('today','personal');assert.equal(await evaluate("document.querySelector('#goal-clients').textContent"),'1 / 4');assert.equal(await evaluate("document.querySelector('#goal-mrr').textContent"),'$800');assert.equal(await evaluate("document.querySelector('#goal-conversations').textContent"),'1 / 20');
 for(const width of [320,375,768]){await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<768});for(const page of ['today','founder']){await navigate(page,'personal');assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,page+' goal panels must not overflow at '+width);}}
 await capture('connected-founder-mobile');
 // Long content, connected desktop/mobile captures, and a 200% desktop zoom equivalent.
 await navigate('knowledge','personal');const longName='Long note title '+ 'a'.repeat(80);await create(longName,'# '+longName+'\n\nSynthetic long-title QA note');
 for(const [width,height]of [[320,800],[375,812],[720,450],[1440,900]]){
  await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:width===720?2:1,mobile:width<768});
  assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'Long titles and zoom must not cause horizontal page overflow');
  await evaluate("document.querySelector('#save').scrollIntoView();document.querySelector('#save').focus()");
  assert.ok(await evaluate("(r=>r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight)(document.querySelector('#save').getBoundingClientRect())"),'Save stays reachable at small widths and 200% zoom');
  await readable(['#note-path','#search-help','.note b','.note-excerpt','#save','#save-state','.graph-note-button span','.graph-note-button small']);
  assert.ok(await evaluate("[...document.querySelectorAll('.graph-note-button')].every(button=>{const box=button.getBoundingClientRect(),title=button.querySelector('span').getBoundingClientRect(),path=button.querySelector('small').getBoundingClientRect();return [title,path].every(text=>text.left>=box.left&&text.right<=box.right&&text.top>=box.top&&text.bottom<=box.bottom)&&path.top>=title.bottom;})"),'Graph titles and paths stay stacked inside their controls');
  assert.ok(await evaluate("(list=>list.scrollWidth<=list.clientWidth)(document.querySelector('.graph-list ul'))"),'The graph list must not hide horizontal overflow');
  await evaluate("document.querySelector('.graph-note-button').focus()");await readable(['.graph-note-button span','.graph-note-button small']);
  const graphTarget=await evaluate("(()=>{const button=document.querySelector('.graph-note-button');button.scrollIntoView({block:'center'});const r=button.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2};})()");
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',...graphTarget});await sleep(250);await readable(['.graph-note-button span','.graph-note-button small']);
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:0,y:0});
  assert.ok(await evaluate("document.querySelector('#content').getBoundingClientRect().height>=320"),'The selected-note editor retains its usable writing height');
  if(width!==720)await capture('connected-knowledge-'+width);
 }
 await navigate('today','personal');await capture('connected-today-desktop');
 await send('Emulation.setDeviceMetricsOverride',{width:375,height:812,deviceScaleFactor:1,mobile:true});await capture('connected-today-mobile');
 await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
 assert.equal(await evaluate("getComputedStyle(document.querySelector('.quick-card')).transitionDuration"),'0s');
 await send('Emulation.setScriptExecutionDisabled',{value:true});await send('Page.reload');await sleep(400);
 assert.ok(await evaluate("(r=>r.width>0&&r.height>0)(document.querySelector('noscript').getBoundingClientRect())"),'JavaScript-disabled guidance remains readable');await capture('noscript');
 assert.ok(await evaluate("document.querySelector('noscript').getBoundingClientRect().top<200"),'JavaScript-disabled guidance is visible in the first viewport');
 await send('Emulation.setScriptExecutionDisabled',{value:false});await send('Page.reload');await wait("document.querySelector('#overview')?.getAttribute('aria-busy')==='false'");
 await navigate('settings','parallel');await click('Forget folder');await wait("document.querySelector('#connection').textContent==='Folder not connected'");await navigate('knowledge','parallel');assert.equal(await evaluate("document.querySelectorAll('#notes button').length"),0);
 await send('Page.addScriptToEvaluateOnNewDocument',{source:'window.showDirectoryPicker=undefined;'});await navigate('settings','parallel');assert.match(await evaluate("document.querySelector('.folder-panel').textContent"),/This browser cannot/);await navigate('today','parallel');
 assert.match(await evaluate("document.querySelector('#overview').textContent"),/not available in this browser/);assert.deepEqual(await evaluate("['#capture','#create','#empty-create'].map(s=>document.querySelector(s).disabled)"),[true,true,true]);
 await send('Page.addScriptToEvaluateOnNewDocument',{source:'navigator.brave={isBrave:async()=>true};'});await navigate('settings','personal');assert.match(await evaluate("document.querySelector('.folder-panel').textContent"),/Brave turns off folder access/);assert.equal(await evaluate("document.querySelector('.folder-panel code').textContent"),'brave://flags/#file-system-access-api');await navigate('knowledge','personal');assert.match(await evaluate("document.querySelector('#overview').textContent"),/not available in this browser/);assert.deepEqual(await evaluate("['#capture','#create','#empty-create'].map(s=>document.querySelector(s).disabled)"),[true,true,true]);
 assert.deepEqual(uploads,[]);assert.deepEqual(runtimeErrors,[]);console.log('PASS: goal setup, lead pipeline, conversation counter and goal stats, local browser handles, cancellation, IndexedDB reconnect after reload, workspace isolation, draft switch protection, denied permission with accurate status, draft-preserving reconnect, stale conflicts, templates, both workspaces create/edit/save/reopen/search/links/backlinks/graph/journal/review/founder/projects, stacked note rows, seven pages at six sizes, centered desktop layouts, compact mobile Pages menu with keyboard opening and Escape focus return, Settings-only folder controls and top return link, dark styling, forget, unsupported and Brave guidance with disabled create actions, no note uploads or runtime exceptions.');console.log('Screenshots: '+path.join(dir,'screenshots'));await send('Browser.close');
}finally{ws?.close();browser.kill();}
