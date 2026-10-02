import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createVault,digest,unsupportedReason} from './src/local-vault.mjs';
const missing=()=>Object.assign(Error('Missing'),{name:'NotFoundError'});
class Directory{
 constructor(name){this.name=name;this.kind='directory';this.items=new Map();this.permission='granted';this.prompts=0;}
 async queryPermission(){return this.permission;}
 async requestPermission(){this.prompts++;return this.permission;}
 async isSameEntry(other){return this===other;}
 async resolve(other){if(this===other)return [];for(const [name,item]of this.items)if(item.kind==='directory'){const found=await item.resolve(other);if(found)return [name,...found];}return null;}
 async getDirectoryHandle(name,{create=false}={}){if(!this.items.has(name)){if(!create)throw missing();this.items.set(name,new Directory(name));}return this.items.get(name);}
 async getFileHandle(name,{create=false}={}){if(!this.items.has(name)){if(!create)throw missing();let content='';const file={name,kind:'file',fail:false,getFile:async()=>({size:new TextEncoder().encode(content).length,lastModified:0,text:async()=>content}),createWritable:async()=>{let pending=content;return {write:async value=>{if(file.fail)throw Error('Disk write failed');pending=value;},close:async()=>{content=pending;},abort:async()=>{}};}};this.items.set(name,file);}return this.items.get(name);}
 async *entries(){yield* this.items;}
}
function fixture(){const values=new Map(),store={get:async key=>values.get(key),set:async(key,value)=>values.set(key,value),remove:async key=>values.delete(key)};let queue=Promise.resolve();const locks={request:(_name,fn)=>{const result=queue.then(fn);queue=result.catch(()=>{});return result;}};return {store,locks};}
test('folders remain isolated, remembered, overlap-safe and versioned',async()=>{
 const deps=fixture(),a=new Directory('Personal'),b=new Directory('Parallel');
 const personal=createVault('personal',{...deps,picker:async()=>a}),parallel=createVault('parallel',{...deps,picker:async()=>b});
 assert.equal(await personal.restore(),false);await personal.connect();await parallel.connect();assert.deepEqual(await personal.list(),[]);assert.equal(a.items.size,0);
 const path='knowledge/Same.md';await personal.save({path,content:'# Personal',version:null});await parallel.save({path,content:'# Parallel',version:null});
 const old=(await personal.list())[0];assert.equal((await parallel.list())[0].content,'# Parallel');
 const tab=createVault('personal',deps);assert.equal(await tab.restore(),true);assert.equal(a.prompts,0);
 await tab.save({...old,content:'# Updated'});await assert.rejects(personal.save({...old,content:'Stale'}),/changed outside/);
 assert.equal((await a.getDirectoryHandle('.history')).items.size,1);
 assert.equal((await parallel.list())[0].content,'# Parallel');
 for(const chosen of [a,await a.getDirectoryHandle('nested',{create:true})]){const bad=createVault('parallel',{...deps,picker:async()=>chosen});await assert.rejects(bad.connect(),/same or nested/);}
 await tab.forget();await assert.rejects(personal.list(),/changed in another tab/);assert.equal((await b.getDirectoryHandle('knowledge')).items.size,1);
});
test('permission denial, cancellation, path boundaries, write failure and concurrent conflicts preserve content',async()=>{
 const deps=fixture(),root=new Directory('Personal');let cancel=false;const vault=createVault('personal',{...deps,picker:async()=>{if(cancel)throw Object.assign(Error('Cancelled'),{name:'AbortError'});return root;}});await vault.connect();
 const path='knowledge/Test.md';await vault.save({path,content:'# Original',version:null});let note=(await vault.list())[0];
 for(const path of ['../escape.md','knowledge/../../secret.md','knowledge/nested/file.md','.env'])await assert.rejects(vault.save({path,content:'x',version:null}),/Invalid/);
 root.permission='denied';await assert.rejects(vault.save({...note,content:'Denied'}),/permission/);await assert.rejects(vault.reconnect(),/denied/);root.permission='granted';
 cancel=true;await assert.rejects(vault.connect(),{name:'AbortError'});assert.equal((await vault.list())[0].content,'# Original');
 const file=await(await root.getDirectoryHandle('knowledge')).getFileHandle('Test.md');file.fail=true;await assert.rejects(vault.save({...note,content:'Failed'}),/Disk write/);file.fail=false;assert.equal((await vault.list())[0].content,'# Original');
 const concurrent=await Promise.allSettled([vault.save({...note,content:'First'}),vault.save({...note,content:'Second'})]);assert.equal(concurrent.filter(r=>r.status==='fulfilled').length,1);assert.equal((await vault.list())[0].version,await digest('First'));
});
test('unsupported reason names the failed requirement',()=>{
 const keys=['isSecureContext','showDirectoryPicker','indexedDB','navigator'],saved=keys.map(k=>Object.getOwnPropertyDescriptor(globalThis,k));
 const env=(secure,picker,brave,locks=true)=>{for(const [k,value]of Object.entries({isSecureContext:secure,showDirectoryPicker:picker?()=>{}:undefined,indexedDB:{},navigator:{locks:locks?{}:undefined,...(brave?{brave:{}}:{})}}))Object.defineProperty(globalThis,k,{value,configurable:true,writable:true});return unsupportedReason();};
 try{
  assert.equal(env(true,true,false),null);
  assert.equal(env(true,true,true),null);
  assert.equal(env(false,false,true),'insecure');
  assert.equal(env(true,false,true),'brave');
  assert.equal(env(true,false,false),'browser');
  assert.equal(env(true,true,false,false),'browser');
 }finally{keys.forEach((k,i)=>saved[i]?Object.defineProperty(globalThis,k,saved[i]):delete globalThis[k]);}
});
