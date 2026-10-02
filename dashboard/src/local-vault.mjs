export const folders=['journal','knowledge','projects','reviews','founder','inbox'];
export const supported=()=>globalThis.isSecureContext && typeof globalThis.showDirectoryPicker==='function' && !!globalThis.indexedDB && !!globalThis.navigator?.locks;
export const unsupportedReason=()=>supported()?null:!globalThis.isSecureContext?'insecure':typeof globalThis.showDirectoryPicker!=='function'&&globalThis.navigator?.brave?'brave':'browser';
export const digest=async content=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(content))),x=>x.toString(16).padStart(2,'0')).join('');
const valid=path=>typeof path==='string' && /^(journal|knowledge|projects|reviews|founder|inbox)\/[a-zA-Z0-9][a-zA-Z0-9 _-]*\.md$/.test(path);
const limit=1024*1024;
export function handleStore(){
 const open=()=>new Promise((resolve,reject)=>{const request=indexedDB.open('kwg-local-vault-handles',1);request.onupgradeneeded=()=>request.result.createObjectStore('handles');request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(Error('Cannot remember folders in this browser. Allow site storage and try again.'));});
 async function access(mode,operation){const db=await open();try{return await new Promise((resolve,reject)=>{const tx=db.transaction('handles',mode),request=operation(tx.objectStore('handles'));let result;request.onsuccess=()=>{result=request.result;};tx.oncomplete=()=>resolve(result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);});}finally{db.close();}}
 return {get:key=>access('readonly',s=>s.get(key)),set:(key,value)=>access('readwrite',s=>s.put(value,key)),remove:key=>access('readwrite',s=>s.delete(key))};
}
export function createVault(workspace,{store=handleStore(),locks=navigator.locks,picker=options=>globalThis.showDirectoryPicker(options)}={}){
 if(!['personal','parallel'].includes(workspace))throw Error('Unknown workspace. Choose Personal or Parallel.');
 let root=null;
 const other=workspace==='personal'?'parallel':'personal';
 async function permission(){if(!root)throw Error('Choose a folder for this workspace first.');if(await root.queryPermission({mode:'readwrite'})!=='granted')throw Object.assign(Error('Folder permission is needed. Use Reconnect folder, then retry.'),{name:'NotAllowedError'});const remembered=await store.get(workspace);if(!remembered||!await root.isSameEntry(remembered))throw Error('This workspace folder changed in another tab. Keep your draft and reload this page.');}
 async function current(path){const [folder,name]=path.split('/');try{const dir=await root.getDirectoryHandle(folder),file=await(await dir.getFileHandle(name)).getFile();if(file.size>limit)throw Error('Note exceeds 1 MiB. Edit it in Obsidian.');return {content:await file.text(),modified:new Date(file.lastModified).toISOString()};}catch(e){if(e.name==='NotFoundError')return null;throw e;}}
 return {
  get name(){return root?.name||'';},
  async restore(){root=await store.get(workspace)||null;return !!root && await root.queryPermission({mode:'readwrite'})==='granted';},
  async connect(){const selected=await picker({id:'kwg-'+workspace,mode:'readwrite'});return locks.request('kwg-vault-mutation',async()=>{const existing=await store.get(other);if(existing&&(await selected.isSameEntry(existing)||await selected.resolve(existing)!==null||await existing.resolve(selected)!==null))throw Error('Choose a separate folder. Personal and Parallel cannot use the same or nested folders.');if(await selected.queryPermission({mode:'readwrite'})!=='granted')throw Error('Read and write permission was not granted. Choose the folder again.');await store.set(workspace,selected);root=selected;});},
  async reconnect(){if(!root)throw Error('Choose a folder first.');if(await root.requestPermission({mode:'readwrite'})!=='granted')throw Object.assign(Error('Permission was denied. Your draft is still in this tab.'),{name:'NotAllowedError'});await permission();},
  async forget(){await locks.request('kwg-vault-mutation',async()=>{await store.remove(workspace);root=null;});},
  async list(){await permission();const notes=[];for(const folder of folders){let dir;try{dir=await root.getDirectoryHandle(folder);}catch(e){if(e.name==='NotFoundError')continue;throw e;}for await(const [name,handle]of dir.entries()){const path=folder+'/'+name;if(handle.kind!=='file'||!valid(path))continue;const file=await handle.getFile();if(file.size>limit)continue;const content=await file.text();notes.push({path,content,version:await digest(content),modified:new Date(file.lastModified).toISOString()});}}return notes.sort((a,b)=>b.modified.localeCompare(a.modified));},
  async save(note){if(!valid(note.path)||typeof note.content!=='string'||!(note.version===null||typeof note.version==='string'))throw Error('Invalid note path, content, or version.');if(new TextEncoder().encode(note.content).length>limit)throw Error('Note exceeds 1 MiB. Your draft is still in this tab.');return locks.request('kwg-vault-mutation',async()=>{
   await permission();const old=await current(note.path);if((old?await digest(old.content):null)!==note.version)throw Error('This note changed outside this editor. Copy your draft before reloading the latest version.');
   if(old){const history=await root.getDirectoryHandle('.history',{create:true}),backup=await history.getFileHandle(crypto.randomUUID()+'.md',{create:true});const stream=await backup.createWritable({mode:'exclusive'});try{await stream.write(old.content);await stream.close();}catch(e){await stream.abort().catch(()=>{});throw e;}}
   // Browser locks serialize this origin's tabs. Native editors cannot share that lock;
   // recheck immediately before writing, and keep the previous version in local history.
   const [folder,name]=note.path.split('/'),dir=await root.getDirectoryHandle(folder,{create:true});const latest=await current(note.path);if((latest?await digest(latest.content):null)!==note.version)throw Error('This note changed during save. Copy your draft and reload.');
   const handle=await dir.getFileHandle(name,{create:true});const stream=await handle.createWritable({mode:'exclusive'});try{await stream.write(note.content);await stream.close();}catch(e){await stream.abort().catch(()=>{});throw e;}return {version:await digest(note.content)};
  });}
 };
}
