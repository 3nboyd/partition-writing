'use strict';
const $=s=>document.querySelector(s), token=$('meta[name="partition-token"]').content;
let state,selectedStyle,selectedMode='guide',pendingMemory=[],uploading=false,polling=false;
function text(el,value){el.textContent=value;return el;}
function node(tag,cls,value){const el=document.createElement(tag);if(cls)el.className=cls;if(value!==undefined)el.textContent=value;return el;}
async function api(path,body){const r=await fetch('/api/'+path,{method:body===undefined?'GET':'POST',headers:{'X-Partition-Token':token,'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});const d=await r.json();if(!r.ok)throw Error(d.error||'Request failed.');return d;}
function status(message,error=false){text($('#status'),message);$('#status').classList.toggle('error',error);}
function fail(e){status(e.message||String(e),true);}
function action(fn){return async()=>{try{await fn();}catch(e){fail(e);}};}
function render(){
 text($('#count'),state.library.length);text($('#guide-count'),state.analysis.styles.length+' guides');
 $('#build').disabled=uploading||state.job.status==='running'||!state.library.length;
 text($('#build'),state.job.status==='running'?'Reading & building…':'Organize & build guides ↗');
 const docs=$('#documents');docs.replaceChildren();
 const classifications=new Map(state.analysis.documents.map(d=>[d.id,d]));
 for(const d of state.library){const c=classifications.get(d.id),row=node('div','document');row.append(node('span','file-icon',d.name.split('.').pop().toUpperCase().slice(0,4)));
 const info=node('div');info.append(node('h3','',d.name));info.append(node('p','',d.words.toLocaleString()+' words'+(c?' · '+c.reason:'')));
 info.append(node('span','badge'+(!c||c.style==='needs-review'?' review':''),c?(c.kind==='sample'?state.styles[c.style]:c.kind==='resume'?'Résumé · background':'Reference · background'):'Ready to organize'));
 if(c)info.append(node('span','badge',Math.round(c.confidence*100)+'% confidence'));
 row.append(info);const controls=node('details','doc-options');controls.append(node('summary','','Adjust'));const style=node('select');style.setAttribute('aria-label','Style for '+d.name);
 for(const [id,name]of Object.entries(state.styles)){const o=node('option','',name);o.value=id;o.selected=id===(c?.style||'needs-review');style.append(o);}
 const kind=node('select');kind.setAttribute('aria-label','Type for '+d.name);for(const [id,name] of [['sample','My writing'],['resume','Résumé'],['reference','Reference']]){const o=node('option','',name);o.value=id;o.selected=id===(c?.kind||d.kind);kind.append(o);}
 const save=node('button','text-button','Save correction');save.onclick=action(async()=>{await api('override',{id:d.id,style:style.value,kind:kind.value});status('Correction saved. Build guides again to apply it.');controls.open=false;});
 const archive=node('button','text-button','Archive');archive.onclick=action(async()=>{await api('archive',{id:d.id});await load();status('Archived locally. Rebuild to refresh the guides.');});controls.append(style,kind,save,archive);row.append(controls);docs.append(row);}
 if(!state.library.length)docs.append(node('p','empty','Upload a few samples to begin. Your originals stay untouched.'));
 const styles=$('#styles');styles.replaceChildren();for(const s of state.analysis.styles){const b=node('button','style-card');const label=node('span');label.append(node('strong','',s.name),node('small','',s.source_ids.length+' source sample'+(s.source_ids.length===1?'':'s')+' · guide + writing prompts'));b.append(label,node('span','','↗'));b.onclick=()=>openStyle(s.id);styles.append(b);}
 if(!state.analysis.styles.length)styles.append(node('p','empty','Your styles emerge from your samples. No need to define them first.'));
 if(state.job.status==='running'||state.job.status==='error'||state.job.status==='done')status(state.job.message,state.job.status==='error');
 else status(state.analysis.built_at?'Your library is ready. Open a style to use it in any chat.':state.library.length+' documents ready. Build your guides when you’re ready.');
}
async function load(){state=await api('state');render();if(state.job.status==='running'&&!polling)poll();}
async function poll(){polling=true;try{while(state?.job.status==='running'){await new Promise(resolve=>setTimeout(resolve,1800));await load();}}catch(e){fail(e);}finally{polling=false;}}
async function upload(files){if(uploading)return;uploading=true;$('#build').disabled=true;let done=0,errors=[];
 try{for(const file of files){status('Uploading '+(done+1)+' of '+files.length+'…');try{if(file.size>12*1024*1024)throw Error(file.name+': over 12 MB.');const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(Error('Could not read '+file.name));reader.readAsDataURL(file);});await api('upload',{name:file.name,data});}catch(e){errors.push(e.message);}done++;}await load();status(errors.length?errors.join(' '):done+' documents added. Ready to organize.',!!errors.length);}finally{uploading=false;$('#files').value='';$('#build').disabled=state?.job.status==='running'||!state?.library.length;}}
$('#files').onchange=e=>upload([...e.target.files]).catch(fail);
const drop=$('#dropzone');for(const name of ['dragenter','dragover'])drop.addEventListener(name,e=>{e.preventDefault();drop.classList.add('dragging');});for(const name of ['dragleave','drop'])drop.addEventListener(name,e=>{e.preventDefault();drop.classList.remove('dragging');});drop.addEventListener('drop',e=>upload([...e.dataTransfer.files]).catch(fail));
$('#build').onclick=action(async()=>{await api('build',{});await load();});$('#refresh').onclick=action(load);
async function copy(value){try{await navigator.clipboard.writeText(value);return true;}catch{const area=node('textarea');area.value=value;document.body.append(area);area.select();const copied=document.execCommand('copy');area.remove();if(!copied)throw Error('Copy is unavailable. Use Download prompt.');return true;}}
function openStyle(id){selectedStyle=id;selectedMode='guide';$('#task').value='';renderGuide();$('#guide-dialog').showModal();}
function renderGuide(){const s=state.analysis.styles.find(x=>x.id===selectedStyle);text($('#dialog-title'),s.name+' writing');text($('#guide-content'),selectedMode==='guide'?s.guide:selectedMode==='new'?s.new_prompt:s.edit_prompt);for(const mode of ['guide','new','edit'])$('#tab-'+mode).classList.toggle('active',mode===selectedMode);$('#task').hidden=selectedMode==='guide';$('#task-label').hidden=selectedMode==='guide';text($('#copy-bundle'),'Copy '+(selectedMode==='guide'?'guide + context':'writing prompt'));}
for(const mode of ['guide','new','edit'])$('#tab-'+mode).onclick=()=>{selectedMode=mode;renderGuide();};$('#close-dialog').onclick=()=>$('#guide-dialog').close();
async function bundle(){return api('bundle',{style:selectedStyle,mode:selectedMode==='guide'?'new':selectedMode,task:$('#task').value});}
$('#copy-bundle').onclick=action(async()=>{const b=await bundle();await copy(b.text);text($('#copy-bundle'),'Copied ✓');});
$('#download-bundle').onclick=action(async()=>{const b=await bundle(),url=URL.createObjectURL(new Blob([b.text],{type:'text/markdown;charset=utf-8'}));const a=node('a');a.href=url;a.download=b.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('#save-preferences').onclick=action(async()=>{await api('preferences',{text:$('#preferences').value});status('Preferences saved. Build guides to include these changes.');});
$('#memory-prompt').onclick=action(async()=>{await copy(state.memory_prompt);text($('#memory-prompt'),'Memory request copied ✓');});
$('#preview-memory').onclick=action(async()=>{pendingMemory=(await api('memory/preview',{text:$('#memory').value})).items;const list=$('#memory-items');list.replaceChildren();for(const [index,item]of pendingMemory.entries()){const row=node('div','memory-item'),check=node('input');check.type='checkbox';check.id='memory-'+index;check.checked=item.selected;check.onchange=()=>item.selected=check.checked;const label=node('label','',item.text+(item.kind==='inferred'?' (uncertain)':''));label.htmlFor=check.id;row.append(check,label);list.append(row);}$('#save-memory').hidden=false;});
$('#save-memory').onclick=action(async()=>{const draft={...state.draft,memory_text:$('#memory').value,memory_items:pendingMemory};await api('draft',draft);await api('apply',{});await load();status('Selected memory saved. Build guides to include relevant guidance.');});
(async()=>{await load();$('#preferences').value=state.writing_preferences||'';$('#memory').value=state.draft.memory_text||'';})().catch(fail);
