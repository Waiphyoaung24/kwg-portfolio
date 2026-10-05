import {useEffect,useMemo,useRef,useState} from 'react';
import {Button} from './components/ui/button';
import {Input} from './components/ui/input';
import {Label} from './components/ui/label';
import {NativeSelect,NativeSelectOption} from './components/ui/native-select';
import {Icon} from './Icon';
import {buildGraph,filterGraph,layoutGraph} from '../shared/graph-model.js';
import type {Note} from './types';

type GraphNode={id:string;label:string;kind:string;path:string|null;targets:string[]};
type Edge={source:string;target:string};
type Graph={nodes:GraphNode[];edges:Edge[]};
const geometry={width:900,height:480,radius:6,hit:22,label:24,zoomMin:.5,zoomMax:3,zoomStep:1.2,pan:32,drag:4};
export function NoteGraph({notes,activePath,onOpen}:{notes:Note[];activePath:string|null;onOpen:(path:string)=>boolean}){
 const [canvasScale,setCanvasScale]=useState(1);
 const [query,setQuery]=useState(''),[mode,setMode]=useState('all'),[center,setCenter]=useState(''),[orphans,setOrphans]=useState(true),[unresolved,setUnresolved]=useState(true),[hovered,setHovered]=useState<string|null>(null),[notice,setNotice]=useState(''),[view,setView]=useState({x:0,y:0,zoom:1});
 const stage=useRef<HTMLDivElement>(null),drag=useRef<{x:number;y:number;vx:number;vy:number}|null>(null),moved=useRef(false);
 const graph=useMemo(()=>buildGraph(notes) as Graph,[notes]);
 const localId=notes.some(n=>n.path===center)?center:notes.some(n=>n.path===activePath)?activePath:notes[0]?.path||null;
 const filtered=useMemo(()=>filterGraph(graph,{query,showOrphans:orphans,showUnresolved:unresolved,localId:mode==='local'?localId:null}),[graph,query,orphans,unresolved,mode,localId]);
 const points=useMemo(()=>layoutGraph(filtered) as (GraphNode&{x:number;y:number})[],[filtered]),positions=new Map(points.map(n=>[n.id,n]));
 const focus=hovered||activePath,neighbors=new Set<string>();if(focus){neighbors.add(focus);for(const e of filtered.edges){if(e.source===focus)neighbors.add(e.target);if(e.target===focus)neighbors.add(e.source);}}
 const zoom=(factor:number)=>setView(v=>({...v,zoom:Math.max(geometry.zoomMin,Math.min(geometry.zoomMax,v.zoom*factor))}));
 useEffect(()=>{const el=stage.current;if(!el)return;const resize=()=>{setCanvasScale(Math.max(.1,Math.min(el.clientWidth/geometry.width,el.clientHeight/geometry.height)));};resize();const observer=new ResizeObserver(resize);observer.observe(el);return()=>observer.disconnect();},[points.length]);
 useEffect(()=>{const el=stage.current;if(!el)return;const wheel=(e:WheelEvent)=>{if(document.activeElement!==el)return;e.preventDefault();zoom(e.deltaY<0?geometry.zoomStep:1/geometry.zoomStep);};el.addEventListener('wheel',wheel,{passive:false});return()=>el.removeEventListener('wheel',wheel);},[points.length]);
 const reset=()=>setView({x:0,y:0,zoom:1});
 function open(node:GraphNode){if(node.path){if(onOpen(node.path))setNotice('Opened '+node.label+'.');}else setNotice(node.kind==='ambiguous'?`"${node.label}" matches more than one note. Use a folder-qualified link, such as [[knowledge/Note title]], to choose a target.`:`"${node.label}" has not been created. Use New note to create it, then save. No file was created by selecting this node.`);}
 function relationships(id:string){const describe=(target:string)=>{const n=positions.get(target);return n?`${n.label}${n.kind==='missing'?' (not created)':n.kind==='ambiguous'?' (ambiguous link)':''}`:target;};const outgoing=filtered.edges.filter((e:Edge)=>e.source===id).map((e:Edge)=>describe(e.target)),incoming=filtered.edges.filter((e:Edge)=>e.target===id).map((e:Edge)=>describe(e.source));return outgoing.length||incoming.length?`Visible links to: ${outgoing.join(', ')||'none'}. Linked from: ${incoming.join(', ')||'none'}.`:'No visible connections.';}
 const connected=graph.edges.length>0;
 return <section className="panel note-graph" aria-labelledby="graph-heading"><div className="panel-head"><div><h2 id="graph-heading">Note graph</h2><p>Explore links between saved notes across your vault.</p></div><Icon name="network"/></div>
 {!notes.length?<div className="graph-empty"><h3>No saved notes to show</h3><p>Create and save two notes, then add <code>[[Other note title]]</code> to one of them and save again. Their connection will appear here.</p><p>This is Dot's graph, separate from Obsidian's native Graph view.</p></div>:<>
 <div className="graph-controls"><div><Label htmlFor="graph-search">Filter graph by title or path</Label><Input id="graph-search" type="search" value={query} onInput={e=>setQuery(e.currentTarget.value)} placeholder="Find a note"/></div><div><Label htmlFor="graph-mode">View</Label><NativeSelect id="graph-mode" value={mode} onChange={e=>{setMode(e.currentTarget.value);reset();}}><NativeSelectOption value="all">All notes</NativeSelectOption><NativeSelectOption value="local">Local connections</NativeSelectOption></NativeSelect></div>{mode==='local'&&<div><Label htmlFor="graph-center">Center note</Label><NativeSelect id="graph-center" value={localId||''} onChange={e=>{setCenter(e.currentTarget.value);reset();}}>{graph.nodes.filter(n=>n.path).map(n=><NativeSelectOption key={n.id} value={n.id}>{n.label} ({n.path})</NativeSelectOption>)}</NativeSelect></div>}</div>
 <div className="graph-options"><Label><input id="graph-orphans" type="checkbox" checked={orphans} onChange={e=>setOrphans(e.currentTarget.checked)}/>Show unlinked notes</Label><Label><input id="graph-unresolved" type="checkbox" checked={unresolved} onChange={e=>setUnresolved(e.currentTarget.checked)}/>Show unresolved links</Label></div>
 <div className="graph-toolbar" aria-label="Graph controls"><Button variant="outline" aria-label="Zoom in" onClick={()=>zoom(geometry.zoomStep)}>Zoom in</Button><Button variant="outline" aria-label="Zoom out" onClick={()=>zoom(1/geometry.zoomStep)}>Zoom out</Button><Button variant="outline" onClick={reset}>Reset view</Button><span aria-live="polite">{Math.round(view.zoom*100)}%</span><span id="graph-count" role="status">{filtered.nodes.length} {filtered.nodes.length===1?'node':'nodes'}, {filtered.edges.length} {filtered.edges.length===1?'link':'links'}</span></div>
 <p id="graph-help" className="graph-help">Select a saved note to open it. Unresolved links show an explanation. Drag the background to pan. Focus the graph to use arrow keys to pan, the wheel or + and - to zoom, and 0 to reset. The note list below includes the connections and opening actions.</p>
 {mode==='local'&&<p className="graph-help">Local view shows the center note and its direct incoming and outgoing connections.</p>}
 {!connected&&<p className="graph-help">No connections yet. Add <code>[[Other note title]]</code> to a note and save to connect it.</p>}
 {filtered.limited&&<p role="status">Showing the first 150 of {filtered.matched} matching nodes. Use the filter or local view to narrow the graph.</p>}
 {!filtered.nodes.length?<div className="graph-empty"><p>No nodes match these filters. Clear the search or show unlinked notes and unresolved links.</p></div>:<>
 <div ref={stage} id="graph-stage" className="graph-stage" role="group" aria-label="Note graph pan and zoom" aria-describedby="graph-help" tabIndex={0} onKeyDown={e=>{const steps:Record<string,[number,number]>={ArrowLeft:[geometry.pan,0],ArrowRight:[-geometry.pan,0],ArrowUp:[0,geometry.pan],ArrowDown:[0,-geometry.pan]};if(steps[e.key]){e.preventDefault();const [x,y]=steps[e.key];setView(v=>({...v,x:v.x+x,y:v.y+y}));}else if(['+','=','-','0'].includes(e.key)){e.preventDefault();if(e.key==='0')reset();else zoom(e.key==='-'?1/geometry.zoomStep:geometry.zoomStep);}}}
 onPointerDown={e=>{moved.current=false;if((e.target as Element).closest('[data-graph-node]'))return;stage.current?.focus({preventScroll:true});drag.current={x:e.clientX,y:e.clientY,vx:view.x,vy:view.y};e.currentTarget.setPointerCapture(e.pointerId);}}
 onPointerMove={e=>{const origin=drag.current;if(!origin)return;const dx=e.clientX-origin.x,dy=e.clientY-origin.y;if(Math.hypot(dx,dy)>geometry.drag)moved.current=true;const rect=e.currentTarget.getBoundingClientRect(),scale=Math.min(rect.width/geometry.width,rect.height/geometry.height);setView(v=>({...v,x:origin.vx+dx/scale,y:origin.vy+dy/scale}));}}
 onPointerUp={e=>{drag.current=null;if(e.currentTarget.hasPointerCapture(e.pointerId))e.currentTarget.releasePointerCapture(e.pointerId);}} onPointerCancel={()=>{drag.current=null;}}>
 <svg viewBox={`0 0 ${geometry.width} ${geometry.height}`} aria-hidden="true"><g data-graph-transform transform={`translate(${geometry.width/2+view.x} ${geometry.height/2+view.y}) scale(${view.zoom}) translate(${-geometry.width/2} ${-geometry.height/2})`}>
 {filtered.edges.map((edge:Edge)=>{const a=positions.get(edge.source),b=positions.get(edge.target);return a&&b?<line key={edge.source+'>'+edge.target} data-graph-edge className={`graph-edge ${focus&&(edge.source===focus||edge.target===focus)?'highlight':''}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y}/>:null;})}
 {points.map(node=><g key={node.id} data-graph-node={node.id} className={`graph-node ${node.kind} ${focus===node.id?'selected':''} ${hovered&&!neighbors.has(node.id)?'dim':''}`} transform={`translate(${node.x} ${node.y})`} onPointerEnter={()=>setHovered(node.id)} onPointerLeave={()=>setHovered(null)} onClick={()=>{if(!moved.current)open(node);}}><title>{node.label}{node.kind==='note'?'':node.kind==='missing'?' (not created)':' (ambiguous link)'}</title><circle className="graph-hit" r={geometry.hit/(canvasScale*view.zoom)}/><circle className="graph-dot" r={geometry.radius}/><text y={geometry.label} textAnchor="middle">{node.label.length>28?node.label.slice(0,25)+'...':node.label}{node.kind==='note'?'':' ?'}</text></g>)}
 </g></svg></div>
 <p className="graph-help">Solid nodes are saved notes. Dashed nodes are missing or ambiguous targets. This is Dot's graph, separate from Obsidian's native Graph view.</p>
 <details className="graph-list" open><summary>Notes in this graph ({points.length})</summary><ul>{points.map(node=><li key={node.id}><Button variant="ghost" className="graph-note-button block h-auto whitespace-normal" data-graph-open={node.id} onFocus={()=>setHovered(node.id)} onBlur={()=>setHovered(null)} onClick={()=>open(node)}><span>{node.label}</span><small>{node.path|| (node.kind==='missing'?'Not created':'Ambiguous link')}</small></Button><p className="graph-relations">{relationships(node.id)}</p></li>)}</ul></details>
 </>}
 <p id="graph-notice" role="status" className="graph-help">{notice}</p>
 </>}
 </section>;
}
