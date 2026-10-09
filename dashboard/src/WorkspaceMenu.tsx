import { useEffect,useLayoutEffect,useRef,useState,type KeyboardEvent } from 'react';
import { CheckIcon,ChevronDownIcon } from 'lucide-react';
import { workspace,workspaceName } from './notes';

const options=[['personal','Personal'],['parallel','Parallel']] as const;
// daisyUI dropdown with the WAI-ARIA menu-radio keyboard pattern: arrows, Home/End, Escape returns focus.
export function WorkspaceMenu({canLeave,onLeave,page}:{canLeave:()=>boolean;onLeave:()=>void;page:string}){
 const [open,setOpen]=useState(false),root=useRef<HTMLDivElement>(null),trigger=useRef<HTMLButtonElement>(null),focusTarget=useRef<'checked'|'first'|'last'>('checked');
 const items=()=>[...root.current?.querySelectorAll<HTMLButtonElement>('[role=menuitemradio]')??[]];
 const show=(focus:'checked'|'first'|'last'='checked')=>{focusTarget.current=focus;setOpen(true);};
 useLayoutEffect(()=>{if(!open)return;const list=items(),focus=focusTarget.current;(focus==='first'?list[0]:focus==='last'?list.at(-1):list.find(b=>b.getAttribute('aria-checked')==='true'))?.focus();},[open]);
 const close=(refocus=true)=>{setOpen(false);if(refocus)trigger.current?.focus();};
 useEffect(()=>{if(!open)return;const outside=(e:PointerEvent)=>{if(!root.current?.contains(e.target as Node))close(false);};document.addEventListener('pointerdown',outside);return()=>document.removeEventListener('pointerdown',outside);},[open]);
 function choose(next:string){close();if(next===workspace||!canLeave())return;onLeave();location.assign('/vault/dashboard?page='+page+'&workspace='+next);}
 function onMenuKey(e:KeyboardEvent){const list=items(),i=list.indexOf(document.activeElement as HTMLButtonElement);const move=(n:number)=>{e.preventDefault();list[(n+list.length)%list.length]?.focus();};
  if(e.key==='ArrowDown')move(i+1);else if(e.key==='ArrowUp')move(i-1);else if(e.key==='Home')move(0);else if(e.key==='End')move(list.length-1);else if(e.key==='Escape'){e.preventDefault();e.stopPropagation();close();}else if(e.key==='Tab')close(false);}
 return <div ref={root} className="workspace-switch border-t border-base-300 px-2 pt-4">
  <span id="workspace-label" className="mb-2 block text-sm font-medium">Workspace</span>
  <div className={'dropdown dropdown-top w-full'+(open?' dropdown-open':'')}>
   <button ref={trigger} id="workspace-select" type="button" data-workspace={workspace} className="workspace-trigger btn btn-outline btn-block justify-between" aria-haspopup="menu" aria-expanded={open} aria-labelledby="workspace-label workspace-current" onClick={()=>open?close():show()} onKeyDown={e=>{if(['ArrowDown','ArrowUp','Enter',' '].includes(e.key)){e.preventDefault();show(e.key==='ArrowUp'?'last':'checked');}}}><span id="workspace-current">{workspaceName}</span><ChevronDownIcon aria-hidden="true" className="size-4"/></button>
   {open&&<ul role="menu" aria-labelledby="workspace-label" className="dropdown-content menu z-50 mb-2 w-full rounded-box border border-base-300 bg-base-200 p-1" onKeyDown={onMenuKey}>{options.map(([id,label])=><li key={id} role="none"><button type="button" role="menuitemradio" aria-checked={id===workspace} data-workspace={id} tabIndex={-1} className="min-h-11 justify-between" onClick={()=>choose(id)}>{label}{id===workspace&&<CheckIcon aria-hidden="true" className="size-4"/>}</button></li>)}</ul>}
  </div>
 </div>;
}
