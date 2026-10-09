import { useEffect, useRef, useState } from 'react';
import { Icon } from './Icon';
import { templateChoices,makeTemplate } from '../shared/vault-model.js';
import { today,workspace } from './notes';
import type { Note } from './types';
export const defaults:Record<string,string>={journal:'daily',projects:'project',reviews:'weekly',founder:'blank',inbox:'ideas',knowledge:'blank'};
export type NewRequest={kind:string;name:string;opener:HTMLElement|null;template?:string};
const select='select w-full',label='mt-6 mb-2 block text-sm font-semibold';
// Native <dialog> provides the focus trap, Escape and inert backdrop; outside clicks do not close it.
export function NewNote({request,notes,onClose,onCreate}:{request:NewRequest|null;notes:Note[];onClose:()=>void;onCreate:(note:Note)=>boolean}){
 const created=useRef(false);const [error,setError]=useState('');const dialog=useRef<HTMLDialogElement>(null),form=useRef<HTMLFormElement>(null),titleRef=useRef<HTMLInputElement>(null),opener=useRef<HTMLElement|null>(null),closing=useRef(false);
 if(request)opener.current=request.opener;
 useEffect(()=>{const d=dialog.current;if(!d)return;if(request&&!d.open){created.current=false;setError('');d.showModal();titleRef.current?.focus();}else if(!request&&d.open){closing.current=true;d.close();if(created.current)requestAnimationFrame(()=>document.getElementById('content')?.focus());else opener.current?.focus();}},[request]);
 // The close event is async: ignore closes started above so a quick reopen is not cancelled.
 const restore=()=>{if(closing.current){closing.current=false;return;}onClose();opener.current?.focus();};
 const field=(id:string)=>form.current!.querySelector<HTMLInputElement|HTMLSelectElement>('#'+id)!;
 return <dialog ref={dialog} id="new-dialog" className="modal modal-bottom sm:modal-middle" aria-labelledby="dialog-title"  onClose={restore}><div className="modal-box max-h-[calc(100dvh-2rem)] border border-base-300 bg-base-200">
 {request&&<form id="new-form" ref={form} noValidate onSubmit={e=>{e.preventDefault();const name=field('title').value.trim(),path=`${field('kind').value}/${name}.md`;let problem='';if(!/^[a-zA-Z0-9][a-zA-Z0-9 _-]{0,99}$/.test(name))problem='Letters, numbers, spaces, - or _ only.';if(notes.some(n=>n.path.toLowerCase()===path.toLowerCase()))problem='Title already exists.';setError(problem);if(problem){titleRef.current?.focus();return;}if(onCreate({path,content:makeTemplate(field('template').value,name,today,field('area').value),version:null,modified:new Date().toISOString()})){created.current=true;onClose();}}}>
 <div className="dialog-icon mb-4 grid size-12 place-items-center rounded-field bg-base-300 text-primary"><Icon name="file"/></div><h2 id="dialog-title" className="text-xl">New note</h2>
 <label htmlFor="title" className={label}>Note title</label><input ref={titleRef} id="title" name="title" className={'input w-full'+(error?' input-error':'')} required maxLength={100} defaultValue={request.name} aria-describedby="title-error" aria-invalid={error?true:undefined} onInput={()=>setError('')}/><p id="title-error" className="field-error mt-2 text-sm text-error" role="alert" hidden={!error}>{error}</p>
 <label htmlFor="template" className={label}>Template</label><select id="template" className={select} defaultValue={request.template||defaults[request.kind]||'blank'} onChange={e=>{const choice=templateChoices.find(([id])=>id===e.currentTarget.value);if(choice&&choice[0]!=='blank')field('kind').value=choice[2];}}>{templateChoices.map(([id,name])=><option key={id} value={id}>{name}</option>)}</select>
 <label htmlFor="area" className={label}>Area</label><select id="area" className={select} defaultValue={workspace==='parallel'?'parallel':'personal'}><option value="personal">Personal</option><option value="parallel">Parallel</option><option value="business-one">Business One</option><option value="business-two">Business Two</option></select>
 <label htmlFor="kind" className={label}>Section</label><select id="kind" className={select} defaultValue={request.kind||'knowledge'} onChange={e=>{field('template').value=defaults[e.currentTarget.value];}}>{[['inbox','Inbox'],['knowledge','Knowledge'],['projects','Projects'],['journal','Journal'],['founder','Founder dashboard'],['reviews','Weekly reviews']].map(([id,name])=><option key={id} value={id}>{name}</option>)}</select>
 <div className="modal-action mt-8"><button type="button" id="cancel" className="btn btn-outline" onClick={onClose}>Cancel</button><button type="submit" className="btn btn-primary">Create note</button></div>
 </form>}
 </div></dialog>;
}
