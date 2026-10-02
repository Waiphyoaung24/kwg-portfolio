// Shared, read-only wikilink model. No file writes or dependency on Obsidian plugins.
export const graphTitle=n=>n.content.match(/^#\s+(.+)$/m)?.[1]||n.path.split('/').pop().replace(/\.md$/i,'');
const key=s=>s.replace(/\\/g,'/').replace(/^\.\//,'').replace(/\.md$/i,'').trim().toLowerCase();
export function wikiLinks(content){
 let fence=null;
 return content.split(/\r?\n/).flatMap(line=>{
  const marker=line.match(/^\s*(`{3,}|~{3,})/);
  if(marker){if(!fence)fence=marker[1][0];else if(fence===marker[1][0])fence=null;return [];}
  if(fence)return [];
  const plain=line.replace(/(`+)[\s\S]*?\1/g,'');
  return [...plain.matchAll(/(?<!!|\\)\[\[([^\]\n]+)\]\]/g)].map(m=>{const [raw,label]=m[1].split('|'),target=raw.split('#')[0].trim();return {target,label:label?.trim()||target,raw:m[1]};});
 });
}
export function resolveLink(notes,sourcePath,target){
 const clean=target.split('|')[0].split('#')[0].trim();
 if(!clean)return notes.find(n=>n.path===sourcePath)||null;
 const normalized=key(clean),exact=notes.filter(n=>key(n.path)===normalized);
 if(exact.length===1)return exact[0];
 const relative=notes.filter(n=>key(n.path)===key(sourcePath.slice(0,sourcePath.lastIndexOf('/')+1)+clean));
 if(relative.length===1)return relative[0];
 const matches=notes.filter(n=>key(n.path.split('/').pop())===normalized||key(graphTitle(n))===normalized);
 return matches.length===1?matches[0]:null;
}
export function buildGraph(notes){
 const nodes=notes.map(n=>({id:n.path,label:graphTitle(n),kind:'note',path:n.path,targets:[]})),edges=[],seen=new Set(),byId=new Map(nodes.map(n=>[n.id,n]));
 for(const note of notes)for(const link of wikiLinks(note.content)){
  const resolved=resolveLink(notes,note.path,link.target);
  if(resolved?.path===note.path)continue;
  let id=resolved?.path;
  if(!id){
   const k=key(link.target);if(!k)continue;
   const candidates=notes.filter(n=>key(n.path.split('/').pop())===k||key(graphTitle(n))===k);
   id='unresolved:'+k;
   if(!byId.has(id)){const node={id,label:link.target,kind:candidates.length>1?'ambiguous':'missing',path:null,targets:candidates.map(n=>n.path)};byId.set(id,node);nodes.push(node);}
  }
  const pair=note.path+'\0'+id;
  if(!seen.has(pair)){seen.add(pair);edges.push({source:note.path,target:id});}
 }
 return {nodes,edges};
}
/** @param {any} graph @param {{query?:string,showOrphans?:boolean,showUnresolved?:boolean,localId?:string|null,limit?:number}} options */
export function filterGraph(graph,{query='',showOrphans=true,showUnresolved=true,localId=null,limit=150}={}){
 const degree=new Map(graph.nodes.map(n=>[n.id,0]));
 for(const e of graph.edges){degree.set(e.source,(degree.get(e.source)||0)+1);degree.set(e.target,(degree.get(e.target)||0)+1);}
 const neighbors=localId?new Set([localId]):null;
 if(neighbors)for(const e of graph.edges){if(e.source===localId)neighbors.add(e.target);if(e.target===localId)neighbors.add(e.source);}
 const term=query.trim().toLowerCase(),matched=graph.nodes.filter(n=>(!neighbors||neighbors.has(n.id))&&(showOrphans||degree.get(n.id)>0)&&(showUnresolved||n.kind==='note')&&(!term||(n.label+' '+(n.path||'')).toLowerCase().includes(term))).sort((a,b)=>a.id.localeCompare(b.id));
 const nodes=matched.slice(0,limit),ids=new Set(nodes.map(n=>n.id));
 return {nodes,edges:graph.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)),matched:matched.length,limited:matched.length>limit};
}
export function layoutGraph(graph){
 // ponytail: bounded deterministic force layout, computed once per filtered graph.
 // 150 visible nodes keeps quadratic repulsion bounded; use a worker/spatial tree for larger views.
 const nodes=graph.nodes.map((n,i)=>{const angle=i*2.3999632297,r=Math.sqrt(i+1)*19;return {...n,x:450+Math.cos(angle)*r,y:240+Math.sin(angle)*r};}),byId=new Map(nodes.map(n=>[n.id,n]));
 for(let step=0;step<90;step++){
  const forces=nodes.map(n=>({x:(450-n.x)*.012,y:(240-n.y)*.012})),indices=new Map(nodes.map((n,i)=>[n.id,i]));
  for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){const dx=nodes[i].x-nodes[j].x,dy=nodes[i].y-nodes[j].y,d2=Math.max(dx*dx+dy*dy,100),f=1500/d2;forces[i].x+=dx*f;forces[i].y+=dy*f;forces[j].x-=dx*f;forces[j].y-=dy*f;}
  for(const edge of graph.edges){const a=byId.get(edge.source),b=byId.get(edge.target);if(!a||!b)continue;const dx=b.x-a.x,dy=b.y-a.y,d=Math.max(Math.hypot(dx,dy),1),f=(d-100)*.02/d;forces[indices.get(a.id)].x+=dx*f;forces[indices.get(a.id)].y+=dy*f;forces[indices.get(b.id)].x-=dx*f;forces[indices.get(b.id)].y-=dy*f;}
  for(let i=0;i<nodes.length;i++){nodes[i].x=Math.min(852,Math.max(48,nodes[i].x+Math.max(-8,Math.min(8,forces[i].x))));nodes[i].y=Math.min(432,Math.max(48,nodes[i].y+Math.max(-8,Math.min(8,forces[i].y))));}
 }
 return nodes;
}
