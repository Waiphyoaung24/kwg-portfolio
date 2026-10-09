import type { CSSProperties } from 'react';
import { milestones,daysUntil,goals,pipeline,conversations,niches,STAGES,NICHE_CHECKS } from '../shared/goal-model.js';
import { today,week,linkTo,scoped,workspace } from './notes';
import type { Note } from './types';

type OnNew=(kind:string,name?:string,opener?:HTMLElement,template?:string)=>void;
type Lead={note:Note;name:string;stage:string;mrr:number|null;nextAction:string;nextDate:string|null;warnings:string[]};
const muted='text-base-content/70',cardTitle='text-base font-semibold leading-6',card='card border border-base-300 bg-base-200',CONVERSATION_TARGET=20;
const shortDate=(d:string)=>new Date(d+'T12:00:00Z').toLocaleDateString('en',{day:'numeric',month:'short',timeZone:'UTC'});
const money=(n:number)=>'$'+n.toLocaleString('en');
const SHORT:Record<string,string>={problem_words:'Words',experience:'Experience',buyers:'Buyers',underserved:'Underserved',ship_fast:'2 weeks'};
const stageLabel=(s:string)=>s[0].toUpperCase()+s.slice(1);

export function MilestoneBadge(){const m=milestones(today);return <p className="px-2"><span className="badge badge-primary h-auto py-1 whitespace-normal">{m.ended?'Goal period ended':`${m.list[m.current].id} ${m.list[m.current].title} · ${m.daysLeft}d left`}</span></p>;}

export function GoalSummary({notes,onNew}:{notes:Note[];onNew:OnNew}){
 const g=goals(notes),m=milestones(today);
 if(!g)return workspace==='personal'?<section className={card+' goal-setup'} aria-labelledby="goal-heading"><div className="card-body gap-4 p-5 sm:p-6 flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between"><h2 id="goal-heading" className={cardTitle}>Set your 2026 goal</h2><button type="button" className="btn btn-primary" onClick={e=>onNew('founder','goals-2026',e.currentTarget,'goals')}>Create goal</button></div></section>:null;
 const p=pipeline(notes,today,week) as {won:number;mrr:number},c=conversations(notes),left=daysUntil(today,g.deadline);
 const pct=(v:number,t:number)=>t>0?Math.min(100,Math.round(v/t*100)):0;
 return <section className="goal-summary grid grid-cols-1 gap-4" aria-labelledby="goal-heading">
  <h2 id="goal-heading" className="sr-only">2026 goal progress</h2>
  {m.ended?<div role="status" className="alert alert-soft"><span>Goal ended. <a className="link" href={scoped('/review')}>Q4 review</a></span></div>:
  <ol className="steps steps-vertical w-full py-2 sm:steps-horizontal" aria-label="Milestones">{m.list.map((s,i)=><li key={s.id} className={'step text-sm '+(i<=m.current?'step-primary':'')} aria-current={i===m.current?'step':undefined}><span className="text-start sm:text-center"><b>{s.id} {s.title}</b><span className={'block text-xs '+muted}>{shortDate(s.due)}</span></span></li>)}</ol>}
  <div className="stats stats-vertical w-full border border-base-300 bg-base-200 md:stats-horizontal">
   <div className="stat"><div className="stat-figure"><div className="radial-progress text-primary" style={{'--value':pct(p.won,g.targetClients),'--size':'3.5rem'} as CSSProperties} role="img" aria-label={`${pct(p.won,g.targetClients)}% of client target`}>{pct(p.won,g.targetClients)}%</div></div><div className={'stat-title '+muted}>Retainer clients</div><div className="stat-value text-3xl tabular-nums" id="goal-clients">{p.won} / {g.targetClients}</div><div className={'stat-desc '+muted}>Floor: {g.floorClients} by {shortDate(g.floorDate)}</div></div>
   <div className="stat"><div className={'stat-title '+muted}>Monthly revenue</div><div className="stat-value text-3xl tabular-nums" id="goal-mrr">{money(p.mrr)}</div><div className={'stat-desc '+muted}>Target {money(g.targetMrr)}</div><progress className="progress progress-primary mt-2" value={pct(p.mrr,g.targetMrr)} max={100} aria-label="Monthly revenue progress"/></div>
   <div className="stat"><div className={'stat-title '+muted}>Conversations</div><div className="stat-value text-3xl tabular-nums" id="goal-conversations">{c.total} / {CONVERSATION_TARGET}</div><div className={'stat-desc '+muted}>Target {CONVERSATION_TARGET}</div></div>
   <div className="stat"><div className={'stat-title '+muted}>Weeks left</div><div className="stat-value text-3xl tabular-nums">{left>0?Math.ceil(left/7):0}</div><div className={'stat-desc '+muted}>Deadline {shortDate(g.deadline)}</div></div>
  </div>
 </section>;
}

export function LeadFollowUps({notes}:{notes:Note[]}){const overdue=(pipeline(notes,today,week) as {overdue:Lead[]}).overdue;
 return <section className={card+' h-full'} aria-labelledby="followups-heading"><div className="card-body gap-4 p-5 sm:p-6"><div className="flex items-center justify-between gap-3"><h2 id="followups-heading" className={cardTitle}>Lead follow-ups</h2><span className="badge badge-soft badge-error">{overdue.length} overdue</span></div>{overdue.length?overdue.slice(0,8).map(l=><a key={l.note.path} className="task-row flex min-h-11 flex-col border-b border-base-300 py-3 text-sm last:border-0 hover:underline" href={linkTo(l.note)}>{l.nextAction||'Follow up with '+l.name}<small className={'text-xs '+muted}>{l.name} · due {shortDate(l.nextDate!)}</small></a>):null}</div></section>;}

