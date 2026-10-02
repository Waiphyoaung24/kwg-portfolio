import {test} from 'node:test';
import assert from 'node:assert/strict';
import {wikiLinks,resolveLink,buildGraph,filterGraph,layoutGraph} from './shared/graph-model.js';
const note=(path,content)=>({path,content,version:'test',modified:'2026-10-01'});
test('graph resolves aliases, headings, paths, duplicates and missing links without inventing files',()=>{
 const notes=[note('knowledge/Alpha.md','# Alpha\n[[Beta|Display]] [[Beta#Heading]] [[Missing]] [[Duplicate]]\n`[[Inline]]`\n```md\n[[Code]]\n```'),note('projects/Beta.md','# Beta\n[[knowledge/Alpha.md]]'),note('journal/Duplicate.md','# Duplicate'),note('projects/Duplicate.md','# Duplicate'),note('knowledge/Alone.md','# Alone')];
 const g=buildGraph(notes);assert.equal(g.nodes.length,7);assert.equal(g.edges.length,4);assert.equal(g.nodes.find(n=>n.label==='Missing').kind,'missing');assert.equal(g.nodes.find(n=>n.id==='unresolved:duplicate').kind,'ambiguous');
 assert.equal(resolveLink(notes,'knowledge/Alpha.md','Beta#Heading|Name').path,'projects/Beta.md');assert.equal(resolveLink(notes,'knowledge/Alpha.md','Duplicate'),null);assert.equal(resolveLink(notes,'projects/Beta.md','Duplicate').path,'projects/Duplicate.md');assert.equal(resolveLink(notes,'knowledge/Alpha.md','#Heading').path,'knowledge/Alpha.md');
 assert.deepEqual(wikiLinks('![[image.png]] `[[code]]` \\[[escaped]] [[Real|Label]]').map(l=>l.target),['Real']);
 assert.equal(filterGraph(g,{showOrphans:false,showUnresolved:false}).nodes.length,2);assert.equal(filterGraph(g,{localId:'knowledge/Alpha.md'}).nodes.length,4);assert.equal(filterGraph(g,{query:'Alone'}).nodes.length,1);assert.equal(filterGraph(g,{limit:2}).limited,true);
});
test('graph handles empty, isolated and bounded deterministic layout',()=>{
 assert.deepEqual(buildGraph([]),{nodes:[],edges:[]});const g=buildGraph([note('knowledge/Single.md','# Single')]);assert.equal(filterGraph(g,{showOrphans:false}).nodes.length,0);assert.equal(layoutGraph(g).length,1);
 const many=buildGraph(Array.from({length:160},(_,i)=>note(`knowledge/Note ${i}.md`,`# Note ${i}`)));const filtered=filterGraph(many);assert.equal(filtered.nodes.length,150);assert.equal(filtered.matched,160);const layout=layoutGraph(filtered);assert.deepEqual(layoutGraph(filtered),layout);assert.ok(layout.every(n=>Number.isFinite(n.x)&&Number.isFinite(n.y)&&n.x>=48&&n.x<=852&&n.y>=48&&n.y<=432));
});
