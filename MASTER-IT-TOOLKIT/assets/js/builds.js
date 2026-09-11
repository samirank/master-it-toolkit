/* PC build templates and user-owned SQLite workflows. No arbitrary shell execution. */
(() => {
 'use strict';
 let custom={},loaded=false,loading=null,loadError='';
 const presets=window.TOOLKIT_BUILDS||{},tools=window.TOOLKIT_DATA||[];
 const node=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
 const button=(text,fn)=>{const b=node('button',text);b.onclick=fn;return b;};
 async function api(path,body){const r=await fetch(new URL('api/'+path,location.href),body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{cache:'no-store'});const data=await r.json();if(!r.ok)throw Error(data.error||'Launcher unavailable');return data;}
 function modal(title){const d=node('dialog');d.className='download-dialog';d.setAttribute('aria-label',title);d.append(button('Close',()=>d.close()),node('h2',title));d.onclose=()=>d.remove();document.body.append(d);d.showModal();return d;}
 function exportData(id,def){const url=URL.createObjectURL(new Blob([JSON.stringify({schemaVersion:1,id,...def},null,2)],{type:'application/json'}));const a=node('a');a.href=url;a.download=id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 async function load(){if(loaded)return;if(!loading)loading=(async()=>{if(window.TOOLKIT_LAUNCHER){custom=(await api('workspace')).customWorkflows||{};}loaded=true;})().finally(()=>loading=null);return loading;}
 const all=()=>({...presets,...custom});
 function field(label,input){const l=node('label',label);l.className='note-field';l.append(input);return l;}
 function select(values,value){const s=node('select');for(const [v,label] of values){const o=node('option',label);o.value=v;s.append(o);}s.value=value;return s;}
 async function editor(id){
  try{await load();}catch(e){loadError=e.message;}
  const original=all()[id],isCustom=id?.startsWith('custom-');
  const definition=original?structuredClone(original):{name:'My custom PC',platform:'Windows',steps:[{text:'Confirm scope and verify a recoverable backup.'}]};
  const d=modal(isCustom?'Edit custom build':'Create custom build');
  const name=node('input');name.value=isCustom?definition.name:original?definition.name+' · custom':definition.name;name.maxLength=120;
  const platform=select(['Windows','Linux','macOS'].map(v=>[v,v]),definition.platform||'Windows');d.append(field('Build name',name),field('Target platform',platform));
  const rows=node('div');d.append(rows);const steps=definition.steps;
  function paint(){rows.replaceChildren();steps.forEach((step,index)=>{
   const row=node('section');row.className='panel';const text=node('textarea');text.value=step.text;text.maxLength=4000;text.oninput=()=>step.text=text.value;
   const tool=select([['','No tool · manual checkpoint'],...tools.slice().sort((a,b)=>a.name.localeCompare(b.name)).map(t=>[t.id,t.name])],step.tool||'');tool.onchange=()=>{if(tool.value)step.tool=tool.value;else{delete step.tool;if(step.action!=='copy')step.action='manual';paint();}};
   const action=select([['manual','Manual checkpoint'],['install','Review and install'],['run','Run portable tool'],['copy','Reviewed file migration']],step.action||'manual');action.onchange=()=>step.action=action.value;
   const link=node('input');link.value=step.url||'';link.placeholder='https://official-documentation';link.oninput=()=>{if(link.value)step.url=link.value;else delete step.url;};
   row.append(node('h3','Step '+(index+1)),field('Instructions',text),field('Application',tool),field('Action',action),field('Optional official instructions',link));
   const controls=node('div');controls.className='actions';controls.append(button('Move up',()=>{if(index){[steps[index-1],steps[index]]=[steps[index],steps[index-1]];paint();}}),button('Move down',()=>{if(index<steps.length-1){[steps[index+1],steps[index]]=[steps[index],steps[index+1]];paint();}}),button('Remove step',()=>{steps.splice(index,1);paint();}));row.append(controls);rows.append(row);
  });}paint();
  d.append(button('Add step',()=>{steps.push({text:'',action:'manual'});paint();}));
  const status=node('p',window.TOOLKIT_LAUNCHER?'Custom builds are saved to SQLite on the SSD.': 'Preview only. Open the desktop launcher to save custom builds.');status.setAttribute('role','status');d.append(status);
  const save=button('Save custom build',async()=>{save.disabled=true;status.textContent='Saving to SQLite…';try{
   if(loadError)throw Error(loadError);
   const key=isCustom?id:'custom-'+crypto.randomUUID();
   const next={...custom,[key]:{name:name.value.trim(),platform:platform.value,steps}};
   await api('workspace',{key:'customWorkflows',value:next});custom=next;status.textContent='Saved to SQLite.';d.close();refresh();
  }catch(e){status.textContent=e.message;}finally{save.disabled=false;}});save.disabled=!window.TOOLKIT_LAUNCHER;d.append(save);
 }
 function preview(id){const def=all()[id];if(!def)return;const d=modal(def.name);d.append(node('p',def.platform+' setup · '+def.steps.length+' steps. Download the packages first, then start the guided workflow. Installer prompts, restarts and verification require your review.'));
  const actions=node('div');actions.className='actions';const architecture=select(['x64','arm64','x86'].map(v=>[v,v]),'x64');actions.append(field('Package architecture',architecture));const status=node('p');status.setAttribute('role','status');
  actions.append(button('Download build packages',async()=>{try{if(!window.TOOLKIT_LAUNCHER)throw Error('Open the desktop launcher to download packages.');const ids=[...new Set(def.steps.map(s=>s.tool).filter(Boolean))];if(!ids.length)throw Error('This build has manual steps only.');status.textContent='Starting package queue…';const result=await api('action',{action:'bulk-download',confirmed:true,tools:ids,platform:def.platform,architecture:architecture.value,mode:'missing'});status.textContent=result.message;window.dispatchEvent(new CustomEvent('toolkit-activity',{detail:{busy:true,message:result.message}}));}catch(e){status.textContent=e.message;}}));
  const start=button('Start guided build',()=>d.close());start.dataset.workflow=id;actions.append(start,button('Customize build',()=>{d.close();editor(id);}),button('Export build definition',()=>exportData(id,def)));d.append(actions,status);
  const list=node('ol');for(const step of def.steps){const row=node('li');row.append(node('p',step.text));if(step.tool){const t=tools.find(t=>t.id===step.tool);row.append(node('small',(t?.name||step.tool)+' · '+(step.action||'manual')));const dl=node('button','Download / manage');dl.dataset.manageDownload=step.tool;row.append(dl);}if(step.url){const a=node('a','Official instructions ↗');a.href=step.url;a.target='_blank';a.rel='noopener noreferrer';row.append(a);}list.append(row);}d.append(list);
 }
 function refresh(){const root=document.getElementById('build-library');if(root)render(root);}
 async function render(root){root.replaceChildren(node('p','Loading PC build profiles…'));try{await load();}catch(e){loadError=e.message;}if(!root.isConnected)return;root.replaceChildren();
  root.append(node('p','Software setup profiles: download the chosen apps, then follow a reviewed sequence for installation, configuration and verification. Free/open-source choices are preferred.'));
  const controls=node('div');controls.className='actions';controls.append(button('Saved run reports',async()=>{const d=modal('Saved workflow reports');try{const data=await api('history');for(const run of data.workflows||[]){const row=node('section');row.className='panel';row.append(node('h3',run.name),node('p',new Date(run.finished*1000).toLocaleString()),node('p',run.message),button('Export run report',()=>exportData('workflow-run-'+run.id,run)));d.append(row);}if(!(data.workflows||[]).length)d.append(node('p','No completed or stopped runs saved yet.'));}catch(e){d.append(node('p',e.message));}}),button('Create custom build',()=>editor()),button('Reload saved builds',()=>{loaded=false;loadError='';refresh();}));root.append(controls);
  if(loadError)root.append(node('p','SQLite unavailable: '+loadError));
  const grid=node('div');grid.className='cards';root.append(grid);
  for(const [id,def] of Object.entries(all())){const card=node('article');card.className='tool-card';card.append(node('h2',def.name),node('p',def.platform+' · '+def.steps.length+' steps · '+(id.startsWith('custom-')?'Saved custom build':'Included profile')),button('Review build',()=>preview(id)),button(id.startsWith('custom-')?'Edit build':'Clone and customize',()=>editor(id)));if(id.startsWith('custom-'))card.append(button('Delete build',()=>{const confirm=modal('Delete '+def.name+'?');confirm.append(node('p','This removes the saved definition. Export it first if you need a copy.'),button('Delete saved build',async()=>{try{const next={...custom};delete next[id];await api('workspace',{key:'customWorkflows',value:next});custom=next;confirm.close();refresh();}catch(e){confirm.append(node('p',e.message));}}));}));grid.append(card);}
 }
 window.ToolkitBuilds={render,get:id=>all()[id]};
})();
