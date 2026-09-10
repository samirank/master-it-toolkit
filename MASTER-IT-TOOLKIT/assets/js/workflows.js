/* Local processes stay in the launcher; checklist verification stays with the technician. */
(() => {
 'use strict';
 const definitions=window.TOOLKIT_WORKFLOWS, tools=window.TOOLKIT_DATA;
 const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
 const button=(text,fn)=>{const n=el('button',text);n.onclick=fn;return n;};
 const api=async(path,body)=>{const r=await fetch(new URL('api/'+path,location.href),body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,confirmed:true})}:{});const data=await r.json();if(!r.ok)throw Error(data.error||'Launcher unavailable');return data;};
 const activity=message=>window.dispatchEvent(new CustomEvent('toolkit-activity',{detail:{message,busy:true}}));
 function modal(title){const d=el('dialog');d.className='download-dialog';d.setAttribute('aria-label',title);d.append(button('Close',()=>d.close()),el('h2',title));document.body.append(d);d.onclose=()=>d.remove();d.showModal();return d;}
 async function openTool(id){
  const tool=tools.find(t=>t.id===id);if(!tool)return;
  const d=modal('Run '+tool.name), status=el('p','Checking scanned executables…');status.setAttribute('role','status');d.append(status);
  if(!window.TOOLKIT_LAUNCHER){status.textContent='Open the local Windows launcher to run portable applications. The demo cannot execute files.';return;}
  try{
   const data=await api('run-options?tool='+encodeURIComponent(id));
   if(data.files.length===1&&!data.confirmationRequired){await api('action',{action:'run-portable',tool:id,executable:data.files[0].path});activity('Opening '+tool.name+'…');d.close();return;}
   status.textContent=data.reason||data.launchNote||'Runs from the SSD, with no installer switches or automatic elevation. Review the application’s own prompts and results.';
   for(const file of data.files){const row=el('section');row.className='workflow-file';row.append(el('code',file.fullPath));row.append(button('Run '+file.name,async()=>{
    try{await api('action',{action:'run-portable',tool:id,executable:file.path});activity('Opening '+tool.name+'…');d.close();}catch(e){status.textContent=e.message;}
   }));d.append(row);}
   if(!data.files.length){const b=button('Download / manage portable files',()=>d.close());b.dataset.manageDownload=id;d.append(b);}
  }catch(e){status.textContent=e.message;}
 }
 let current=null, record=null, runner=null, last='', polling=false;
 const reopen=button('Workflow status',()=>showRunner());reopen.hidden=true;reopen.id='workflow-status-button';document.querySelector('.launcher-panel').after(reopen);
 function showRunner(){
  if(runner?.isConnected){runner.showModal();return;}
  runner=modal('Workflow runner');last='';paint();
 }
 function paint(){
  if(!runner?.isConnected)return;
  const key=JSON.stringify(current);if(key===last)return;last=key;
  runner.querySelector('.workflow-body')?.remove();const body=el('div');body.className='workflow-body';runner.append(body);
  const w=current?.workflow;
  body.append(el('p',current?.message||'Waiting for launcher…'));
  if(w){
   body.append(el('h3',w.name+' · Step '+(w.step+1)+' / '+w.count),el('p',w.current.text));
   const progress=el('progress');progress.max=w.count;progress.value=w.step;progress.setAttribute('aria-label','Workflow progress');body.append(progress);
   const controls=el('div');controls.className='actions';body.append(controls);
   const control=async(command,extra={})=>{try{await api('action',{action:'workflow-control',run:w.id,step:w.step,command,...extra});await poll();}catch(e){body.append(el('p',e.message));}};
   if(w.waiting){
    if(w.current.url){const a=el('a','Official instructions ↗');a.href=w.current.url;a.target='_blank';a.rel='noopener noreferrer';controls.append(a);}
    if(w.current.action==='install')controls.append(button('Review step installer',async()=>{
     const d=modal('Review installation'),status=el('p','Checking downloaded installers and installed apps…');d.append(status);
     try{const info=await api('install-options?tool='+encodeURIComponent(w.current.tool));
      status.textContent=info.reason||'Review the package and publisher. Windows installation uses the toolkit recovery checkpoint and may request UAC. Verify the result before continuing.';
      if(info.installedOnHost)d.append(el('p','Already detected on this PC. Review its version; you can verify this step without reinstalling.'));
      for(const file of info.files||[]){d.append(el('p',file.name+' · Publisher: '+(file.signature?.publisher||'Unknown')+' · Signature: '+file.signature?.status));const b=button('Install '+file.name,async()=>{await control('install',{package:file.path,sha256:file.sha256});d.close();});if(file.signature?.status!=='Valid'){b.disabled=true;d.append(el('p','This workflow requires a valid publisher signature. Use the individual installation review for other packages.'));}d.append(b);}
      if(!(info.files||[]).length)d.append(el('p','Stop the workflow to download a suitable installer, or set up the portable/native edition manually and verify the step.'));
     }catch(e){status.textContent=e.message;}
    }));
    else if(w.current.tool&&w.current.action!=='manual')controls.append(button('Launch step tool',()=>control('run')));
    controls.append(button('I verified this step · Continue',()=>control('next')),button('Skip · Record as unverified',()=>control('skip')));
   }else body.append(el('p','Application running… Follow its prompts and close it when finished.'));
   controls.append(button('Stop workflow',()=>control('stop')));
   body.append(el('small','Stop prevents further launches and leaves open applications running. Closing this panel does not stop the workflow. Review any helper windows before continuing.'));
  }
  if(record){body.append(button('Export workflow record',()=>{
   const blob=new Blob([JSON.stringify(record,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='toolkit-workflow-record.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }));}
 }
 async function poll(){
  if(!window.TOOLKIT_LAUNCHER||polling)return;polling=true;
  try{const data=await api('status');if(data.workflow||data.workflowRecord){current=data;if(data.workflowRecord)record={finishedAt:new Date().toISOString(),message:data.message,steps:data.workflowRecord};reopen.hidden=false;paint();}
   else if(current?.workflow){current={message:data.message};paint();}
  }catch(e){if(runner?.isConnected){current={message:'Launcher disconnected. Reopen it to check the workflow; do not assume an application finished.'};paint();}}
  finally{polling=false;}
 }
 function start(id){
  const def=definitions[id]||window.ToolkitBuilds?.get(id);if(!def)return;const d=modal(def.name+' workflow');
  d.append(el('p','Prefer suitable free/open-source tools; for automation prefer documented command-line or batch interfaces. Paid editions are optional when a required capability is missing.'));
  d.append(el('p','Automatic mode opens the available portable tool for each supported step, then waits for your review. Manual mode waits for you to launch each tool. Missing tools, consent, scan findings, copy settings and destructive actions always need attention.'));
  const list=el('ol');for(const step of def.steps)list.append(el('li',step.text+(step.tool?' — '+tools.find(t=>t.id===step.tool)?.name:'')));d.append(list);
  if(!window.TOOLKIT_LAUNCHER){d.append(el('p','Use the local launcher to run workflows. This demo provides the full checklist preview.'));return;}
  const actions=el('div');actions.className='actions';d.append(actions);
  for(const mode of ['manual','automatic'])actions.append(button(mode==='automatic'?'Start · Automatic launches':'Start · Manual launches',async()=>{
   try{current=await api('action',{action:'workflow',workflow:id,mode});record=null;activity('Starting '+def.name+'…');d.close();showRunner();await poll();}catch(e){d.append(el('p',e.message));}
  }));
 }
 document.addEventListener('click',event=>{const run=event.target.closest('[data-run-tool]'), flow=event.target.closest('[data-workflow]');if(run)openTool(run.dataset.runTool);if(flow)start(flow.dataset.workflow);});
 poll();setInterval(poll,1500);
})();
