import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
const dir=await fs.mkdtemp(path.join(os.tmpdir(),'kwg-dashboard-ui-'));
const origin=process.env.DASHBOARD_ORIGIN||'http://127.0.0.1:4327';
const browser=spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--remote-debugging-port=0',`--user-data-dir=${path.join(dir,'profile')}`,'about:blank'],{windowsHide:true,stdio:['ignore','ignore','inherit']});
let ws;const sleep=ms=>new Promise(r=>setTimeout(r,ms));
try{
 let port;for(let i=0;i<60;i++){try{port=(await fs.readFile(path.join(dir,'profile','DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{await sleep(200);}}
 if(!port)throw Error('Edge did not expose a debugging port.');
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
 const navigate=async(page,workspace)=>{await send('Page.navigate',{url:url(page,workspace)});await wait("document.querySelector('#overview')?.getAttribute('aria-busy')==='false'");};
 const click=label=>evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent==='${label}').click()`);
 await navigate('knowledge','personal');assert.match(await evaluate("document.querySelector('.folder-panel').textContent"),/No notes are uploaded/);assert.equal(await evaluate("document.querySelector('#connection').textContent"),'Folder not connected');
 await evaluate('window.testCancel=true');await click('Choose folder');await wait("document.querySelector('#status').textContent.includes('cancelled')");await evaluate('window.testCancel=false');await click('Choose folder');await wait("document.querySelector('#connection').textContent==='Local folder connected'");
 await evaluate("document.querySelector('#create').click()");await wait("!!document.querySelector('#title')");await evaluate("document.querySelector('#title').value='Browser note';document.querySelector('#new-form').requestSubmit()");await wait("document.querySelector('#note-path').textContent==='knowledge/Browser note.md'");
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
 await evaluate('window.testDenied=true');await click('Reconnect folder');await wait("document.querySelector('#status').textContent.includes('denied')");
 assert.equal(await evaluate("document.querySelector('#connection').textContent"),'Folder not connected');
 await evaluate('window.testDenied=false');await click('Reconnect folder');await wait("document.querySelector('#connection').textContent==='Local folder connected'");
 // A native/external edit makes the old browser version stale.
 await evaluate("(async()=>{const root=await navigator.storage.getDirectory(),vault=await root.getDirectoryHandle('personal'),folder=await vault.getDirectoryHandle('knowledge'),file=await folder.getFileHandle('Browser note.md'),s=await file.createWritable();await s.write('# External edit');await s.close();})()");
 await evaluate("document.querySelector('#content').value+=' stale draft';document.querySelector('#content').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#save').click()");await wait("document.querySelector('#status').textContent.includes('changed outside')");assert.match(await evaluate("document.querySelector('#content').value"),/stale draft/);
 // Reload after consciously discarding the synthetic test draft.
 await evaluate('window.onbeforeunload=null');const nav=navigate('knowledge','parallel');await sleep(100);if(dialog)await send('Page.handleJavaScriptDialog',{accept:true}).catch(()=>{});await nav;await click('Choose folder');await wait("document.querySelector('#connection').textContent==='Local folder connected'");assert.equal(await evaluate("document.querySelectorAll('#notes button').length"),0);
 await evaluate("document.querySelector('#create').click()");await wait("!!document.querySelector('#area')");assert.equal(await evaluate("document.querySelector('#area').value"),'parallel');assert.equal(await evaluate("document.querySelectorAll('#template option').length"),10);await click('Cancel');
 await fs.mkdir(path.join(dir,'screenshots'));
 for(const [width,height]of [[360,800],[768,1024],[1280,800],[1440,900]]){await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<768});for(const page of ['today','founder','journal','knowledge','projects','review']){await navigate(page,'parallel');assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);assert.equal(await evaluate("getComputedStyle(document.body).backgroundColor"),'rgb(10, 10, 10)');assert.equal(await evaluate("getComputedStyle(document.querySelector('h1')).fontWeight"),'400');assert.equal(await evaluate("getComputedStyle(document.querySelector('nav a[aria-current=page]')).color"),'rgb(255, 255, 255)');}const shot=await send('Page.captureScreenshot',{format:'png'});await fs.writeFile(path.join(dir,'screenshots',width+'.png'),Buffer.from(shot.data,'base64'));}
 await navigate('knowledge','personal');assert.equal(await evaluate("document.querySelectorAll('[data-graph-node]').length"),1);assert.equal(await evaluate("(r=>r.length>0&&r.every(n=>getComputedStyle(n).display==='block'&&n.querySelector('b').offsetHeight<40))([...document.querySelectorAll('#notes .note')])"),true);assert.equal(await evaluate("[...document.querySelectorAll('a[href^=\"/vault/dashboard\"]')].every(a=>new URL(a.href).searchParams.get('workspace')==='personal')"),true);
 const writeDraft=async content=>{await evaluate(`document.querySelector('#content').value=${JSON.stringify(content)};document.querySelector('#content').dispatchEvent(new Event('input',{bubbles:true}))`);await evaluate("document.querySelector('#save').click()");await wait("document.querySelector('#save-state').textContent==='Saved to your vault'");};
 const create=async(name,content)=>{await evaluate("document.querySelector('#create').click()");await wait("!!document.querySelector('#title')");await evaluate(`document.querySelector('#title').value=${JSON.stringify(name)};document.querySelector('#new-form').requestSubmit()`);await wait("!document.querySelector('#title')");await writeDraft(content);return evaluate("document.querySelector('#note-path').textContent");};
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
  await send('Page.reload');await wait("document.querySelector('#overview')?.getAttribute('aria-busy')==='false'");
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
  await navigate('founder',workspace);assert.match(await evaluate("document.querySelector('#overview').textContent"),/2 remaining/);
 }
 await click('Forget folder');await wait("document.querySelector('#connection').textContent==='Folder not connected'");assert.equal(await evaluate("document.querySelectorAll('#notes button').length"),0);
 await send('Page.addScriptToEvaluateOnNewDocument',{source:'window.showDirectoryPicker=undefined;'});await navigate('today','parallel');assert.match(await evaluate("document.querySelector('.folder-panel').textContent"),/This browser cannot/);
 assert.match(await evaluate("document.querySelector('#overview').textContent"),/not available in this browser/);assert.deepEqual(await evaluate("['#capture','#create','#empty-create'].map(s=>document.querySelector(s).disabled)"),[true,true,true]);
 await send('Page.addScriptToEvaluateOnNewDocument',{source:'navigator.brave={isBrave:async()=>true};'});await navigate('knowledge','personal');assert.match(await evaluate("document.querySelector('.folder-panel').textContent"),/Brave turns off folder access/);assert.equal(await evaluate("document.querySelector('.folder-panel code').textContent"),'brave://flags/#file-system-access-api');assert.match(await evaluate("document.querySelector('#overview').textContent"),/not available in this browser/);assert.deepEqual(await evaluate("['#capture','#create','#empty-create'].map(s=>document.querySelector(s).disabled)"),[true,true,true]);
 assert.deepEqual(uploads,[]);assert.deepEqual(runtimeErrors,[]);console.log('PASS: local browser handles, cancellation, IndexedDB reconnect after reload, workspace isolation, draft switch protection, denied permission with accurate status, draft-preserving reconnect, stale conflicts, templates, both workspaces create/edit/save/reopen/search/links/backlinks/graph/journal/review/founder/projects, stacked note rows, six pages at four sizes, dark styling, forget, unsupported and Brave guidance with disabled create actions, no note uploads or runtime exceptions.');console.log('Screenshots: '+path.join(dir,'screenshots'));await send('Browser.close');
}finally{ws?.close();browser.kill();}
