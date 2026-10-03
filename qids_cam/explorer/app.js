/* All visible research data is read from the embedded, Python-verified archive. */
"use strict";
(() => {
  const data = JSON.parse(document.getElementById("receipt-data").textContent);
  const proof = data.proof, nodes = data.archive.nodes, trace = data.trace;
  const $ = id => document.getElementById(id);
  const safe = value => String(value).replace(/[\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]/g,
    c => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
  const text = (id, value) => { $(id).textContent = safe(value); };
  const displayJSON = value => JSON.stringify(value,null,2).replace(/[\u007f-\u009f\u202a-\u202e\u2066-\u2069]/g,
    c => "\\u" + c.charCodeAt(0).toString(16).padStart(4,"0"));
  const el = (tag, value, className) => {
    const n = document.createElement(tag);
    if (value !== undefined) n.textContent = safe(value);
    if (className) n.className = className;
    return n;
  };
  const svg = (tag, attrs) => {
    const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attrs || {}).forEach(([k,v]) => n.setAttribute(k, v));
    return n;
  };
  const byCID = new Map(data.propositions.map(p => [p.cid,p]));
  let selected = data.propositions.find(p => p.aliases.length > 1)?.cid || data.propositions[0]?.cid || null;
  let selectedCandidate = null, step = trace.length, shownEvents = 100;
  const graphNodes = new Map(), candidateNodes = new Map(), edgeNodes = [];
  const stateAtStep = () => {
    const result = new Map();
    for (const e of trace.slice(0, step)) {
      if (e.status) result.set(e.cid, {status:e.status,score:e.score,reason:e.detail});
      else if (e.event === "expand") result.set(e.cid,{status:"evaluating",score:null,reason:e.detail});
    }
    return result;
  };
  const statusName = value => value === "pending" ? "Not evaluated" : value === "evaluating" ? "Evaluating" : value;
  const label = p => p.aliases[0] || p.cid.slice(7,19);
  const short = (value, limit) => value.length > limit ? value.slice(0,limit-1) + "…" : value;
  text("problem-id", data.problem.id);
  text("query", data.problem.query);
  const meta = data.problem.metadata;
  const synthetic = meta.synthetic === true || /synthetic/i.test(String(meta.note || ""));
  text("evidence-label", synthetic ? "SYNTHETIC FIXTURE · NOT EMPIRICAL MODEL EVIDENCE" : "SUPPLIED EVIDENCE · TRUTH NOT ESTABLISHED");
  text("candidate-count", proof.candidates.length);
  text("identity-count", byCID.size);
  text("reuse-count", proof.metrics.memo_hits + proof.metrics.nogood_hits);
  text("avoided-count", proof.metrics.avoided_requirements);
  text("root", data.archive.root);
  text("context-cid", proof.context);
  $("context-json").textContent = displayJSON(nodes[proof.context_node].payload.constraints);
  $("config-json").textContent = displayJSON(proof.solver);
  $("metrics-json").textContent = displayJSON(proof.metrics);
  $("no-good-summary").append(el("p",
    proof.metrics.learned_nogoods + " learned no-goods · " + proof.metrics.nogood_hits +
    " recorded no-good hits · " + proof.metrics.memo_hits + " memo hits", "small"));
  $("no-good-summary").append(el("p",
    "Counts are from this receipt. Cold-run fixtures have not demonstrated extra work reduction from learning beyond memoizing destroyed states.",
    "small muted"));
  $("step").max = trace.length;
  $("step").value = step;
  for (const kind of [...new Set(trace.map(e => e.event))].sort()) {
    const o = el("option", kind); o.value = kind; $("event-filter").append(o);
  }

  const positions = new Map(), levels = new Map(), depths = new Map();
  function depth(cid) {
    if (depths.has(cid)) return depths.get(cid);
    const p = byCID.get(cid);
    const n = p.dependencies.length ? 1 + Math.max(...p.dependencies.map(depth)) : 0;
    depths.set(cid,n); return n;
  }
  for (const p of [...data.propositions].sort((a,b) => label(a).localeCompare(label(b)))) {
    const d = depth(p.cid);
    if (!levels.has(d)) levels.set(d,[]);
    levels.get(d).push(p);
  }
  const height = Math.max(380, ...[...levels.values()].map(a => a.length * 72 + 48));
  const width = Math.max(530, levels.size * 290 + 28);
  $("graph").setAttribute("viewBox","0 0 " + width + " " + height);
  $("graph").style.height = (height * Math.min(1, 600/width)) + "px";
  const defs = svg("defs"), marker = svg("marker",{id:"arrow",viewBox:"0 0 10 10",
    refX:9,refY:5,markerWidth:6,markerHeight:6,orient:"auto-start-reverse"});
  marker.append(svg("path",{d:"M 0 0 L 10 5 L 0 10 z",fill:"#a3b29c"}));
  defs.append(marker); $("graph").append(defs);
  for (const [d, ps] of levels) {
    ps.forEach((p,i) => positions.set(p.cid,{x:24+d*290,y:24+i*72+(height-ps.length*72-48)/2}));
  }
  for (const p of data.propositions) {
    for (const dep of p.dependencies) {
      const a = positions.get(dep), b = positions.get(p.cid);
      const x = a.x + 240, y = a.y + 28, mid = (x+b.x)/2;
      const line = svg("path",{d:"M "+x+" "+y+" C "+mid+" "+y+", "+mid+" "+(b.y+28)+", "+b.x+" "+(b.y+28),
        class:"edge","marker-end":"url(#arrow)"});
      $("graph").append(line); edgeNodes.push({line,dep,to:p.cid});
    }
  }
  for (const p of data.propositions) {
    const xy = positions.get(p.cid), g = svg("g",{transform:"translate("+xy.x+","+xy.y+")",
      class:"node",tabindex:0,role:"button","data-cid":p.cid,"aria-label":"Inspect " + safe(p.aliases.join(", "))});
    const title = svg("title"); title.textContent = safe(p.statement); g.append(title);
    g.append(svg("rect",{width:240,height:56,rx:5}));
    g.append(svg("circle",{cx:14,cy:18,r:3,class:"state-dot"}));
    const alias = svg("text",{x:24,y:22,class:"node-label"});
    alias.textContent = safe(short(label(p),28)); g.append(alias);
    const caption = svg("text",{x:12,y:42,class:"node-caption"});
    caption.textContent = p.cid.slice(7,19) + " · " + p.aliases.length + (p.aliases.length === 1 ? " alias" : " aliases"); g.append(caption);
    const choose = () => { selected=p.cid; render(); };
    g.addEventListener("click",choose);
    g.addEventListener("keydown",e => {if(e.key==="Enter" || e.key===" "){e.preventDefault();choose();}});
    $("graph").append(g); graphNodes.set(p.cid,g);
  }
  for (const c of proof.candidates) {
    const b = el("button",undefined,"candidate");
    b.append(el("div",c.label,"candidate-title"));
    const status = el("div",undefined,"candidate-status");
    status.append(el("span")); status.append(el("span")); b.append(status);
    b.addEventListener("click",() => { selectedCandidate = selectedCandidate === c.key ? null : c.key; render(); });
    $("candidates").append(b); candidateNodes.set(c.key,b);
  }

  function renderDetail(states) {
    const body = $("node-body"); body.replaceChildren();
    if (!selected) {text("node-title","No propositions in this receipt");return;}
    const p = byCID.get(selected), state = states.get(selected);
    text("node-title",label(p)); text("node-statement",p.statement); text("node-cid",p.cid);
    $("node-status").replaceChildren(el("span",statusName(state?.status || "pending"),"status " + (state?.status || "pending")));
    body.append(el("p","LOCAL ALIASES","eyebrow detail-label"), el("div",p.aliases.join(" · "),"alias-list"));
    body.append(el("p",state ? "Score: " + (state.score === null ? "pending" : state.score.toFixed(6)) + " · " + state.reason : "This identity has not been evaluated by the displayed trace step.","small"));
    const hits = trace.slice(0,step).filter(e=>e.cid===p.cid && /^(memo-hit|nogood-hit)$/.test(e.event));
    body.append(el("p",hits.length + " recorded reuse events by this step.","small"));
    if (state?.status === "destroyed" && proof.solver.learn_nogoods) {
      body.append(el("p","Learned destroyed state under the archived configuration. Its reuse scope is this proposition CID + the context CID + solver configuration.","small"));
    }
    const heading = el("p","DEPENDENCIES","eyebrow detail-label");body.append(heading);
    if (!p.dependencies.length) body.append(el("p","No proposition prerequisites.","small muted"));
    for (const cid of p.dependencies) {
      const b=el("button",label(byCID.get(cid)),"node-link");
      b.addEventListener("click",()=>{selected=cid;render();});body.append(b);
    }
    const evidence = el("details");evidence.append(el("summary",p.evidence.length+" linked evidence observations"));
    for (const cid of p.evidence) {
      const e = nodes[cid].payload;
      evidence.append(el("p",e.text,"small"));
      evidence.append(el("p","Stance " + e.stance + " · supplied confidence " + e.confidence + " · source " + e.source,"small muted"));
      evidence.append(el("code",cid,"cid"));
    }
    body.append(evidence);
    const raw=el("details");raw.append(el("summary","Exact archived node"));
    const pre=el("pre");pre.textContent=displayJSON(nodes[p.cid]);raw.append(pre);body.append(raw);
  }
  function renderTrace() {
    text("step-output",step + " / " + trace.length);
    $("previous").disabled=step===0; $("next").disabled=step===trace.length;
    const e=trace[step-1];
    text("current-event",e ? String(e.step).padStart(3,"0") + " / " + e.event + " / " + e.subject + " — " + e.detail : "Before execution. No proposition or candidate has been evaluated.");
    const events=trace.filter(e=>($("event-filter").value==="all" || e.event===$("event-filter").value) &&
      (!$("selected-only").checked || e.cid===selected));
    const target=$("trace-events");target.replaceChildren();
    for(const e of events.slice(0,shownEvents)){
      const b=el("button",undefined,"trace-event" + (e.step===step?" current":""));
      b.append(el("span",String(e.step).padStart(3,"0")),el("span",e.event),el("small",e.subject+" · "+e.detail));
      b.addEventListener("click",()=>{if(byCID.has(e.cid))selected=e.cid;setStep(e.step);});
      target.append(b);
    }
    if(!events.length)target.append(el("p","No matching recorded events.","small muted"));
    $("more-events").hidden=events.length<=shownEvents;
  }
  function render() {
    const states=stateAtStep(), query=$("search").value.trim().toLowerCase();
    const candidate=proof.candidates.find(c=>c.key===selectedCandidate);
    const related=new Set();
    function collect(cid){if(related.has(cid))return;related.add(cid);byCID.get(cid)?.dependencies.forEach(collect);}
    if(candidate)nodes[candidate.cid].payload.requirements.forEach(collect);
    let matches=0;
    for(const p of data.propositions){
      const found=!query || (p.aliases.join(" ")+" "+p.statement+" "+p.cid).toLowerCase().includes(query);
      if(found)matches++;
      const g=graphNodes.get(p.cid), state=states.get(p.cid);
      g.setAttribute("class","node "+(state?.status||"pending")+(selected===p.cid?" selected":"")+(!found || (candidate&&!related.has(p.cid))?" dim":""));
      g.setAttribute("aria-pressed",String(selected===p.cid));
      g.setAttribute("aria-label","Inspect " + safe(p.aliases.join(", ")) + " · " + statusName(state?.status||"pending"));
    }
    for(const edge of edgeNodes)edge.line.setAttribute("class","edge"+((edge.dep===selected||edge.to===selected)?" active":""));
    for(const c of proof.candidates){
      const b=candidateNodes.get(c.key), state=states.get(c.cid);
      b.className="candidate "+(state?.status||"pending")+(selectedCandidate===c.key?" selected":"");
      b.setAttribute("aria-pressed",String(selectedCandidate===c.key));
      b.querySelector(".candidate-status").children[0].textContent=statusName(state?.status||"pending")+(c.key===proof.winner && step===trace.length?" · winner":"");
      b.querySelector(".candidate-status").children[1].textContent=state?.score===undefined || state?.score===null?"—":state.score.toFixed(3);
    }
    const caption=candidate ? candidate.label + " · final receipt: " + candidate.evaluated_requirements.length +
      " evaluated requirements, " + candidate.skipped_requirements.length + " skipped (" +
      (candidate.skipped_requirements.join(", ") || "none") + "). Select again to show all paths." :
      matches + " matching identities · " + data.propositions.reduce((n,p)=>n+p.aliases.length,0) +
      " local aliases · " + (step===trace.length?"final archived state":"state at step "+step);
    text("graph-caption",caption);renderDetail(states);renderTrace();
  }
  function setStep(value){step=Math.max(0,Math.min(trace.length,Number(value)));$("step").value=step;render();}
  $("step").addEventListener("input",e=>setStep(e.target.value));
  $("previous").addEventListener("click",()=>setStep(step-1));
  $("next").addEventListener("click",()=>setStep(step+1));
  $("end").addEventListener("click",()=>setStep(trace.length));
  $("search").addEventListener("input",render);
  $("event-filter").addEventListener("change",()=>{shownEvents=100;renderTrace();});
  $("selected-only").addEventListener("change",()=>{shownEvents=100;renderTrace();});
  $("more-events").addEventListener("click",()=>{shownEvents+=100;renderTrace();});
  $("download").addEventListener("click",()=>{
    const url=URL.createObjectURL(new Blob([data.archive_json+"\n"],{type:"application/json"}));
    const a=document.createElement("a");a.href=url;a.download="proof.json";a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  render();
})();
