import {test} from 'node:test';import assert from 'node:assert/strict';
import {MILESTONES,STAGES,milestones,goals,pipeline,conversations,niches} from './shared/goal-model.js';
import {makeTemplate,properties} from './shared/vault-model.js';
const note=(path,content)=>({path,content,modified:'2026-10-01T00:00:00Z',version:'v'});
const front=fields=>`---\n${Object.entries(fields).map(([k,v])=>`${k}: ${v}`).join('\n')}\n---\n\n# Note\n`;

test('milestones pick the first milestone not yet past and count days left',()=>{
 assert.deepEqual(MILESTONES.map(m=>m.due),['2026-10-24','2026-11-07','2026-12-05','2026-12-31']);
 assert.deepEqual([milestones('2026-10-10').current,milestones('2026-10-10').daysLeft],[0,14]);
 assert.deepEqual([milestones('2026-10-24').current,milestones('2026-10-24').daysLeft],[0,0]);
 assert.equal(milestones('2026-10-25').current,1);
 assert.deepEqual([milestones('2026-12-31').current,milestones('2026-12-31').ended],[3,false]);
 const after=milestones('2027-01-01');assert.equal(after.ended,true);assert.equal(after.daysLeft,0);
});

test('goals read the founder goals note and fall back to plan defaults for bad values',()=>{
 assert.equal(goals([]),null);
 assert.equal(goals([note('knowledge/Goals.md',front({type:'goals'}))]),null,'Goals outside founder/ are ignored');
 const g=goals([note('founder/goals-2026.md',front({type:'goals',target_clients:3,target_mrr:'abc',deadline:'2026-02-31'}))]);
 assert.equal(g.targetClients,3);assert.equal(g.targetMrr,3200);assert.equal(g.deadline,'2026-12-31');assert.equal(g.floorClients,1);assert.equal(g.floorDate,'2026-12-05');
 const fromTemplate=goals([note('founder/goals-2026.md',makeTemplate('goals','goals-2026','2026-10-10'))]);
 assert.deepEqual([fromTemplate.targetClients,fromTemplate.targetMrr,fromTemplate.deadline],[4,3200,'2026-12-31']);
});

test('pipeline groups founder leads by stage, sums won MRR, and flags bad fields',()=>{
 const ns=[
  note('founder/Ana.md',front({type:'lead',name:'Ana',stage:'won',mrr:800,contacted:'2026-10-06'})),
  note('founder/Ben.md',front({type:'lead',stage:'won',mrr:'eight hundred'})),
  note('founder/Cy.md',front({type:'lead',stage:'call',next_date:'2026-10-01',contacted:'2026-10-07'})),
  note('founder/Di.md',front({type:'lead',stage:'maybe',next_date:'2026-13-01'})),
  note('founder/Ed.md',front({type:'lead',stage:'lost',next_date:'2026-09-01',contacted:'2026-09-01'})),
  note('inbox/Fa.md',front({type:'lead',stage:'won',mrr:800})),
  note('founder/Plan.md',front({type:'goals'})),
 ];
 const p=pipeline(ns,'2026-10-10','2026-10-06');
 assert.deepEqual(Object.keys(p.stages),STAGES);
 assert.equal(p.leads.length,5,'Only founder/ lead notes count');
 assert.equal(p.won,2);assert.equal(p.mrr,800,'Invalid MRR is excluded from totals');
 assert.deepEqual(p.stages.lead.map(l=>l.name),['Di'],'Unknown stage falls back to lead');
 assert.deepEqual(p.overdue.map(l=>l.name),['Cy'],'Lost leads and invalid dates are never overdue');
 assert.equal(p.contactedThisWeek,2);
 assert.equal(p.leads.find(l=>l.name==='Ana').name,'Ana');
 assert.deepEqual(p.leads.find(l=>l.name==='Ben').warnings,['Invalid mrr']);
 assert.deepEqual(p.leads.find(l=>l.name==='Di').warnings,['Unknown stage','Invalid next_date']);
 const lead=properties(makeTemplate('lead','New lead','2026-10-10'));
 assert.equal(lead.type,'lead');assert.equal(lead.stage,'lead');assert.equal(lead.name,'New lead');
});

test('conversations and niche validation summarize typed notes',()=>{
 const ns=[
  note('inbox/C1.md',front({type:'conversation',niche:'Clinics',would_pay:'yes'})),
  note('inbox/C2.md',front({type:'conversation',niche:'Clinics',would_pay:'no'})),
  note('founder/C3.md',front({type:'conversation',would_pay:'later'})),
  note('founder/Clinics.md',front({type:'niche',verdict:'pass',problem_words:'pass',experience:'pass',buyers:'pass',underserved:'pass',ship_fast:'pass'})),
  note('founder/Cafes.md',front({type:'niche',verdict:'unsure',buyers:'fail'})),
 ];
 const c=conversations(ns);
 assert.equal(c.total,3);assert.deepEqual(c.byNiche,{Clinics:2,Unspecified:1});assert.deepEqual(c.wouldPay,{yes:1,no:1,maybe:1});
 const n=niches(ns);
 assert.deepEqual(n.map(x=>[x.name,x.verdict]),[['Clinics','pass'],['Cafes','pending']]);
 assert.deepEqual(n[1].checks.map(c=>c.result),['','','fail','','']);
 assert.equal(properties(makeTemplate('conversation','Call','2026-10-10')).type,'conversation');
 assert.equal(properties(makeTemplate('niche','Clinics','2026-10-10')).verdict,'pending');
});