export function Pipeline({notes,onNew}:{notes:Note[];onNew:OnNew}){
 const p=pipeline(notes,today,week) as {stages:Record<string,Lead[]>;leads:Lead[];contactedThisWeek:number};
 return <section className={card+' pipeline'} aria-labelledby="pipeline-heading"><div className="card-body gap-4 p-5 sm:p-6 min-w-0">
  <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 id="pipeline-heading" className={cardTitle}>Lead pipeline</h2><p className={'text-sm '+muted}>{p.leads.length} {p.leads.length===1?'lead':'leads'} · {p.contactedThisWeek} contacted this week</p></div><button type="button" className="btn btn-outline btn-sm" onClick={e=>onNew('founder','',e.currentTarget,'lead')}>Add a lead</button></div>
  {p.leads.length?<div className="-mx-2 overflow-x-auto px-2 pb-2"><div className="grid auto-cols-[minmax(11rem,1fr)] grid-flow-col gap-3">{STAGES.map(stage=><div key={stage} className="min-w-0 rounded-box bg-base-100 p-3" aria-labelledby={'stage-'+stage}>
   <h3 id={'stage-'+stage} className="mb-3 flex items-center justify-between text-sm">{stageLabel(stage)}<span className="badge badge-ghost badge-sm">{p.stages[stage].length}</span></h3>
   <ul className="grid gap-2">{p.stages[stage].map(l=><li key={l.note.path}><a className="lead-card card card-sm border border-base-300 bg-base-200 hover:border-primary" href={linkTo(l.note)} data-stage={l.stage}><div className="card-body gap-1"><b className="text-sm break-words">{l.name}</b>{l.stage==='won'&&l.mrr!==null&&<span className="text-xs text-success">{money(l.mrr)}/month</span>}{l.nextAction&&<span className={'text-xs '+muted}>{l.nextAction}</span>}{l.nextDate&&<span className={'text-xs '+(l.nextDate<today&&!['won','lost'].includes(l.stage)?'text-error':muted)}>{l.nextDate<today&&!['won','lost'].includes(l.stage)?'Overdue: ':'Next: '}{shortDate(l.nextDate)}</span>}{l.warnings.length>0&&<span className="badge badge-warning badge-sm" title={l.warnings.join(', ')}>Check fields</span>}</div></a></li>)}</ul>
  </div>)}</div></div>:null}
 </div></section>;
}

export function Validation({notes,onNew}:{notes:Note[];onNew:OnNew}){
 const n=niches(notes) as {note:Note;name:string;verdict:string;checks:{key:string;label:string;result:string}[]}[],c=conversations(notes);
 const badge=(v:string)=><span className={'badge badge-sm '+(v==='pass'?'badge-success':v==='fail'?'badge-error':'badge-ghost')}>{v?stageLabel(v):'Open'}</span>;
 return <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]">
  <section className={card+' h-full'} aria-labelledby="niche-heading"><div className="card-body gap-4 p-5 sm:p-6 min-w-0"><div className="flex flex-wrap items-center justify-between gap-3"><h2 id="niche-heading" className={cardTitle}>Niche validation</h2><button type="button" className="btn btn-outline btn-sm" onClick={e=>onNew('founder','',e.currentTarget,'niche')}>Validate a niche</button></div>
   {n.length?<div className="overflow-x-auto"><table className="table table-sm"><thead><tr><th scope="col">Niche</th>{NICHE_CHECKS.map(([key,label])=><th key={key} scope="col" className="font-normal"><abbr title={label}>{SHORT[key]}</abbr></th>)}<th scope="col">Verdict</th></tr></thead><tbody>{n.map(x=><tr key={x.note.path}><th scope="row"><a className="link" href={linkTo(x.note)}>{x.name}</a></th>{x.checks.map(k=><td key={k.key}>{badge(k.result)}</td>)}<td>{badge(x.verdict)}</td></tr>)}</tbody></table></div>:null}
  </div></section>
  <section className={card+' h-full'} aria-labelledby="conversation-heading"><div className="card-body gap-4 p-5 sm:p-6"><div className="flex items-center justify-between gap-3"><h2 id="conversation-heading" className={cardTitle}>Customer conversations</h2><span className="badge badge-ghost" id="conversation-count">{c.total} / {CONVERSATION_TARGET}</span></div>
   <progress className="progress progress-primary" value={Math.min(c.total,CONVERSATION_TARGET)} max={CONVERSATION_TARGET} aria-label="Conversations toward 20"/>
   <p className={'text-sm '+muted}>Would pay: {c.wouldPay.yes} yes, {c.wouldPay.maybe} maybe, {c.wouldPay.no} no.</p>
   {Object.keys(c.byNiche).length>0&&<ul className="text-sm">{Object.entries(c.byNiche).map(([k,v])=><li key={k} className="flex justify-between border-b border-base-300 py-2 last:border-0"><span className="break-words">{k}</span><span>{v as number}</span></li>)}</ul>}
   <button type="button" className="btn btn-outline btn-sm self-start" onClick={e=>onNew('inbox','',e.currentTarget,'conversation')}>Log a conversation</button>
  </div></section>
 </div>;
}
