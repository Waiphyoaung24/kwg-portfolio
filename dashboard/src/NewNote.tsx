import { useRef, useState } from 'react';
import { Dialog,DialogContent,DialogTitle,DialogDescription } from './components/ui/dialog';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { NativeSelect, NativeSelectOption } from './components/ui/native-select';
import { Icon } from './Icon';
import { templateChoices,makeTemplate } from '../shared/vault-model.js';
import { today,workspace } from './notes';
import type { Note } from './types';
export const defaults:Record<string,string>={journal:'daily',projects:'project',reviews:'weekly',founder:'blank',inbox:'ideas',knowledge:'blank'};
export type NewRequest={kind:string;name:string;opener:HTMLElement|null};
export function NewNote({request,notes,onClose,onCreate}:{request:NewRequest|null;notes:Note[];onClose:()=>void;onCreate:(note:Note)=>boolean}){
 const created=useRef(false);const [error,setError]=useState('');const form=useRef<HTMLFormElement>(null),titleRef=useRef<HTMLInputElement>(null),opener=useRef<HTMLElement|null>(null);
 if(request)opener.current=request.opener;
 const field=(id:string)=>form.current!.querySelector<HTMLInputElement|HTMLSelectElement>('#'+id)!;
 return <Dialog open={!!request} onOpenChange={open=>{if(!open)onClose();}}><DialogContent id="new-dialog" aria-labelledby="dialog-title" className="dot-dialog" showCloseButton={false} onOpenAutoFocus={e=>{e.preventDefault();created.current=false;setError('');titleRef.current?.focus();}} onCloseAutoFocus={e=>{e.preventDefault();if(created.current)document.getElementById('content')?.focus();else opener.current?.focus();}} onPointerDownOutside={e=>e.preventDefault()}>
 <form id="new-form" ref={form} noValidate onSubmit={e=>{e.preventDefault();const name=field('title').value.trim(),path=`${field('kind').value}/${name}.md`;let problem='';if(!/^[a-zA-Z0-9][a-zA-Z0-9 _-]{0,99}$/.test(name))problem='Start with a letter or number. Use only letters, numbers, spaces, hyphens, or underscores.';if(notes.some(n=>n.path.toLowerCase()===path.toLowerCase()))problem='A note with this title already exists in this section. Choose another title.';setError(problem);if(problem){titleRef.current?.focus();return;}if(onCreate({path,content:makeTemplate(field('template').value,name,today,field('area').value),version:null,modified:new Date().toISOString()})){created.current=true;onClose();}}}>
 <div className="dialog-icon"><Icon name="file"/></div><DialogTitle id="dialog-title">New note</DialogTitle><DialogDescription>Choose a template, title, and section. Save the draft when you are ready.</DialogDescription>
 <Label htmlFor="title">Note title</Label><Input ref={titleRef} id="title" name="title" required maxLength={100} defaultValue={request?.name||''} placeholder="For example, Product launch" aria-describedby="title-help title-error" aria-invalid={error?true:undefined} onInput={()=>setError('')}/><small id="title-help">Use letters, numbers, spaces, hyphens, or underscores for the filename.</small><p id="title-error" className="field-error" role="alert" hidden={!error}>{error}</p>
 <Label htmlFor="template">Template</Label><NativeSelect id="template" defaultValue={defaults[request?.kind||'knowledge']} aria-describedby="template-help" onChange={e=>{const choice=templateChoices.find(([id])=>id===e.currentTarget.value);if(choice&&choice[0]!=='blank')field('kind').value=choice[2];}}>{templateChoices.map(([id,label])=><NativeSelectOption key={id} value={id}>{label}</NativeSelectOption>)}</NativeSelect><small id="template-help">Adapted from Wai-G. Area labels do not move notes between vaults.</small>
 <Label htmlFor="area">Area for project, person, money, and daily templates</Label><NativeSelect id="area" defaultValue={workspace==='parallel'?'parallel':'personal'}><NativeSelectOption value="personal">Personal</NativeSelectOption><NativeSelectOption value="parallel">Parallel</NativeSelectOption><NativeSelectOption value="business-one">Business One</NativeSelectOption><NativeSelectOption value="business-two">Business Two</NativeSelectOption></NativeSelect>
 <Label htmlFor="kind">Section</Label><NativeSelect id="kind" defaultValue={request?.kind||'knowledge'} onChange={e=>{field('template').value=defaults[e.currentTarget.value];}}>{[['inbox','Inbox'],['knowledge','Knowledge'],['projects','Projects'],['journal','Journal'],['founder','Founder dashboard'],['reviews','Weekly reviews']].map(([id,label])=><NativeSelectOption key={id} value={id}>{label}</NativeSelectOption>)}</NativeSelect>
 <div className="dialog-actions"><Button type="button" id="cancel" variant="outline" onClick={onClose}>Cancel</Button><Button type="submit">Create note</Button></div>
 </form></DialogContent></Dialog>;
}
