import { useEffect, useRef, useState } from 'react';
import { Icon } from './Icon';
import { templateChoices,makeTemplate } from '../shared/vault-model.js';
import { today,workspace } from './notes';
import type { Note } from './types';
export const defaults:Record<string,string>={journal:'daily',projects:'project',reviews:'weekly',founder:'blank',inbox:'ideas',knowledge:'blank'};
export type NewRequest={kind:string;name:string;opener:HTMLElement|null;template?:string};
const select='select w-full',help='mt-2 block text-xs text-base-content/70',label='mt-6 mb-2 block text-sm font-semibold';
// Native <dialog> provides the focus trap, Escape and inert backdrop; outside clicks do not close it.
export function NewNote({request,notes,onClose,onCreate}:{request:NewRequest|null;notes:Note[];onClose:()=>void;onCreate:(note:Note)=>boolean}){
 const created=useRef(false);const [error,setError]=useState('');const dialog=useRef<HTMLDialogElement>(null),form=useRef<HTMLFormElement>(null),titleRef=useRef<HTMLInputElement>(null),opener=useRef<HTMLElement|null>(null);
 if(request)opener.current=request.opener;
 useEffect(()=>{const d=dialog.current;if(!d)return;if(request&&!d.open){created.current=false;setError('');d.showModal();titleRef.current?.focus();}else if(!request&&d.open)d.close();},[request]);
 const restore=()=>{onClose();requestAnimationFrame(()=>{if(created.current)document.getElementById('content')?.focus();else opener.current?.focus();});};
 const field=(id:string)=>form.current!.querySelector<HTMLInputElement|HTMLSelectElement>('#'+id)!;
 return <dialog ref={dialog} id="new-dialog" className="modal modal-bottom sm:modal-middle" aria-labelledby="dialog-title" aria-describedby="dialog-description" onClose={restore}><div className="modal-box max-h-[calc(100dvh-2rem)] border border-base-300 bg-base-200">
 {request&&<form id="new-form" ref={form} noValidate onSubmit={e=>{e.preventDefault();const name=field('title').value.trim(),path=`${field('kind').value}/${name}.md`;let problem='';if(!/^[a-zA-Z0-9][a-zA-Z0-9 _-]{0,99}$/.test(name))problem='Start with a letter or number. Use only letters, numbers, spaces, hyphens, or underscores.';if(notes.some(n=>n.path.toLowerCase()===path.toLowerCase()))problem='A note with this title already exists in this section. Choose another title.';setError(problem);if(problem){titleRef.current?.focus();return;}if(onCreate({path,content:makeTemplate(field('template').value,name,today,field('area').value),version:null,modified:new Date().toISOString()})){created.current=true;onClose();}}}>
 <div className="dialog-icon mb-4 grid size-12 place-items-center rounded-field bg-base-300 text-primary"><Icon name="file"/></div><h2 id="dialog-title" className="text-xl">New note</h2><p id="dialog-description" className="text-sm leading-relaxed text-base-content/70">Choose a template, title, and section. Save the draft when you are ready.</p>
 <label htmlFor="title" className={label}>Note title</label><input ref={titleRef} id="title" name="title" className={'input w-full'+(error?' input-error':'')} required maxLength={100} defaultValue={request.name} placeholder="For example, Product launch" aria-describedby="title-help title-error" aria-invalid={error?true:undefined} onInput={()=>setError('')}/><small id="title-help" className={help}>Use letters, numbers, spaces, hyphens, or underscores for the filename.</small><p id="title-error" className="field-error mt-2 text-sm text-error" role="alert" hidden={!error}>{error}</p>
 <label htmlFor="template" className={label}>Template</label><select id="template" className={select} defaultValue={request.template||defaults[request.kind]||'blank'} aria-describedby="template-help" onChange={e=>{const choice=templateChoices.find(([id])=>id===e.currentTarget.value);if(choice&&choice[0]!=='blank')field('kind').value=choice[2];}}>{templateChoices.map(([id,name])=><option key={id} value={id}>{name}</option>)}</select><small id="template-help" className={help}>Adapted from Wai-G. Area labels do not move notes between vaults.</small>
 <label htmlFor="area" className={label}>Area for project, person, money, and daily templates</label><select id="area" className={select} defaultValue={workspace==='parallel'?'parallel':'personal'}><option value="personal">Personal</option><option value="parallel">Parallel</option><option value="business-one">Business One</option><option value="business-two">Business Two</option></select>
 <label htmlFor="kind" className={label}>Section</label><select id="kind" className={select} defaultValue={request.kind||'knowledge'} onChange={e=>{field('template').value=defaults[e.currentTarget.value];}}>{[['inbox','Inbox'],['knowledge','Knowledge'],['projects','Projects'],['journal','Journal'],['founder','Founder dashboard'],['reviews','Weekly reviews']].map(([id,name])=><option key={id} value={id}>{name}</option>)}</select>
 <div className="modal-action mt-8"><button type="button" id="cancel" className="btn btn-outline" onClick={onClose}>Cancel</button><button type="submit" className="btn btn-primary">Create note</button></div>
 </form>}
 </div></dialog>;
}
