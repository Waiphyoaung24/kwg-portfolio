import {properties,validDate} from './vault-model.js';
// 2026 one-person-company plan: milestone dates match the GitHub milestones M1-M4.
export const MILESTONES=[{id:'M1',title:'Niche',due:'2026-10-24'},{id:'M2',title:'Offer',due:'2026-11-07'},{id:'M3',title:'First clients',due:'2026-12-05'},{id:'M4',title:'Retainers + systems',due:'2026-12-31'}];
export const STAGES=['lead','contacted','call','proposal','won','lost'];
export const NICHE_CHECKS=[['problem_words',"Problem in the customer's own words"],['experience','6+ months firsthand experience'],['buyers','10 people who would pay now'],['underserved','Underserved market'],['ship_fast','Minimum version in 2 weeks or less']];
const days=(from,to)=>Math.round((Date.parse(to+'T12:00:00Z')-Date.parse(from+'T12:00:00Z'))/86400000);
const amount=value=>{const n=Number(value);return value!==undefined&&value!==''&&Number.isFinite(n)&&n>=0?n:null;};
const typed=(notes,type,folder)=>notes.filter(n=>(!folder||n.path.startsWith(folder+'/'))&&properties(n.content).type===type);
const fileName=n=>n.path.split('/').pop().slice(0,-3);
export function milestones(today){const current=MILESTONES.findIndex(m=>today<=m.due);return current<0?{list:MILESTONES,current:MILESTONES.length,daysLeft:0,ended:true}:{list:MILESTONES,current,daysLeft:days(today,MILESTONES[current].due),ended:false};}
export const daysUntil=days;
export function goals(notes){const note=typed(notes,'goals','founder')[0];if(!note)return null;const p=properties(note.content);return {note,targetClients:amount(p.target_clients)??4,floorClients:amount(p.floor_clients)??1,floorDate:validDate(p.floor_date)?p.floor_date:'2026-12-05',targetMrr:amount(p.target_mrr)??3200,deadline:validDate(p.deadline)?p.deadline:'2026-12-31'};}
export function pipeline(notes,today,week){
 const stages=Object.fromEntries(STAGES.map(s=>[s,[]])),leads=typed(notes,'lead','founder').map(note=>{const p=properties(note.content),warnings=[];
  const stage=STAGES.includes(p.stage)?p.stage:(warnings.push('Unknown stage'),'lead');
  const mrr=amount(p.mrr);if(p.mrr&&mrr===null)warnings.push('Invalid mrr');
  const nextDate=validDate(p.next_date)?p.next_date:null;if(p.next_date&&!nextDate)warnings.push('Invalid next_date');
  return {note,name:p.name||fileName(note),stage,mrr,nextAction:p.next_action||'',nextDate,contacted:validDate(p.contacted)?p.contacted:null,warnings};});
 for(const lead of leads)stages[lead.stage].push(lead);
 return {stages,leads,won:stages.won.length,mrr:stages.won.reduce((sum,l)=>sum+(l.mrr??0),0),
  overdue:leads.filter(l=>l.nextDate&&l.nextDate<today&&!['won','lost'].includes(l.stage)).sort((a,b)=>a.nextDate.localeCompare(b.nextDate)),
  contactedThisWeek:leads.filter(l=>l.contacted&&l.contacted>=week&&l.contacted<=today).length};
}
export function conversations(notes){const byNiche={},wouldPay={yes:0,no:0,maybe:0},items=typed(notes,'conversation');for(const n of items){const p=properties(n.content),niche=p.niche||'Unspecified';byNiche[niche]=(byNiche[niche]||0)+1;wouldPay[['yes','no'].includes(p.would_pay)?p.would_pay:'maybe']++;}return {total:items.length,byNiche,wouldPay};}
export function niches(notes){return typed(notes,'niche','founder').map(note=>{const p=properties(note.content);return {note,name:fileName(note),verdict:['pass','fail'].includes(p.verdict)?p.verdict:'pending',checks:NICHE_CHECKS.map(([key,label])=>({key,label,result:['pass','fail'].includes(p[key])?p[key]:''}))};});}
